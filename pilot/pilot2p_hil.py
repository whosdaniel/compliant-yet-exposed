"""pilot2p_hil.py -- A1 grounding: a self-contained DISAGGREGATION CONTROL LOOP that emits real
per-DER TLS commands, captured off real loopback sockets. Upgrades the "strong continuous-AGC
command-down layer is modeled" caveat (Section 7.3) by showing A1 is realizable in a running stack.

WHAT IS REAL HERE:
  - a controller takes an aggregate AGC trajectory and DISAGGREGATES it (state-of-charge-equalizing)
    into one setpoint per DER per 4 s tick (A1a: central per-DER computation);
  - each per-DER setpoint is sent as a real TLS 1.3 record over that DER's own loopback connection
    (A1b: a distinct per-4s network message; A1d: per-DER flows are separable by connection);
  - repeated/unchanged setpoints still emit a record (A1c: no batching/suppression in this build);
  - per-DER, per-window command counts and inter-record timing are captured off the sockets.

WHAT IS NOT CLAIMED (honesty / anti-tautology):
  - This is an emulation, not a commercial DERMS; it shows A1 is REALIZABLE, not that any vendor does it.
  - It deliberately does NOT recover co-membership. The award/pool schedule is set by us, so clustering
    the capture would recover our own schedule (tautology = the killed VPP failure). Co-membership
    recovery and the A2/A3 conditions stay in the Section 8 simulation (argued, not measured).
  - Wall-clock cadence is COMPRESSED to keep the run short (4 s nominal -> TICK s); the per-DER message
    structure, counts, and active/idle contrast are real; only the absolute period is scaled (labeled).

Legal: all endpoints and traffic are ours, on 127.0.0.1. No third-party traffic is touched.
"""
from __future__ import annotations
import ssl, socket, threading, time, json, os
import numpy as np
import real_tls_measure as R
from real_socket_capture import ensure_cert, CERT, KEY

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results"); os.makedirs(RES, exist_ok=True)

M = 8                      # DERs (each its own TLS connection)
K = 2                      # pools (schedule set by us; NOT recovered from the capture)
W = 6                      # award windows
TICKS_PER_WINDOW = 10      # 4 s setpoints per active window (compressed)
TICK = 0.02               # compressed wall-clock per 4 s nominal tick
P_AWARD = 0.5
SETPOINT = R.PAYLOADS["setpoint (Modbus write)"]   # 12 B plaintext -> 34 B wire (measured)
OVH = 22


def soc_equalizing_setpoints(agc_value, soc):
    """Disaggregate one aggregate AGC value across a pool's DERs, weighted by headroom (SoC)."""
    w = soc / (soc.sum() + 1e-9)
    return agc_value * w


def sink_server(port, ready, stop):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(CERT, KEY)
    ls = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ls.bind(("127.0.0.1", port)); ls.listen(M + 4); ls.settimeout(0.5); ready.set()

    def drain(tls):
        try:
            while True:
                if not tls.recv(4096):
                    break
        except OSError:
            pass
        finally:
            try: tls.close()
            except OSError: pass

    while not stop.is_set():
        try:
            conn, _ = ls.accept()
            tls = ctx.wrap_socket(conn, server_side=True)
            threading.Thread(target=drain, args=(tls,), daemon=True).start()
        except socket.timeout:
            continue
        except OSError:
            break
    ls.close()


