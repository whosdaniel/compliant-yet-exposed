"""pilot2s_verify.py -- integrity check of the finished E8 run (pilot2s_scale.jsonl): completeness against the
design grid, duplicates, and exact re-run determinism of a fixed random sample (10 runs with M <= 3072
plus 2 adverse runs at M = 12288, which exercise the silhouette subsample path). Run: python pilot2s_verify.py"""
import json, random, sys
from collections import Counter
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pilot2s_scale as e8

rows = [json.loads(l) for l in open(e8.JSONL) if l.strip()]
keys = [e8.key(r["M"], r["K"], r["W"], r["cond"], r["seed"]) for r in rows]
expected = {e8.key(*t) for t in e8.all_tasks()}
dup = [k for k, c in Counter(keys).items() if c > 1]
print(f"lines={len(rows)} expected_tasks={len(expected)} unique={len(set(keys))} dups={len(dup)} "
      f"missing={len(expected - set(keys))} extra={len(set(keys) - expected)}")

# exact re-run of a random sample (fixed sampling seed so this check is itself reproducible)
by = {k: r for k, r in zip(keys, rows)}
rng = random.Random(20261027)
small = [r for r in rows if r["M"] <= 3072]
pick = rng.sample(small, 10) + rng.sample([r for r in rows if r["M"] == 12288 and r["cond"] == "adverse"], 2)
bad = 0
for r in pick:
    n = e8.run_one(r["M"], r["K"], r["W"], r["cond"], r["seed"])
    same = (n["ari_oracle"], n["ari_silK"], n["khat"]) == (r["ari_oracle"], r["ari_silK"], r["khat"])
    bad += (not same)
    print(f"M={r['M']:>5} K={r['K']:>2} W={r['W']:>2} {r['cond']:<9} seed={r['seed']:>2} "
          f"stored=({r['ari_oracle']},{r['ari_silK']},{r['khat']}) rerun=({n['ari_oracle']},{n['ari_silK']},{n['khat']}) "
          f"{'OK' if same else 'MISMATCH'}")
print("determinism:", "ALL MATCH" if bad == 0 else f"{bad} MISMATCH")
