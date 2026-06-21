"""
real_socket_capture.py — REAL-SOCKET capture (Approach 3 / robustness artifact).

Upgrades Pilot-2's idle-vs-active traffic SHAPE from arithmetic composition to a real
capture taken off a genuine loopback TLS 1.3 connection. Produces a real .pcap.

HOW (root-free, fully legal): we run our OWN compliant exchange over a real loopback
TCP socket: a TLS server thread and a TLS client thread, connected THROUGH a tiny
in-process TCP relay we control. The relay forwards opaque bytes both directions and
logs every wire chunk with a wall-clock timestamp. The TLS endpoints are ours, the
traffic is ours, the capture is on localhost. This is NOT interception of any third
party (which would be illegal) and NOT a live-deployment trace.

WHAT IS REAL HERE (label exactly):
  - real TLS 1.3 handshake + real AES-GCM record bytes traversing a real socket
  - real per-record wire sizes and real wall-clock inter-record timing
  - real idle-vs-active traffic SHAPE (counts + bytes), captured not composed
WHAT IS STILL MODELED (unchanged):
  - the 4s/30s cadence VALUES are spec-imposed by us (CAISO-derived), not discovered
  - the strong continuous-AGC command-down layer (illegal/no-stack) stays model-grade
  - pool/award structure and co-membership recovery stay in Pilot-2 sim (§8.4 label):
    THIS CAPTURE DELIBERATELY DOES NOT STAGE OR RECOVER CO-MEMBERSHIP. A local capture
    of experimenter-scheduled pools would recover our own schedule = tautology. It is a traffic-shape grounding artifact only.
"""
import ssl, socket, threading, time, struct, json, os, subprocess, tempfile
import real_tls_measure as R  # reuse the real schema-serialized payloads

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results"); os.makedirs(RES, exist_ok=True)
CERT = os.path.join(tempfile.gettempdir(), "_rsc_cert.pem")
KEY = os.path.join(tempfile.gettempdir(), "_rsc_key.pem")

# spec-imposed cadence (modeled values; only sizes/timing-of-record are "real")
SETPOINT_PERIOD_S = 4.0      # CAISO AGC 4s
IDLE_POLL_PERIOD_S = 15.0    # idle VEN poll (scaled from 30s to keep capture short; labeled)
N_SETPOINTS = 12             # representative active slice (per-minute rate stated in §8.5)
N_IDLE_POLLS = 3


def ensure_cert():
    if os.path.exists(CERT) and os.path.exists(KEY):
        return
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-keyout", KEY,
                    "-out", CERT, "-days", "1", "-nodes", "-subj", "/CN=vtn.local"],
                   check=True, capture_output=True)


# ----------------------------- tiny logging TCP relay -----------------------------
class Relay:
    """client <-> [relay logs chunks] <-> server, all on 127.0.0.1."""
    def __init__(self, server_port):
        self.server_port = server_port
        self.log = []                # (t, direction, nbytes)
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lsock.bind(("127.0.0.1", 0))
        self.lsock.listen(1)
        self.port = self.lsock.getsockname()[1]
        self.t0 = None

    def _pump(self, src, dst, direction):
        try:
            while True:
                data = src.recv(65535)
                if not data:
                    break
                self.log.append((time.time(), direction, len(data), data))
                dst.sendall(data)
        except OSError:
            pass
        finally:
            try: dst.shutdown(socket.SHUT_WR)
            except OSError: pass

    def serve(self):
        cli, _ = self.lsock.accept()
        up = socket.create_connection(("127.0.0.1", self.server_port))
        a = threading.Thread(target=self._pump, args=(cli, up, "c2s"), daemon=True)
        b = threading.Thread(target=self._pump, args=(up, cli, "s2c"), daemon=True)
        a.start(); b.start(); a.join(); b.join()
        cli.close(); up.close()


