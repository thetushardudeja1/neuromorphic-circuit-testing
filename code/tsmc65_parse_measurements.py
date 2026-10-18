"""Parse the HSPICE measurement files (<root>/data/<kind>/<deck>/die.mt*, manifest.json) into one tidy CSV, <root>/readouts.csv.

One row = one neuron at one stimulus: Monte Carlo run `mc_run` of an .alter condition. mc_run 1 is HSPICE's nominal sample (flag is_nominal),
runs 2..K are independent local-mismatch draws. Handles both mt layouts: Monte Carlo (one row per run) and the wrapped non-MC layout (sens deck).
Class labels come from the manifest (alter# -> condition label/defect/stimulus/extra knobs), never from the file name.
usage: python tsmc65_parse_measurements.py [root = folder where raw_hspice_measurements.tgz was extracted]"""
import csv, glob, json, os, re, sys

root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "tsmc65", "raw")
NUM = re.compile(r"^[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?$")


def parse_mt(path):
    """-> list of dicts {col: value-or-None}; 'failed' -> None."""
    L = open(path, errors="replace").read().splitlines()
    i = next((k for k, x in enumerate(L) if x.startswith("index") or x.strip().startswith("t1 ")), None)
    out = []
    if i is not None and L[i].startswith("index"):                       # Monte Carlo layout
        hdr = L[i].split()
        for x in L[i + 1:]:
            p = x.split()
            if len(p) == len(hdr):
                out.append({h: (float(v) if NUM.match(v) else None) for h, v in zip(hdr, p)})
        return out
    # wrapped non-MC layout: header names (4 per line) until the numbers start, then values in the same order
    j = next(k for k, x in enumerate(L) if x.strip().startswith("t1 "))
    names, k = [], j
    while k < len(L) and L[k].strip() and not NUM.match(L[k].split()[0]) and L[k].split()[0] != "failed":
        names += L[k].split(); k += 1
    vals = []
    for x in L[k:]:
        vals += x.split()
    if len(vals) >= len(names):
        out.append({h: (float(v) if NUM.match(v) else None) for h, v in zip(names, vals[:len(names)])})
    return out


def main():
    rows_out, bad = [], 0
    cols = None
    for kind in ("sens", "drift", "tap", "main"):
        for deck in sorted(glob.glob(os.path.join(root, "data", kind, "*"))):
            mf = os.path.join(deck, "manifest.json")
            if not os.path.exists(mf):
                continue
            m = json.load(open(mf))
            ex = os.path.join(deck, "EXIT")
            if not os.path.exists(ex) or open(ex).read().strip() != "0":
                bad += 1
                continue
            cond = m["conditions"]
            for f in glob.glob(os.path.join(deck, "die.mt*")):
                for r in parse_mt(f):
                    alt = int(r.get("alter#", 0)) if r.get("alter#") is not None else 0
                    if alt < 1 or alt > len(cond):
                        continue
                    c = cond[alt - 1]
                    run = int(r["index"]) if r.get("index") is not None else 1
                    d = c["defect"]
                    lab = c["label"]
                    cls = "healthy" if d is None else "%s_%s" % (d[0], d[1])
                    row = dict(deck=m["id"], kind=m["kind"], die=m["die"], corner=m["corner"], seed=m["seed"], mc_run=run,
                               is_nominal=int(run == 1 and not m["nomc"]), label=lab, defect_id=cls, stim_nA=round(c["iamp"] * 1e9),
                               **{("x_" + k): v for k, v in c["extra"].items()})
                    row.update({k: v for k, v in r.items() if k not in ("index", "alter#", "temper")})
                    rows_out.append(row)
    cols = []
    for r in rows_out:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(os.path.join(root, "readouts.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows_out)
    print("rows", len(rows_out), "decks skipped (no manifest/EXIT!=0):", bad)


if __name__ == "__main__":
    main()
