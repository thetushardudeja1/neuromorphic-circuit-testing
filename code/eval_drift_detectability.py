"""detectability of parametric drift in units of the healthy population spread (sigma).
Method (no ad-hoc max over noisy readouts): for every readout f (at each stimulus) and drift parameter p (mn1 Vth, Cm) fit the matched shift
   f(drifted) - f(same neuron, undrifted) = a * s + noise        over sizes s in {+-2,5,10,20 mV} / {+-1,2.5,5,10 %}  (linear regime, through the origin)
slope a = median over the 160 matched neurons; noise = RMS residual of that fit (includes simulator time-step jitter, so it is an UPPER bound).
Smallest detectable drift at 3 sigma:
   s_pop  = 3 * sigma_pop / |a|     sigma_pop = spread of f across healthy neurons of the MC dies  -> a test with no per-neuron history
   s_self = 3 * noise / |a|                                                                         -> before/after comparison of the SAME neuron
The best readout per parameter is reported; feature sets: spike+Vm vs +supply current."""
import numpy as np, pandas as pd
d = pd.read_csv("data/tsmc65/readouts.csv.gz", low_memory=False)
d["lat"] = d.t1 - 5e-6; d["per"] = d.t2 - d.t1; d["width"] = d.tf1 - d.t1
SPIKE = ["lat", "per", "width", "t6"]; ANALOG = ["vtrip", "vpk", "vmin", "vrst", "tcmp", "ttrip"]; SUP = ["qdd_all", "qdd_sp", "ipk"]
SETS = {"spike+Vm": SPIKE + ANALOG, "spike+Vm+supply": SPIKE + ANALOG + SUP}
pop = d[(d.kind == "main") & (d.is_nominal == 0) & (d.defect_id == "healthy") & (d.corner == "MC")]
dr = d[(d.kind == "drift") & (d.is_nominal == 0)].copy(); dr["neuron"] = dr.deck + "_r" + dr.mc_run.astype(str)
ALLF = SPIKE + ANALOG + SUP
def parse(lab):
    if lab == "base": return None
    _, par, rest = lab.split("_", 2); sgn = 1 if rest[0] == "+" else -1; val = float(rest[1:].replace("mV", "").replace("pct", ""))
    return par, sgn * val
dr["pp"] = dr.label.map(parse)
res = []
for par, maxs in (("mn1", 20), ("cm", 10)):
    for st in sorted(dr.stim_nA.unique()):
        b = dr[(dr.label == "base") & (dr.stim_nA == st)].set_index("neuron")[ALLF]
        sub = dr[(dr.stim_nA == st) & dr.pp.map(lambda x: x is not None and x[0] == par and abs(x[1]) <= maxs)]
        S = np.array([x[1] for x in sub.pp]); D = sub.set_index("neuron")[ALLF].reindex(sub.neuron.values).to_numpy() - b.reindex(sub.neuron.values).to_numpy()
        ok = np.isfinite(D)
        for j, f in enumerate(ALLF):
            m = ok[:, j]
            if m.sum() < 50: continue
            s_, y_ = S[m], D[m, j]
            # per-neuron slope through origin, then median over neurons
            nn = sub.neuron.values[m]; sl = pd.Series(y_ * s_).groupby(nn).sum() / pd.Series(s_ ** 2).groupby(nn).sum()
            a = sl.median(); resid = y_ - sl.reindex(nn).to_numpy() * s_; noise = np.sqrt(np.mean(resid ** 2))
            sp = pop[pop.stim_nA == st][f].std()
            if not np.isfinite(a) or a == 0 or not np.isfinite(sp): continue
            res.append(dict(par=par, stim=st, f=f, slope=a, s_pop=3 * sp / abs(a), s_self=3 * noise / abs(a), sigma_pop=sp))
R = pd.DataFrame(res); R["name"] = R.f + "@" + R.stim.astype(int).astype(str)
unit = {"mn1": "mV", "cm": "%"}
for par in ("mn1", "cm"):
    print("\n=== %s drift: smallest drift detectable at 3 sigma (units: %s) ===" % (par, unit[par]))
    for nm, fs in SETS.items():
        r = R[(R.par == par) & R.f.isin(fs)]
        a = r.sort_values("s_pop").iloc[0]; b = r.sort_values("s_self").iloc[0]
        print("  %-16s population-referenced: %6.2f via %-10s | per-neuron before/after: %6.3f via %s" % (nm, a.s_pop, a["name"], b.s_self, b["name"]))
    r = R[(R.par == par) & R.f.isin(SETS["spike+Vm+supply"])].sort_values("s_pop").head(4)
    print("  best 4 readouts (population ref):", ", ".join("%s %.2f%s" % (x["name"], x.s_pop, unit[par]) for _, x in r.iterrows()))
