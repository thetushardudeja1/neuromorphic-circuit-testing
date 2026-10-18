"""identifiability. Finite-difference sensitivity of every readout to every parameter (TSMC 65 nm 'sens' deck, nominal TT),
scaled by the healthy local-mismatch spread of that readout (TT-corner healthy neurons, 'main' data). Question: which parameter
combinations can the readouts tell apart, and which are in the null space (invisible)?"""
import numpy as np, pandas as pd
d = pd.read_csv("data/tsmc65/readouts.csv.gz", low_memory=False)
d["lat"] = d.t1 - 5e-6; d["per"] = d.t2 - d.t1; d["width"] = d.tf1 - d.t1
SPIKE = ["lat", "per", "width", "tl_avg", "tl_max", "t6"]; ANALOG = ["vtrip", "vpk", "vidle", "vmin", "vrst", "tcmp", "ttrip"]
SUP = ["qdd_all", "qdd_sp", "ipk"]; NODE = ["tail_t", "n3_t", "mid_t", "n4_t", "n3min", "midpk", "tailmax", "tailmin", "n4pk"]
ALL = SPIKE + ANALOG + SUP + NODE
s = d[d.kind == "sens"]; h = d[(d.kind == "main") & (d.is_nominal == 0) & (d.defect_id == "healthy") & (d.corner == "TT")]
print("healthy TT neurons for sigma:", h.deck.nunique() * 8, "| sens rows", len(s))
FLOOR = 1e-3        # ASSUMPTION (stated): readouts resolve 0.1 % of their nominal value; avoids dividing by numerically-zero spreads
def vec(sub, fs):
    return sub.set_index("stim_nA")[fs].sort_index()
params = {}
for lab in s.label.unique():
    if lab.endswith("+10mV"):
        params[lab[4:-5].rstrip("_")] = (lab, lab.replace("+10mV", "-10mV"), 10.0)
    elif lab.endswith("_+"):
        params[lab[:-2]] = (lab, lab[:-2] + "_-", {"cm": 2.0, "ib": 5.0, "vref": 10.0, "vrst": 10.0}[lab[:-2]])
names = list(params)
def build(fs):
    sig = np.maximum(h.groupby("stim_nA")[fs].std(), FLOOR * h.groupby("stim_nA")[fs].mean().abs())   # spread, but never below the instrument floor
    cols, keep = [], None
    J = []
    for n in names:
        lp, lm, step = params[n]
        a = vec(s[s.label == lp], fs); b = vec(s[s.label == lm], fs)
        J.append(((a - b) / 2 / sig).to_numpy().ravel())          # change per nudge, in healthy-sigma units
    J = np.clip(np.array(J).T, -50, 50)                          # features x parameters; clipped at 50 sigma (late-window output-level readouts flip chaotically at 400 nA)
    ok = np.isfinite(J).all(1) & np.isfinite(sig.to_numpy().ravel()) & (sig.to_numpy().ravel() > 0)
    return J[ok], ok.sum()
print("\nparameter nudge sizes: device Vth 10 mV; Cm 2 %; Ibias 5 %; Vref 10 mV; Vrst 10 mV")
out = {}
for nm, fs in [("spike + Vm readouts", SPIKE + ANALOG), ("+ supply current", SPIKE + ANALOG + SUP), ("+ internal nodes", ALL)]:
    J, nf = build(fs)
    U, S, Vt = np.linalg.svd(J, full_matrices=False)
    out[nm] = (J, S, Vt)
    print("\n== %s: %d usable features x %d parameters ==" % (nm, nf, len(names)))
    print("  singular values (sigma per nudge): max %.1f, min %.3f" % (S[0], S[-1]))
    for t in (0.1, 0.3, 1.0):
        print("  directions resolvable above %.1f sigma per nudge: %d of %d" % (t, (S > t).sum(), len(names)))
J, S, Vt = out["+ supply current"]
sens = np.linalg.norm(J, axis=0)
print("\n== per-parameter size of the signature (|column| in healthy-sigma, + supply set) - weakest first ==")
for i in np.argsort(sens)[:10]: print("  %-6s %8.2f" % (names[i], sens[i]))
print("\n== pairs of parameters that look alike (cosine of signatures > 0.95) ==")
Jn = J / np.linalg.norm(J, axis=0)
C = Jn.T @ Jn; pairs = [(C[i, j], names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names)) if abs(C[i, j]) > 0.95]
for c, a, b in sorted(pairs, key=lambda x: -abs(x[0]))[:12]: print("  %-6s ~ %-6s  cos %+.3f" % (a, b, c))
print("  (%d confusable pairs in total)" % len(pairs))
# which parameters does the null space consist of?
J2, S2, Vt2 = out["spike + Vm readouts"]
print("\n== weakest directions with spike + Vm only: dominant parameters ==")
for k in range(1, 4):
    v = Vt2[-k]; idx = np.argsort(-np.abs(v))[:4]
    print("  sing.value %.3f : %s" % (S2[-k], ", ".join("%s %+.2f" % (names[i], v[i]) for i in idx)))