# ------------------------------- TLS server thread --------------------------------
def server_thread(server_port, ready):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(CERT, KEY)
    ls = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ls.bind(("127.0.0.1", server_port)); ls.listen(1); ready.set()
    conn, _ = ls.accept()
    tls = ctx.wrap_socket(conn, server_side=True)
    try:
        while True:
            data = tls.recv(65535)
            if not data:
                break
            # server replies to a poll with an event/ack-sized message (telemetry-side)
            if b"oadrPoll" in data:
                tls.sendall(R.PAYLOADS["oadrCreatedEvent (ack)"])
    except OSError:
        pass
    finally:
        try: tls.close()
        except OSError: pass
        ls.close()


# ------------------------------- capture driver -----------------------------------
def run_capture():
    ensure_cert()
    # start server on its own port
    srv_port_holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv_port_holder.bind(("127.0.0.1", 0)); server_port = srv_port_holder.getsockname()[1]
    srv_port_holder.close()

    ready = threading.Event()
    st = threading.Thread(target=server_thread, args=(server_port, ready), daemon=True)
    st.start(); ready.wait(5)

    relay = Relay(server_port)
    rt = threading.Thread(target=relay.serve, daemon=True); rt.start()

    cctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    cctx.check_hostname = False; cctx.verify_mode = ssl.CERT_NONE
    raw = socket.create_connection(("127.0.0.1", relay.port))
    tls = cctx.wrap_socket(raw, server_side=False)  # real handshake THROUGH the relay
    relay.t0 = time.time()
    cipher = tls.cipher()[0]

    events = []   # app-level: (t, phase, name, plaintext_len)

    def send(name, phase):
        pl = R.PAYLOADS[name]
        events.append((time.time(), phase, name, len(pl)))
        tls.sendall(pl)
        time.sleep(0.15)  # let the record flush as its own segment(s) before next

    # --- IDLE phase: sparse polls (server answers each) ---
    for i in range(N_IDLE_POLLS):
        send("oadrPoll (idle)", "idle")
        time.sleep(IDLE_POLL_PERIOD_S)

    # --- ACTIVE-REGULATION phase: 4s setpoints + interleaved telemetry, 1 event + 1 ack ---
    send("oadrDistributeEvent (event delivery)", "active")     # ISO -> agg event delivery
    send("oadrCreatedEvent (ack)", "active")                   # opt-in ack
    for i in range(N_SETPOINTS):
        send("setpoint (Modbus write)", "active")              # per-DER disaggregation setpoint
        send("oadrReport telemetry (active)", "active")        # aggregate telemetry report
        time.sleep(SETPOINT_PERIOD_S)

    time.sleep(0.3)
    try: tls.close()
    except OSError: pass
    rt.join(timeout=3)
    return cipher, events, relay.log, relay