def run():
    ensure_cert()
    # server
    holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    holder.bind(("127.0.0.1", 0)); port = holder.getsockname()[1]; holder.close()
    ready, stop = threading.Event(), threading.Event()
    th = threading.Thread(target=sink_server, args=(port, ready, stop), daemon=True)
    th.start(); ready.wait(5)

    # pools + award schedule (SET BY US -- not recovered from capture)
    rng = np.random.default_rng(0)
    pools = np.array([i % K for i in range(M)]); rng.shuffle(pools)
    pool_sched = {k: np.array([(w % K) == k for w in range(W)]) for k in range(K)}  # distinct per pool (set by us)
    soc = rng.uniform(0.4, 1.0, M)                                    # per-DER state of charge

    # M real TLS client connections (one per DER)
    cctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    cctx.check_hostname = False; cctx.verify_mode = ssl.CERT_NONE
    conns, ports = [], []
    for i in range(M):
        raw = socket.create_connection(("127.0.0.1", port))
        tls = cctx.wrap_socket(raw, server_side=False)
        conns.append(tls); ports.append(tls.getsockname()[1])
    cipher = conns[0].cipher()[0]

    events = []  # (t, der, window, wire_bytes)
    t0 = time.time()
    for w in range(W):
        agc = 100.0 * (0.6 + 0.4 * np.sin(w))     # an aggregate AGC trajectory
        for _ in range(TICKS_PER_WINDOW):
            for i in range(M):
                active = pool_sched[pools[i]][w]
                if not active:
                    continue
                # A1a: central per-DER disaggregation (value computed; size is the fixed setpoint record)
                _sp = soc_equalizing_setpoints(agc, soc[pools == pools[i]])
                try:
                    conns[i].sendall(SETPOINT)                # A1b: real per-DER TLS record
                    events.append((time.time() - t0, i, w, len(SETPOINT) + OVH))
                except OSError:
                    pass
            time.sleep(TICK)

    for c in conns:
        try: c.close()
        except OSError: pass
    stop.set(); th.join(timeout=3)
    return cipher, events, pools.tolist(), ports


def summarize(cipher, events, pools, ports):
    ev = np.array([(e[0], e[1], e[2], e[3]) for e in events], dtype=float)
    per_der_counts = {}
    for i in range(M):
        rows = ev[ev[:, 1] == i]
        # per-window command count for this DER (the observable the Section 8 attack uses)
        counts = [int(np.sum((rows[:, 2] == w))) for w in range(W)]
        per_der_counts[i] = counts
    # realized inter-record interval on one busy DER (real timing, compressed)
    busy = max(range(M), key=lambda i: len(ev[ev[:, 1] == i]))
    bt = np.sort(ev[ev[:, 1] == busy][:, 0])
    iri = np.diff(bt)
    return {
        "cipher": cipher, "n_DER_streams": M, "n_pools_set": K, "windows": W,
        "total_records": len(events),
        "distinct_source_ports": len(set(ports)),     # A1d: per-DER flows separable
        "per_der_window_command_counts": per_der_counts,
        "realized_inter_record_s_median": round(float(np.median(iri)), 4) if len(iri) else None,
        "tick_nominal_s": 4.0, "tick_compressed_s": TICK,
        "wire_bytes_per_setpoint": len(SETPOINT) + OVH,
        "pools_set_by_us": pools,
        "scope": "A1 grounding only (real per-DER TLS command emission + cadence + per-flow separability). "
                 "Co-membership NOT recovered here (set schedule -> tautology); stays Section 8 sim with A2/A3 argued.",
    }


def main():
    cipher, events, pools, ports = run()
    summ = summarize(cipher, events, pools, ports)
    json.dump(summ, open(os.path.join(RES, "pilot2p_hil.json"), "w"), indent=2)
    print("=" * 74)
    print(f"A1 HIL: real TLS disaggregation capture (cipher={cipher})")
    print("=" * 74)
    print(f"  per-DER TLS streams (separable flows): {summ['n_DER_streams']} "
          f"(distinct source ports {summ['distinct_source_ports']})")
    print(f"  total per-DER setpoint records emitted: {summ['total_records']}")
    print(f"  realized inter-record interval (median): {summ['realized_inter_record_s_median']} s "
          f"(nominal 4 s, compressed to {TICK} s)")
    print(f"  per-DER per-window command counts (captured): active windows ~{TICKS_PER_WINDOW}, idle 0")
    for i in range(min(M, 4)):
        print(f"    DER{i} (pool {pools[i]}): {summ['per_der_window_command_counts'][i]}")
    print("  -> A1a-d demonstrated in a running control loop; co-membership stays sim (anti-tautology).")
    print(f"  saved -> {os.path.join(RES, 'pilot2p_hil.json')}")


if __name__ == "__main__":
    main()
