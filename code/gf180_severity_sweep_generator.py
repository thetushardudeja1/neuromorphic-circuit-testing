"""Severity sweep (extension of the catastrophic defect model): same 21 devices, graded severity, 1 stimulus (100 nA), extra readouts (supply, nodes).
 stuck-on short resistance R in {10, 100, 1k, 10k, 100k, 1M} ohm   (10 ohm = El-Sayed 2020 value, the rest is OUR extension)
 open-gate blend b in {1.0, 0.5, 0.25, 0.1}: V(g,s) = (1-b)*V(gate net,s) + b*0.5*V(d,s)   (b = 1 is Esen 2016; b < 1 = partially open, OUR extension)
usage: python gf180_severity_sweep_generator.py --out <output folder> --dies 40 --healthy 40 --workers 20"""
import random, re
import gf180_generator as g

SWEEP_R = [10, 100, 1e3, 1e4, 1e5, 1e6]
SWEEP_B = [1.0, 0.5, 0.25, 0.1]
EXTRA = ["qdd_all", "qdd_sp", "ipk", "tail_t", "n3_t", "mid_t", "n4_t", "n3min", "midpk", "tailmax", "tailmin", "n4pk"]
if EXTRA[0] not in g.MEAS_NAMES:
    g.MEAS_NAMES.extend(EXTRA)
g.STIMULI[:] = [100e-9]
_orig_build = g.build_netlist
GATE = {name: gt for name, kind, d, gt, s, b in g.DEVICES}

def build(corner, die_seed, neuron, amp_list, window_us, solver_opts=""):
    net = _orig_build(corner, die_seed, neuron, amp_list, window_us, solver_opts)
    df = neuron["defect"]
    if df and df[1] == "on" and neuron.get("res"):
        net = re.sub(r"^(rsc_%s \S+ \S+) 10$" % df[0], r"\1 %.6g" % neuron["res"], net, flags=re.M)
    if df and df[1] == "off" and neuron.get("blend") is not None:
        b = neuron["blend"]; dv, gt = df[0], GATE[df[0]]
        net = re.sub(r"^(bgf_%s \S+ 0 v=)v\((\S+)\)\+0\.5\*\(v\((\S+)\)-v\(\S+\)\)$" % dv,
                     lambda m: "%sv(%s)+%.4g*(v(%s)-v(%s))+%.4g*0.5*(v(%s)-v(%s))" % (m.group(1), m.group(2), 1 - b, gt, m.group(2), b, m.group(3), m.group(2)), net, flags=re.M)
    W = re.search(r"\.tran 20n (\d+)u", net).group(1)
    add = [f"meas tran qdd_all integ i(vdd) from=5u to={W}u", "meas tran qdd_sp integ i(vdd) from=5u to=15u", "meas tran ipk min i(vdd)",
           "meas tran tail_t find v(tail) when v(rqst)=1.65 rise=1", "meas tran n3_t find v(n3) when v(rqst)=1.65 rise=1",
           "meas tran mid_t find v(mid) when v(rqst)=1.65 rise=1", "meas tran n4_t find v(n4) when v(rqst)=1.65 rise=1",
           "meas tran n3min min v(n3)", "meas tran midpk max v(mid)", "meas tran tailmax max v(tail)", "meas tran tailmin min v(tail)", "meas tran n4pk max v(n4)"]
    marker = "meas tran vrst find v(vm) when v(vspike)=1.65 fall=1"
    return net.replace(marker, marker + "\n" + "\n".join(add))

def make(args):
    tasks, nid = [], 0
    def add(**kw):
        nonlocal nid
        kw.setdefault("kind", "main"); kw.setdefault("variant", "")
        t = dict(nid=nid, outdir=args.out, **kw); t["id"] = "%s_d%05d_n%06d" % (t["kind"], t["die"], nid); t["die_dir"] = "die_%05d" % t["die"]
        t["die_seed"] = 10_000 + t["die"]; t["corner"] = g.CORNER_CYCLE[t["die"] % len(g.CORNER_CYCLE)]; tasks.append(t); nid += 1
    for die in range(args.first_die, args.first_die + args.dies):
        rng = random.Random(55_000_000 + die)
        for _ in range(args.healthy):
            add(die=die, defect=None, dvt=g._dvt(rng))
        for dev, gt in ((n, None) for n, *_ in g.DEVICES):
            for R in SWEEP_R:
                add(die=die, defect=(dev, "on"), dvt=g._dvt(rng), res=R, variant="R=%g" % R)
            for b in SWEEP_B:
                add(die=die, defect=(dev, "off"), dvt=g._dvt(rng), blend=b, variant="b=%g" % b)
    return tasks

g.build_netlist, g.make_tasks = build, make
if __name__ == "__main__":
    g.main()