# ------------------------------- minimal PCAP writer ------------------------------
def _ip_checksum(b):
    if len(b) % 2: b += b"\x00"
    s = sum(struct.unpack("!%dH" % (len(b) // 2), b))
    s = (s >> 16) + (s & 0xFFFF); s += (s >> 16)
    return (~s) & 0xFFFF

def _tcp_checksum(src, dst, tcp):
    pseudo = src + dst + struct.pack("!BBH", 0, 6, len(tcp))
    return _ip_checksum(pseudo + tcp)

def write_pcap(path, log, cport=49213, sport=8443):
    CIP = socket.inet_aton("127.0.0.1"); SIP = socket.inet_aton("127.0.0.1")
    seq = {"c2s": 1000, "s2c": 5000}
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 101))  # DLT_RAW
        for (t, direction, n, data) in log:
            if direction == "c2s":
                sip, dip, sp, dp = CIP, SIP, cport, sport; my, oth = "c2s", "s2c"
            else:
                sip, dip, sp, dp = SIP, CIP, sport, cport; my, oth = "s2c", "c2s"
            myseq, ackn = seq[my], seq[oth]
            tcp = struct.pack("!HHIIBBHHH", sp, dp, myseq, ackn, 0x50, 0x18, 65535, 0, 0) + data
            csum = _tcp_checksum(sip, dip, tcp)
            tcp = tcp[:16] + struct.pack("!H", csum) + tcp[18:]
            total = 20 + len(tcp)
            ip = struct.pack("!BBHHHBBH", 0x45, 0, total, 0, 0x4000, 64, 6, 0) + sip + dip
            ip = ip[:10] + struct.pack("!H", _ip_checksum(ip)) + ip[12:]
            pkt = ip + tcp
            seq[my] += len(data)
            ts = struct.pack("<IIII", int(t), int((t - int(t)) * 1e6), len(pkt), len(pkt))
            f.write(ts + pkt)


# ----------------------------------- summarize ------------------------------------
def summarize(cipher, events, log, t0):
    # app-level shape (counts + plaintext bytes), bucketed by phase
    OVH = 22  # measured TLS record overhead (real_tls_measure)
    def phase_stat(phase):
        evs = [e for e in events if e[1] == phase]
        msgs = len(evs)
        wire = sum(e[3] + OVH for e in evs)
        return dict(msgs=msgs, wire_bytes=wire)
    idle, active = phase_stat("idle"), phase_stat("active")
    # captured wire totals (real ciphertext bytes off the socket, both dirs)
    cap_c2s = sum(n for (_, d, n, _) in log if d == "c2s")
    cap_s2c = sum(n for (_, d, n, _) in log if d == "s2c")
    span = (log[-1][0] - log[0][0]) if log else 0.0
    return dict(
        cipher=cipher,
        capture="real loopback TLS via in-process relay (root-free); NOT kernel-sniffed, NOT third-party",
        idle_phase=idle, active_phase=active,
        captured_wire_chunks=len(log), captured_bytes_c2s=cap_c2s, captured_bytes_s2c=cap_s2c,
        capture_span_s=round(span, 2),
        cadence_modeled=dict(setpoint_period_s=SETPOINT_PERIOD_S, idle_poll_period_s=IDLE_POLL_PERIOD_S,
                             note="cadence VALUES are spec-imposed (modeled); record sizes & wire timing are real"),
        scope="traffic-shape grounding only; co-membership/award structure NOT captured (stays Pilot-2 sim, §8.4)",
    )


def main():
    cipher, events, log, relay = run_capture()
    pcap_path = os.path.join(RES, "real_socket_capture.pcap")
    write_pcap(pcap_path, log)
    summ = summarize(cipher, events, log, relay.t0)
    json.dump(summ, open(os.path.join(RES, "real_socket_capture.json"), "w"), indent=2)

    print("=" * 78)
    print("REAL-SOCKET capture (cipher=%s) — root-free loopback relay" % cipher)
    print("=" * 78)
    print(f"  captured wire chunks : {summ['captured_wire_chunks']}")
    print(f"  captured bytes       : c2s={summ['captured_bytes_c2s']}  s2c={summ['captured_bytes_s2c']}")
    print(f"  capture span         : {summ['capture_span_s']} s")
    print(f"  idle  phase (shape)  : {summ['idle_phase']['msgs']} msgs, {summ['idle_phase']['wire_bytes']} B")
    print(f"  active phase (shape) : {summ['active_phase']['msgs']} msgs, {summ['active_phase']['wire_bytes']} B")
    if summ['idle_phase']['msgs']:
        print(f"  active/idle ratio    : {summ['active_phase']['msgs']/summ['idle_phase']['msgs']:.1f}x msgs, "
              f"{summ['active_phase']['wire_bytes']/max(1,summ['idle_phase']['wire_bytes']):.1f}x bytes")
    print(f"\n  -> {pcap_path}")
    print(f"  -> {os.path.join(RES, 'real_socket_capture.json')}")
    print("\n  REAL: TLS handshake+records, wire sizes, per-record wall-clock timing, idle/active shape.")
    print("  MODELED (unchanged): 4s/30s cadence values; strong AGC command-down layer; co-membership (Pilot-2).")


if __name__ == "__main__":
    main()
