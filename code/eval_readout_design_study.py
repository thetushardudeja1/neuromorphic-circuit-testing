"""Readout design study. Study 1: self-normalised supply readouts vs measurement noise.  Study 2: minimal test (stimulus subsets x readout families).
Study 3: optimal stimulus choice from the identifiability matrix.  TSMC 65 nm, die-based splits, 1 % false reject, mean of 3 splits."""
import itertools, warnings, time
import numpy as np, pandas as pd
import dataset_loader as cw
warnings.filterwarnings("ignore")
t0 = time.time(); w = cw.tsmc(); y = (w.defect_id != "healthy").astype(int).values; did = w.defect_id.values
STIM = [50, 100, 200, 400]
def run(X, seeds=(0, 1, 2)):
    out, per = [], {}
    for sd in seeds:
        tr, va, te = cw.split(w, sd); m = cw.hgb().fit(X[tr], y[tr]); sc = cw.logit(m.predict_proba(X)[:, 1])
        out.append(cw.miss_at_1pct(sc, y, va, te)); thr = np.quantile(sc[va & (y == 0)], .99)
        for k in set(did) - {"healthy"}: per.setdefault(k, []).append((sc[te & (did == k)] <= thr).mean() * 100)
    return np.mean([o[0] for o in out]), np.mean([o[1] for o in out]), {k: np.mean(v) for k, v in per.items()}
# ---------------- Study 1
print("=== Study 1: self-normalised supply readouts vs noise (relative Gaussian noise on each raw supply value) ===", flush=True)
rng = np.random.default_rng(7)
base = w[cw.cols(w, cw.SPIKE + cw.ANALOG)].to_numpy(float)
supc = cw.cols(w, cw.SUP); S0 = w[supc].to_numpy(float); idx = {c: i for i, c in enumerate(supc)}
lat = {s: w["lat@%d" % s].to_numpy(float) for s in STIM}
def derived(S):
    g = lambda f, s: np.log(np.abs(S[:, idx["%s@%d" % (f, s)]]) + 1e-30); R = []
    for s in STIM:
        R += [g("qdd_sp", s) - g("qdd_all", s), g("ipk", s) - g("qdd_sp", s), g("qdd_sp", s) - np.log(np.abs(lat[s]) + 1e-30)]
        if s != 100: R += [g("qdd_all", s) - g("qdd_all", 100), g("ipk", s) - g("ipk", 100)]
    return np.column_stack(R)
print("  noise | spike+Vm + raw supply            | + self-normalised ratios         | spike+Vm + ratios only", flush=True)
for rel in [0, .02, .05, .10, .20]:
    S = S0 * (1 + rel * rng.standard_normal(S0.shape)); D = derived(S); r = []
    for X in (np.hstack([base, S]), np.hstack([base, S, D]), np.hstack([base, D])):
        a, b, per = run(X); r.append((a, b, sum(v > 5 for v in per.values())))
    print("  %4.0f%% | " % (rel * 100) + " | ".join("miss %5.1f%%  FR %.1f  bad-defects %2d" % x for x in r), flush=True)
# ---------------- Study 2
print("\n=== Study 2: minimal test - missed faulty %% at 1%% false reject by stimulus subset and readout family (test time ~ number of stimuli) ===", flush=True)
FAM = {"spike only": cw.SPIKE, "spike+Vm": cw.SPIKE + cw.ANALOG, "spike+Vm+supply": cw.SPIKE + cw.ANALOG + cw.SUP, "minimal: lat,per,qdd_all,ipk": ["lat", "per", "qdd_all", "ipk"]}
subsets = [(s,) for s in STIM] + list(itertools.combinations(STIM, 2)) + [tuple(STIM)]
res2 = {}
print("  stimuli (nA)      " + "".join("%-34s" % f for f in FAM), flush=True)
for sub in subsets:
    line = "  %-17s " % "+".join(map(str, sub))
    for fn, fs in FAM.items():
        cs = [c for c in cw.cols(w, fs) if int(c.split("@")[1]) in sub]; a, b, per = run(w[cs].to_numpy(float)); res2[(sub, fn)] = a
        line += "%5.1f%% (n=%d, bad %d)%12s" % (a, len(cs), sum(v > 5 for v in per.values()), "")
    print(line, flush=True)
# ---------------- Study 3
print("\n=== Study 3: stimulus choice from the sensitivity (identifiability) matrix: weakest singular value (sigma per nudge) per stimulus subset ===", flush=True)
d = pd.read_csv("data/tsmc65/readouts.csv.gz", low_memory=False); d["lat"] = d.t1 - 5e-6; d["per"] = d.t2 - d.t1; d["width"] = d.tf1 - d.t1
s = d[d.kind == "sens"]; h = d[(d.kind == "main") & (d.is_nominal == 0) & (d.defect_id == "healthy") & (d.corner == "TT")]
F = ["lat", "per", "width", "t6", "vtrip", "vpk", "vmin", "vrst", "tcmp", "ttrip", "qdd_all", "qdd_sp", "ipk"]
params = {}
for lab in s.label.unique():
    if lab.endswith("+10mV"): params[lab[4:-5].rstrip("_")] = (lab, lab.replace("+10mV", "-10mV"))
    elif lab.endswith("_+"): params[lab[:-2]] = (lab, lab[:-2] + "_-")
sig = np.maximum(h.groupby("stim_nA")[F].std(), 1e-3 * h.groupby("stim_nA")[F].mean().abs())
def Jfor(sub):
    cols_ = []
    for n, (lp, lm) in params.items():
        a = s[s.label == lp].set_index("stim_nA")[F].sort_index(); b = s[s.label == lm].set_index("stim_nA")[F].sort_index()
        cols_.append(np.clip(((a - b) / 2 / sig).loc[list(sub)].to_numpy().ravel(), -50, 50))
    J = np.array(cols_).T; ok = np.isfinite(J).all(1); return J[ok]
print("  stimuli (nA)      weakest sv   #dirs > 1 sigma   miss (spike+Vm+supply, Study 2)", flush=True)
for sub in subsets:
    sv = np.linalg.svd(Jfor(sub), compute_uv=False); print("  %-17s %8.3f    %2d of 25        %5.1f%%" % ("+".join(map(str, sub)), sv[-1], (sv > 1).sum(), res2[(sub, "spike+Vm+supply")]), flush=True)
print("\ndone %.0fs" % (time.time() - t0))
