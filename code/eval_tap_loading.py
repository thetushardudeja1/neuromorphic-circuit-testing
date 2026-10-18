"""loading-aware readout. A readout tap (1 kohm + C_tap on Vm) loads the integrating node. TSMC 65 nm 'tap' decks (10 MC dies, matched):
healthy neurons at 0/10/25/50/100 fF and all 46 defects at 0 and 25 fF.
(1) per-fF shift of every readout in healthy-population sigma; (2) a detector trained WITHOUT tap on the main data (excluding the tap dies) is
applied to tapped neurons: false reject of healthy and miss of defects; (3) same detector retrained with the tap capacitance known/included
(train on 5 tap dies, test on the other 5)."""
import numpy as np, pandas as pd, warnings
from sklearn.ensemble import HistGradientBoostingClassifier
warnings.filterwarnings("ignore")
d = pd.read_csv("data/tsmc65/readouts.csv.gz", low_memory=False); d = d[d.is_nominal == 0].copy()
d["lat"] = d.t1 - 5e-6; d["per"] = d.t2 - d.t1; d["width"] = d.tf1 - d.t1
SPIKE = ["lat", "per", "width", "tl_avg", "tl_max", "t6"]; ANALOG = ["vtrip", "vpk", "vidle", "vmin", "vrst", "tcmp", "ttrip"]; SUP = ["qdd_all", "qdd_sp", "ipk"]
F = SPIKE + ANALOG + SUP
d["neuron"] = d.deck + "_r" + d.mc_run.astype(str)
def tapff(l):
    if l.endswith("_tap0") or l.endswith("tap0fF"): return 0
    return int(l.split("_tap")[-1].replace("fF", ""))
tp = d[d.kind == "tap"].copy(); tp["tap"] = tp.label.map(tapff)
tap_dies = sorted(tp["die"].unique()); print("tap dies:", tap_dies, "| tap neurons:", tp.neuron.nunique())
def wide(df, extra=()):
    w = df.pivot_table(index=["neuron", "die", "defect_id"] + list(extra), columns="stim_nA", values=F, aggfunc="first")
    w.columns = ["%s@%d" % (f, int(s)) for f, s in w.columns]; return w.reset_index()
main = wide(d[(d.kind == "main") & (~d.die.isin(tap_dies))])
tw = wide(tp, extra=("tap",))
cols = [c for c in main.columns if "@" in c]
# (1) per-fF shift, healthy, in population sigma (population = healthy MC-corner main neurons, stim-wise)
h = d[(d.kind == "main") & (d.defect_id == "healthy") & (d.corner == "MC")]
sd = {(f, s): h[h.stim_nA == s][f].std() for f in F for s in (50, 100, 200, 400)}
hw = tw[tw.defect_id == "healthy"]
base = hw[hw.tap == 0].set_index("neuron")
print("\n(1) shift of each readout per fF of tap capacitance (healthy, in population sigma per fF; strongest 8 of %d)" % len(cols))
sl = {}
for c in cols:
    f, s = c.split("@"); xs, ys = [], []
    for t in (10, 25, 50, 100):
        g = hw[hw.tap == t].set_index("neuron"); i = g.index.intersection(base.index)
        xs += [t] * len(i); ys += list((g.loc[i, c] - base.loc[i, c]).values)
    xs, ys = np.array(xs, float), np.array(ys, float); m = np.isfinite(ys)
    if m.sum() > 20 and sd[(f, int(s))] > 0: sl[c] = np.sum(xs[m] * ys[m]) / np.sum(xs[m] ** 2) / sd[(f, int(s))]
S = pd.Series(sl).sort_values(key=abs, ascending=False)
print("  " + ", ".join("%s %+.2f" % (k, v) for k, v in S.head(8).items()))
print("  -> a 25 fF tap moves the strongest readout by %.1f population sigma; weakest of the useful set by %.2f" % (abs(S.iloc[0]) * 25, abs(S[abs(S) > 0.01].iloc[-1]) * 25))
# (2) detector trained without tap
dies = np.array(sorted(main["die"].unique())); rng = np.random.default_rng(0); rng.shuffle(dies); nva = int(.2 * len(dies))
va_d = set(dies[:nva]); trm = ~main["die"].isin(va_d); vam = main["die"].isin(va_d)
def fit(Xdf, y): return HistGradientBoostingClassifier(max_iter=150, learning_rate=.1, max_leaf_nodes=31, early_stopping=False, random_state=0).fit(Xdf[cols].to_numpy(float), y)
def score(m, Xdf):
    p = np.clip(m.predict_proba(Xdf[cols].to_numpy(float))[:, 1], 1e-6, 1 - 1e-6); return np.log(p / (1 - p))
ym = (main.defect_id != "healthy").astype(int).values
m0 = fit(main[trm.values], ym[trm.values]); thr = np.quantile(score(m0, main[vam.values])[ym[vam.values] == 0], .99)
tw["fault"] = (tw.defect_id != "healthy").astype(int); tw["sc"] = score(m0, tw)
print("\n(2) detector trained with NO tap, applied to tapped neurons (threshold = 1 %% false reject at tap 0 on held-out main dies)")
for t in (0, 10, 25, 50, 100):
    g = tw[(tw.tap == t) & (tw.fault == 0)]; line = "  tap %3d fF: healthy rejected %5.1f %% (n=%d)" % (t, (g.sc > thr).mean() * 100, len(g))
    if t in (0, 25): gd = tw[(tw.tap == t) & (tw.fault == 1)]; line += " | defects missed %5.1f %% (n=%d)" % ((gd.sc <= thr).mean() * 100, len(gd))
    print(line)
# (3) tap-aware: train with tapped data of 5 tap dies, test on the other 5
half = tap_dies[:5]; te_d = tap_dies[5:]
trt = tw[tw.die.isin(half)]; tet = tw[tw.die.isin(te_d)]
mA = fit(pd.concat([main[trm.values], trt]), np.concatenate([ym[trm.values], trt.fault.values]))
thrA = np.quantile(score(mA, main[vam.values])[ym[vam.values] == 0], .99); tet = tet.assign(sc2=score(mA, tet), sc1=score(m0, tet))
print("\n(3) same detector retrained with tapped examples (5 tap dies), tested on the other 5 tap dies")
for t in (0, 10, 25, 50, 100):
    g = tet[(tet.tap == t) & (tet.fault == 0)]
    line = "  tap %3d fF: healthy rejected  no-tap detector %5.1f %%  ->  tap-aware %5.1f %%" % (t, (g.sc1 > thr).mean() * 100, (g.sc2 > thrA).mean() * 100)
    if t in (0, 25): gd = tet[(tet.tap == t) & (tet.fault == 1)]; line += " | defects missed %5.1f %% -> %5.1f %%" % ((gd.sc1 <= thr).mean() * 100, (gd.sc2 <= thrA).mean() * 100)
    print(line)
