"""capture_record_sizes.py -- reads the TLS records off the loopback capture (pilot/results/real_socket_capture.pcap)
and checks them against the per-phase summary that real_socket_capture.py stored (revision R1, Fig. 4).

The capture script computed each phase's wire bytes as plaintext length + the measured 22-byte TLS 1.3 record overhead.
This check parses the pcap itself: it reassembles the client-to-server TCP stream, walks the TLS record headers, drops
the handshake (ClientHello, ChangeCipherSpec, and the encrypted Finished, the first application-data-typed record),
and splits the remaining application records into the idle and active phases by their timing: a record belongs to the
active phase once the next record follows within 5 s (idle polls are 15 s apart in the capture, active records at most
about 4.2 s). Nothing here depends on record sizes. Output: capture_record_sizes.json next to this script.
Run: python revision/diagnostics/capture_record_sizes.py
"""
import json, os, struct
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PCAP = os.path.join(ROOT, "pilot", "results", "real_socket_capture.pcap")
SUMMARY = os.path.join(ROOT, "pilot", "results", "real_socket_capture.json")

b = open(PCAP, "rb").read()
end = "<" if b[:4] == b"\xd4\xc3\xb2\xa1" else ">"
link = struct.unpack(end + "I", b[20:24])[0]
assert link == 101, f"expected raw-IP linktype 101, got {link}"
off, streams, chunks = 24, defaultdict(bytearray), defaultdict(list)
while off + 16 <= len(b):
    ts, tu, incl, _ = struct.unpack(end + "IIII", b[off:off + 16]); off += 16
    pkt = b[off:off + incl]; off += incl
    ihl = (pkt[0] & 15) * 4; tcp = pkt[ihl:]; doff = (tcp[12] >> 4) * 4
    sport, dport = struct.unpack("!HH", tcp[:4]); data = tcp[doff:]
    if data:
        chunks[(sport, dport)].append((ts + tu / 1e6, len(streams[(sport, dport)])))
        streams[(sport, dport)] += data

c2s = next(k for k in streams if k[1] == 8443)          # client -> server (the server listens on 8443)
s, recs, i = streams[c2s], [], 0
while i + 5 <= len(s):
    ctype, length = s[i], struct.unpack("!H", s[i + 3:i + 5])[0]
    t = max(tt for tt, pos in chunks[c2s] if pos <= i)
    recs.append({"t": t, "type": ctype, "wire": 5 + length}); i += 5 + length
assert i == len(s), "stream does not end on a record boundary"

first_app = next(n for n, r in enumerate(recs) if r["type"] == 23)   # encrypted Finished (TLS 1.3)
app = recs[first_app + 1:]
t0 = app[0]["t"]
start = next(n for n in range(len(app) - 1) if app[n + 1]["t"] - app[n]["t"] < 5.0)
phases = {"idle": app[:start], "active": app[start:]}
summ = json.load(open(SUMMARY))
out = {"pcap": "pilot/results/real_socket_capture.pcap", "handshake_records_c2s": first_app + 1, "phases": {}}
for name, rs in phases.items():
    stored = summ[f"{name}_phase"]
    n, tot = len(rs), sum(r["wire"] for r in rs)
    out["phases"][name] = {
        "records": n, "wire_bytes": tot, "mean_wire_bytes": tot / n,
        "sizes": sorted({r["wire"] for r in rs}),
        "first_s": round(rs[0]["t"] - t0, 2), "last_s": round(rs[-1]["t"] - t0, 2),
        "matches_stored_summary": (n, tot) == (stored["msgs"], stored["wire_bytes"]),
    }
out["all_match"] = all(p["matches_stored_summary"] for p in out["phases"].values())
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "capture_record_sizes.json"), "w"), indent=2)
print(json.dumps(out, indent=1))
