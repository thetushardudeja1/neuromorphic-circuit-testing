"""Cascade and calibration study. Study 4: cost-ordered cascade (spikes first, spike+Vm+supply only for uncertain neurons) - miss vs share of neurons escalated, at 1 % overall false reject,
at a production-like 10 % faulty mix.  Study 5: does 1 % false reject hold per corner / per die with ONE threshold, and what does per-corner calibration do?
TSMC 65 nm, die-based splits (mean of 3)."""
import warnings, time
import numpy as np, pandas as pd
import dataset_loader as cw
warnings.filterwarnings("ignore")
w = cw.tsmc(); y = (w.defect_id != "healthy").astype(int).values; corner = w.corner.values; die = w["die"].values
XA = w[cw.cols(w, cw.SPIKE)].to_numpy(float); XC = w[cw.cols(w, cw.SPIKE + cw.ANALOG + cw.SUP)].to_numpy(float)
PREV = 0.10
def wts(mask):                      # re-weight a set to PREV faulty
    h, f = (mask & (y == 0)).sum(), (mask & (y == 1)).sum(); return np.where(y == 0, (1 - PREV) / h, PREV / f) * mask
def wq(v, wt, q):                   # weighted quantile
    o = np.argsort(v); c = np.cumsum(wt[o]); c /= c[-1]; return v[o][min(np.searchsorted(c, q), len(v) - 1)]
grid = [0.02, 0.05, 0.10, 0.20, 0.40]
agg = {g: [] for g in grid + [1.0]}; e5 = []
for sd in range(3):
    tr, va, te = cw.split(w, sd)
    mA = cw.hgb().fit(XA[tr], y[tr]); sA = cw.logit(mA.predict_proba(XA)[:, 1])
    mC = cw.hgb().fit(XC[tr], y[tr]); sC = cw.logit(mC.predict_proba(XC)[:, 1])
    wv, wtt = wts(va), wts(te); hv = va & (y == 0)
    t_hi = np.quantile(sA[hv], .999)
    for x in grid + [1.0]:
        if x < 1:
            t_lo = wq(sA[va], wv[va], 1 - x - wv[va][sA[va] > t_hi].sum() / wv[va].sum()) if False else None
        # escalated set = scores in (t_lo, t_hi]; choose t_lo so escalated weighted mass on validation = x
        if x == 1.0: E_va, E_te = np.ones_like(va), np.ones_like(te); fault_hi_va = np.zeros_like(va); fault_hi_te = np.zeros_like(te)
        else:
            sv = sA[va]; ws = wv[va]; o = np.argsort(-sv); cum = np.cumsum(ws[o]) / ws.sum()
            above = ws[sv > t_hi].sum() / ws.sum(); k = np.searchsorted(cum, above + x); t_lo = sv[o][min(k, len(sv) - 1)]
            E_va = (sA > t_lo) & (sA <= t_hi); E_te = E_va.copy(); fault_hi_va = sA > t_hi; fault_hi_te = sA > t_hi
        cand = np.sort(sC[va & E_va & (y == 0)])
        best = None
        for t3 in np.concatenate([cand[::max(1, len(cand) // 300)], [np.inf]]):
            dec = fault_hi_va | (E_va & (sC > t3)); fr = (dec & hv).sum() / hv.sum()
            if fr <= 0.01: best = t3; break
        dec = fault_hi_te | (E_te & (sC > best)); miss = ((~dec) & te & (y == 1)).sum() / (te & (y == 1)).sum() * 100; fr = (dec & te & (y == 0)).sum() / (te & (y == 0)).sum() * 100
        esc = (E_te * wtt).sum() / wtt.sum() * 100
        agg[x].append((esc, miss, fr))
    # ---- Study 5 (model C, one global threshold)
    thr = np.quantile(sC[hv], .99); r = {}
    for c in ["MC", "TT", "SS", "FF"]:
        mk = te & (corner == c)
        thr_c = np.quantile(sC[va & (y == 0) & (corner == c)], .99)
        r[c] = ((sC[mk & (y == 0)] > thr).mean() * 100, (sC[mk & (y == 1)] <= thr).mean() * 100, (sC[mk & (y == 0)] > thr_c).mean() * 100, (sC[mk & (y == 1)] <= thr_c).mean() * 100)
    frd = pd.Series(sC[te & (y == 0)] > thr).groupby(die[te & (y == 0)]).mean() * 100
    e5.append((r, frd.std(), (frd > 3).mean() * 100))
print("=== Study 4: cascade (10%% faulty mix). Columns: share of neurons that get the supply+Vm stage | missed faulty | overall false reject (mean of 3 splits) ===")
for x in grid + [1.0]:
    a = np.array(agg[x]).mean(0); print("  escalate target %4.0f%%  -> actually %5.1f%% escalated | miss %5.1f%% | FR %.2f%%" % (x * 100, a[0], a[1], a[2]))
print("\n=== Study 5: one global threshold (1%% FR on pooled validation) - false reject / miss per corner on test dies, and with per-corner calibration ===")
for c in ["MC", "TT", "SS", "FF"]:
    v = np.array([e[0][c] for e in e5]).mean(0); print("  %-3s  global thr: FR %5.2f%% miss %5.2f%%   | per-corner thr: FR %5.2f%% miss %5.2f%%" % (c, *v))
print("  spread of false-reject rate between dies (sd of per-die FR): %.2f points; share of dies with FR > 3%%: %.1f%%" % (np.mean([e[1] for e in e5]), np.mean([e[2] for e in e5])))
