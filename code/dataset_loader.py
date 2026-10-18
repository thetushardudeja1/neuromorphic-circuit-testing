"""Shared loaders: one row per neuron, columns '<readout>@<stimulus nA>', for TSMC 65 nm (main, independent draws) and GF180."""
import os, numpy as np, pandas as pd
SPIKE = ["lat", "per", "width", "tl_avg", "tl_max", "t6"]; ANALOG = ["vtrip", "vpk", "vidle", "vmin", "vrst", "tcmp", "ttrip"]
SUP = ["qdd_all", "qdd_sp", "ipk"]; NODE = ["tail_t", "n3_t", "mid_t", "n4_t", "n3min", "midpk", "tailmax", "tailmin", "n4pk"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _wide(d, feats, key):
    d = d.copy(); d["lat"] = d.t1 - 5e-6; d["per"] = d.t2 - d.t1; d["width"] = d.tf1 - d.t1
    w = d.pivot_table(index=key, columns="stim_nA", values=[f for f in feats if f in d.columns], aggfunc="first")
    w.columns = ["%s@%d" % (f, int(s)) for f, s in w.columns]; return w.reset_index()
def tsmc():
    c = os.path.join(ROOT, "cache", "tsmc65_wide.pkl")
    if os.path.exists(c): return pd.read_pickle(c)
    d = pd.read_csv(os.path.join(ROOT, "data", "tsmc65", "readouts.csv.gz"), low_memory=False); d = d[(d.kind == "main") & (d.is_nominal == 0)].copy()
    d["neuron"] = d.deck + "_r" + d.mc_run.astype(str)
    w = _wide(d, SPIKE + ANALOG + SUP + NODE, ["neuron", "die", "corner", "defect_id"]); os.makedirs(os.path.dirname(c), exist_ok=True); w.to_pickle(c); return w
def gf180():
    c = os.path.join(ROOT, "cache", "gf180_wide.pkl")
    if os.path.exists(c): return pd.read_pickle(c)
    d = pd.read_csv(os.path.join(ROOT, "data", "gf180", "readouts.csv.gz"), low_memory=False); d = d[d.kind == "main"].drop_duplicates(["task", "stim_nA"])
    w = _wide(d, SPIKE + ANALOG, ["task", "die", "corner", "defect_id"]).rename(columns={"task": "neuron"}); os.makedirs(os.path.dirname(c), exist_ok=True); w.to_pickle(c); return w
def cols(w, fams): return [c for c in w.columns if "@" in c and c.split("@")[0] in fams]
def split(w, seed, tr=.6, va=.2):
    dies = np.array(sorted(w["die"].unique())); np.random.default_rng(100 + seed).shuffle(dies); a, b = int(tr * len(dies)), int((tr + va) * len(dies))
    m = {x: 0 for x in dies[:a]}; m.update({x: 1 for x in dies[a:b]}); m.update({x: 2 for x in dies[b:]}); s = w["die"].map(m).values
    return s == 0, s == 1, s == 2
def hgb(): 
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(max_iter=150, learning_rate=.1, max_leaf_nodes=31, early_stopping=False, random_state=0)
def logit(p): p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p / (1 - p))
def miss_at_1pct(sc, y, va, te):
    thr = np.quantile(sc[va & (y == 0)], .99); return (sc[te & (y == 1)] <= thr).mean() * 100, (sc[te & (y == 0)] > thr).mean() * 100
