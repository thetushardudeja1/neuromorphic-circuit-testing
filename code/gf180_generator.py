"""Local dataset generator: I&F neuron on the open GF180MCU PDK, simulated with ngspice.

One ngspice process = one neuron (healthy or with one defect) through all stimuli.
Die = shared global process draw (explicit numbers drawn here from the PDK's own distributions) ;
local mismatch = explicit per-transistor Vth shifts drawn here with the PDK's own Pelgrom formula
(sigma = 0.7071 * par_vth * 1e-6 / sqrt(Leff*Weff), GF180 sm141064.ngspice nmos_3p3_sab / pmos_3p3_sab).
Everything is logged (neuron_parameters.jsonl), so any die/neuron can be re-simulated exactly (ngspice cannot replay seeds).

Topology: El-Sayed et al. IOLTS 2020 Fig.1 (= Serrano-Gotarredona TCAS-I 2006 Fig.10).
Defect rules: stuck-on = 10 ohm drain-source short; open gate = gate cut from its net and driven by
V(g,s)=0.5*V(d,s) (El-Sayed 2020 / Esen 2016); capacitor / output resistor +-50 %.

usage: python gf180_generator.py --out DIR [--dies N] [--healthy H] [--per-defect M] [--workers W] [--limit-tasks T]
"""
import argparse, json, math, os, random, re, subprocess, sys, time, csv
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
from circuit_definition import DEVICES, DEFECTS, DESIGN, defect_id   # topology + defect list shared with the HSPICE flow

NGSPICE = os.environ.get("NGSPICE_EXE", "C:/Users/TUSHAR/anaconda3/envs/ngspice_env/Library/bin/ngspice_con.exe")
PDK = "gf180_models/models/ngspice/sm141064.ngspice"      # relative to HERE (cwd of every ngspice process)
DESIGN_INC = "gf180_models/models/ngspice/design.ngspice"
STIMULI = [50e-9, 100e-9, 200e-9, 400e-9]
CORNER_CYCLE = ["MC", "MC", "MC", "MC", "TT", "SS", "FF", "MC"]
SHORT_WINDOW = {"mp1_on", "mp1_off", "mnb_on", "mpr_on", "mi1_off"}             # saturated / chattering defects: simulate only 7 us
L_UM, WN_UM, WP_UM = 0.5, 2.0, 4.0
PAR_VTH = {"n": 0.007148, "p": 0.00666}                    # GF180 par_vth (nmos_3p3_sab / pmos_3p3_sab)
MEAS_NAMES = ["t1", "t2", "t3", "t6", "t12", "tf1", "tl_avg", "tl_min", "tl_max", "tcmp", "ttrip",
              "vtrip", "vpk", "vidle", "vmin", "vrst"]

# ---------------------------------------------------------------------------------------------
def sigma_vth(kind, w_um, l_um=L_UM):
    leff = (l_um - 0.15) * 1e-6
    weff = (w_um + 0.1) * 1e-6
    return 0.7071 * PAR_VTH[kind] * 1e-6 / math.sqrt(leff * weff)


def cap_c0(side_um):          # GF180 mim_1p0fF: (cox*area + capsw*perimeter)
    s = side_um * 1e-6
    return 0.987e-3 * s * s + 3.3e-10 * 4 * s


def side_for_cap(c):
    a, b = 0.987e-3, 4 * 3.3e-10
    s = (-b + math.sqrt(b * b + 4 * a * c)) / (2 * a)
    return s * 1e6


_STAT_CACHE = {}
def stat_blocks():
    """Bodies of the PDK's `statistical` and `mimcap_statistical` libs (parsed once)."""
    if not _STAT_CACHE:
        txt = open(os.path.join(HERE, PDK), encoding="latin-1").read()
        for name in ("statistical", "mimcap_statistical"):
            m = re.search(r"^\.lib\s+%s\s*$(.*?)^\.endl" % name, txt, re.S | re.M | re.I)
            _STAT_CACHE[name] = m.group(1)
    return _STAT_CACHE


def die_global_lib(seed):
    """Patched copy of the PDK statistical libs with every agauss(m,s,n) replaced by one explicit draw."""
    rng = random.Random(seed)
    draws = {}
    def rep(match):
        mean, spread, nsig = (float(x) for x in match.group(1).split(","))
        v = rng.gauss(mean, spread / nsig)
        return repr(v)
    out = []
    for name, body in stat_blocks().items():
        body = body.replace("'sm141064.ngspice'", "'%s'" % PDK)
        body = re.sub(r"agauss\(([^)]*)\)", rep, body, flags=re.I)
        out.append(body)
    return "\n".join(out)


def build_netlist(corner, die_seed, neuron, amp_list, window_us, solver_opts=""):
    """neuron = dict(defect=None|(dev,kind), dvt={dev: volts})."""
    D = DESIGN
    defect = neuron["defect"]
    dev_fault, cm_c, rout = {}, cap_c0(D["cm_side_um"]) * neuron.get("cm_scale", 1.0), D["rout"]
    if defect:
        dev, kind = defect
        if dev == "cm":
            cm_c *= 1.5 if kind == "plus50" else 0.5
        elif dev == "rout":
            rout *= 1.5 if kind == "plus50" else 0.5
        else:
            dev_fault[dev] = kind
    L = []
    a = L.append
    a(f"* GF180 I&F neuron, corner={corner}, defect={defect}")
    a(".option numdgt=7 gmin=1e-12 " + solver_opts)
    a(f".include {DESIGN_INC}")
    if corner == "MC":
        a(".param sw_stat_global=1 sw_stat_mismatch=0")
        a(f".include statdie_{die_seed}.lib")          # written next to the netlist by the caller
    else:
        a(".param sw_stat_global=0 sw_stat_mismatch=0")
        lib = {"TT": ("typical", "mimcap_typical"), "SS": ("ss", "mimcap_ss"), "FF": ("ff", "mimcap_ff")}[corner]
        a(f".lib {PDK} {lib[0]}")
        a(f".lib {PDK} {lib[1]}")
    # transistor wrappers: the PDK's own subcircuit (sm141064.ngspice nmos_3p3_sab) with an explicit Vth shift
    for k, nm in (("n", "nmos_3p3"), ("p", "pmos_3p3")):
        res = "nplus_u_m1" if k == "n" else "pplus_u_m1"
        a(f".subckt {k}m3 d g s b w=10u l=0.28u dvt=0")
        a(f"xr1 d d1 b {res} wr='w' lr=1.78u")
        a(f"xr2 s s1 b {res} wr='w' lr=0.48u")
        a(f"m0 d1 g s1 b {nm} w='w' l='l' as=0 ad=0 ps=0 pd=0 nrd=0 nrs=0 nf=1 sa=0 sb=0 sd=0 delvto='dvt'")
        a(".ends")
    a(f".param vddv={D['vdd']} vrst={D['vreset'] + neuron.get('vrst_shift', 0.0):.5f} "
      f"vrefv={D['vref'] + neuron.get('vref_shift', 0.0):.5f} ibv={D['ibias'] * neuron.get('ib_scale', 1.0):.5g} iamp={amp_list[0]:.4g}")
    a(f"vdd vdd 0 {{vddv}}\nvrs vrst 0 {{vrst}}\nvrf vref 0 {{vrefv}}")
    a(f"xcm vm 0 mim_1p0fF c_length={_side(cm_c):.5f}u c_width={_side(cm_c):.5f}u")
    a("isyn 0 vm pwl(0 0 5u 0 5.01u {iamp} 15u {iamp} 15.01u 0)")
    extra = []
    for name, kind, d, g, s, b in DEVICES:
        model = "nm3" if kind == "n" else "pm3"
        w = WN_UM if kind == "n" else WP_UM
        gate = g
        f = dev_fault.get(name)
        if f == "on":
            extra.append(f"rsc_{name} {d} {s} 10")
        elif f == "off":
            gate = f"gf_{name}"
            extra.append(f"bgf_{name} {gate} 0 v=v({s})+0.5*(v({d})-v({s}))")
        dvt = neuron["dvt"][name]
        a(f"x{name} {d} {gate} {s} {b} {model} w={w}u l={L_UM}u dvt={dvt:.6e}")
    L += extra
    if neuron.get("tap_cf"):      # readout tap on the membrane node: multiplexer on-resistance + ADC input capacitance
        a("rtap vm tapn 1k")
        a(f"ctap tapn 0 {neuron['tap_cf']:.4g}")
    a("ib vdd nb {ibv}")
    a(f"rrq rqst 0 {D['rrq']:.4g}\ncrq rqst 0 {D['crq']:.4g}")
    a(f"rout vspike 0 {rout:.6g}")
    a("beack acki 0 v={vddv*(1-0.5*(1+tanh(40*(v(rqst)-vddv/2))))}")
    a(f"rd acki ack {D['ack_delay_r']:.4g}\ncd ack 0 {D['ack_delay_c']:.4g}")
    a(".nodeset v(n1)=3.3 v(n2)=0 v(n3)=3.3 v(n4)=0 v(ack)=3.3 v(acki)=3.3 v(cl)=2.0 v(nb)=0.8 v(mid)=0 v(pm)=3.3")
    a(".ic v(vm)=1.1")
    a(f".tran 20n {window_us}u")
    tail0 = window_us - 2
    a(".control\nset noaskquit")
    for i, amp in enumerate(amp_list):
        if i > 0:
            a(f"alterparam iamp = {amp:.4g}\nreset")
        a("run")
        a(f"echo STIM {i}")
        a("meas tran t1 when v(vspike)=1.65 rise=1")
        a("meas tran t2 when v(vspike)=1.65 rise=2")
        a("meas tran t3 when v(vspike)=1.65 rise=3")
        a("meas tran t6 when v(vspike)=1.65 rise=6")
        a("meas tran t12 when v(vspike)=1.65 rise=12")
        a("meas tran tf1 when v(vspike)=1.65 fall=1")
        a(f"meas tran tl_avg avg v(vspike) from={tail0}u to={window_us}u")
        a(f"meas tran tl_min min v(vspike) from={tail0}u to={window_us}u")
        a(f"meas tran tl_max max v(vspike) from={tail0}u to={window_us}u")
        a("meas tran tcmp trig v(rqst) val=1.65 rise=1 targ v(vspike) val=1.65 rise=1")
        a("meas tran ttrip trig v(vm) val=1.6 rise=1 targ v(rqst) val=1.65 rise=1")
        a("meas tran vtrip find v(vm) when v(n1)=3.0 fall=1")
        a("meas tran vpk max v(vm)")
        a("meas tran vidle find v(vm) at=4.9u")
        a("meas tran vmin min v(vm)")
        a("meas tran vrst find v(vm) when v(vspike)=1.65 fall=1")
    a("quit\n.endc\n.end")
    return "\n".join(L) + "\n"


def _side(c):
    return side_for_cap(c)


NUM = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
def parse_output(text, n_stim):
    rows = [dict() for _ in range(n_stim)]
    cur = -1
    for line in text.splitlines():
        m = re.match(r"\s*STIM\s+(\d+)", line)
        if m:
            cur = int(m.group(1))
            continue
        m = re.match(r"\s*(\w+)\s*=\s*(%s)" % NUM, line)
        if m and cur >= 0 and m.group(1) in MEAS_NAMES:
            rows[cur][m.group(1)] = float(m.group(2))
    return rows


def run_task(task):
    """Simulate one neuron through all stimuli. Returns (task_id, rows, window, seconds, status).
    Attempt 1: default solver settings (240 s limit). If it hangs (rare numerical loop, e.g. some open-gate
    defects at unlucky mismatch draws): attempt 2 with relaxed tolerances (reltol=0.01 itl4=100, 600 s limit),
    status 'ok_relaxed'. If that also fails the task is reported as FAIL (never crashes the run)."""
    t0 = time.time()
    tid = task["id"]
    try:
        d = os.path.join(task["outdir"], "work", task["die_dir"])
        os.makedirs(d, exist_ok=True)
        window = 7 if (task["defect"] and defect_id(*task["defect"]) in SHORT_WINDOW) else 25
        if task["corner"] == "MC":
            libpath = os.path.join(d, f"statdie_{task['die_seed']}.lib")
            if not os.path.exists(libpath):
                open(libpath, "w").write(die_global_lib(task["die_seed"]))
        status = "FAIL"
        rows = [dict() for _ in STIMULI]
        for attempt, (opts, limit, label) in enumerate((("", 240, "ok"), ("reltol=0.01 itl4=100", 600, "ok_relaxed"))):
            net = build_netlist(task["corner"], task["die_seed"], task, STIMULI, window, opts)
            cir = os.path.join(d, f"n{task['nid']:05d}.cir")
            open(cir, "w").write(net)
            try:
                r = subprocess.run([NGSPICE, "-b", os.path.relpath(cir, HERE).replace("\\", "/")], cwd=HERE,
                                   capture_output=True, text=True, timeout=limit)
            except subprocess.TimeoutExpired:
                status = "FAIL:timeout%d" % attempt
                continue
            out = r.stdout + r.stderr
            rows = parse_output(out, len(STIMULI))
            if all("tl_avg" in x for x in rows):
                status = label
                break
            status = "FAIL:incomplete " + " ".join(out[-150:].split())
        return tid, rows, window, time.time() - t0, status
    except Exception as e:            # a single bad task must never end the run
        return tid, [dict() for _ in STIMULI], 25, time.time() - t0, "FAIL:exception %r" % (e,)


SIGMA_CM = 0.025          # GF180 global MIM spread: mc_c_cox_1p0fF = N(0, 0.025/3) * cap_mc_skew(3) -> 2.5 % (1 sigma)
SIGMA_VTH_N = sigma_vth("n", WN_UM)
DRIFT_K = [0.5, 1, 2, 3, 5, 8, 12, 20]      # drift size in units of the measured/PDK sigma


def _dvt(rng):
    return {name: rng.gauss(0, sigma_vth(kind, WN_UM if kind == "n" else WP_UM)) for name, kind, *_ in DEVICES}


def make_tasks(args):
    tasks, nid = [], 0
    main = {}            # lookup for matched extension tasks: (die, defect or None, j) -> task
    def add(**kw):
        nonlocal nid
        kw.setdefault("kind", "main"); kw.setdefault("variant", "")
        t = dict(nid=nid, outdir=args.out, **kw)
        t["id"] = "%s_d%05d_n%06d" % (t["kind"], t["die"], nid)
        t["die_dir"] = "die_%05d" % t["die"]
        t["die_seed"] = 10_000 + t["die"]
        t["corner"] = CORNER_CYCLE[t["die"] % len(CORNER_CYCLE)]
        tasks.append(t); nid += 1
        return t
    dies = range(args.first_die, args.first_die + args.dies)
    for die in dies:
        rng = random.Random(77_000_000 + die)
        slots = [None] * args.healthy
        for dev, kind in DEFECTS:
            slots += [(dev, kind)] * args.per_defect
        count = {}
        for defect in slots:
            j = count.get(defect, 0); count[defect] = j + 1
            main[(die, defect, j)] = add(die=die, defect=defect, dvt=_dvt(rng))
    if not args.extensions:
        return tasks
    base0 = {name: 0.0 for name, *_ in DEVICES}
    # (1) sensitivity: nominal TT neuron, one parameter nudged at a time (finite-difference steps)
    sens = [("base", {})]
    for name, *_ in DEVICES:
        for sgn in (+1, -1):
            sens.append((f"dvt_{name}_{'+' if sgn > 0 else '-'}10mV", {"dvt": (name, sgn * 0.010)}))
    for lab, key, step in (("cm", "cm_scale", 0.02), ("ib", "ib_scale", 0.05), ("vref", "vref_shift", 0.010), ("vrst", "vrst_shift", 0.010)):
        for sgn in (+1, -1):
            sens.append((f"{lab}_{'+' if sgn > 0 else '-'}", {key: (1.0 if "scale" in key else 0.0) + sgn * step}))
    for lab, mod in sens:
        dvt = dict(base0)
        extra = {}
        for k, v in mod.items():
            if k == "dvt":
                dvt[v[0]] = v[1]
            else:
                extra[k] = v
        t = add(die=900_000, defect=None, dvt=dvt, kind="sens", variant=lab, **extra)
        t["corner"] = "TT"
    # (2) drift sweeps in sigma units on dies with a statistical global draw
    mc_dies = [d for d in range(args.first_die, args.first_die + args.dies) if CORNER_CYCLE[d % len(CORNER_CYCLE)] == "MC"][:40]
    for die in mc_dies:
        rng = random.Random(88_000_000 + die)
        for param in ("cm", "mn1"):
            for k in DRIFT_K:
                for sgn in (+1, -1):
                    dvt = _dvt(rng)
                    extra = {}
                    if param == "cm":
                        extra["cm_scale"] = 1 + sgn * k * SIGMA_CM
                    else:
                        dvt["mn1"] += sgn * k * SIGMA_VTH_N
                    add(die=die, defect=None, dvt=dvt, kind="drift", variant=f"{param}_{'+' if sgn > 0 else '-'}{k}sig", **extra)
    # (3) tap loading: matched to main neurons of the first 20 dies
    for die in range(args.first_die, args.first_die + min(20, args.dies)):
        for j in range(min(5, args.healthy)):
            m = main[(die, None, j)]
            for cf in (10e-15, 25e-15, 50e-15, 100e-15):
                add(die=die, defect=None, dvt=m["dvt"], kind="tap", variant=f"tap{int(cf*1e15)}fF_h{j}", tap_cf=cf)
        if args.per_defect >= 1:
            for defect in DEFECTS:
                m = main[(die, defect, 0)]
                add(die=die, defect=defect, dvt=m["dvt"], kind="tap", variant="tap25fF_def", tap_cf=25e-15)
    return tasks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--dies", type=int, default=280)
    ap.add_argument("--first-die", type=int, default=0)
    ap.add_argument("--healthy", type=int, default=40)
    ap.add_argument("--per-defect", type=int, default=3)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit-tasks", type=int, default=0)
    ap.add_argument("--extensions", action="store_true", help="add sensitivity, drift and tap task groups")
    ap.add_argument("--kinds", default="main,sens,drift,tap", help="only run these task kinds")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    tasks = [t for t in make_tasks(args) if t["kind"] in args.kinds.split(",")]
    if args.limit_tasks:
        tasks = tasks[: args.limit_tasks]
    done_path = os.path.join(args.out, "tasks_done.txt")
    done = set(open(done_path).read().split()) if os.path.exists(done_path) else set()
    todo = [t for t in tasks if t["id"] not in done]
    print(f"{len(tasks)} tasks, {len(done)} already done, {len(todo)} to run, workers={args.workers}", flush=True)
    csv_path = os.path.join(args.out, "readouts.csv")
    new = not os.path.exists(csv_path)
    fcsv = open(csv_path, "a", newline="")
    wr = csv.writer(fcsv)
    if new:
        wr.writerow(["task", "kind", "variant", "die", "corner", "neuron", "defect_dev", "defect_kind", "defect_id", "stim_nA", "window_us"] + MEAS_NAMES)
    fman = open(os.path.join(args.out, "neuron_parameters.jsonl"), "a")
    fdone = open(done_path, "a")
    stop = os.path.join(args.out, "STOP")
    t_start, n_done, n_fail = time.time(), 0, 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {}
        it = iter(todo)
        def submit():
            if os.path.exists(stop):
                return False
            try:
                t = next(it)
            except StopIteration:
                return False
            futs[ex.submit(run_task, t)] = t
            return True
        for _ in range(args.workers * 2):
            if not submit():
                break
        while futs:
            for f in as_completed(list(futs)):
                t = futs.pop(f)
                try:
                    tid, rows, window, secs, status = f.result()
                except Exception as e:
                    tid, rows, window, secs, status = t["id"], [dict() for _ in STIMULI], 25, 0.0, "FAIL:worker %r" % (e,)
                dev, kind = t["defect"] if t["defect"] else ("", "")
                for i, row in enumerate(rows if status.startswith("ok") else []):
                    wr.writerow([tid, t["kind"], t["variant"], t["die"], t["corner"], t["nid"], dev, kind, defect_id(dev, kind) if dev else "healthy",
                                 STIMULI[i] * 1e9, window] + [row.get(m, "") for m in MEAS_NAMES])
                fcsv.flush()
                fman.write(json.dumps(dict(task=tid, kind=t["kind"], variant=t["variant"], extra={k: t[k] for k in ("cm_scale", "ib_scale", "vref_shift", "vrst_shift", "tap_cf") if k in t}, die=t["die"], corner=t["corner"], die_seed=t["die_seed"], neuron=t["nid"],
                                           defect=t["defect"], dvt=t["dvt"], window_us=window, seconds=round(secs, 2), status=status)) + "\n")
                fman.flush()
                if status.startswith("ok"):
                    fdone.write(tid + "\n")
                    fdone.flush()
                    n_done += 1
                else:
                    n_fail += 1
                if (n_done + n_fail) % 25 == 0:
                    el = time.time() - t_start
                    print(f"[{el/60:.1f} min] done {n_done} fail {n_fail}  rate {(n_done+n_fail)/el*3600:.0f} neurons/h", flush=True)
                submit()
                break
    print(f"finished: {n_done} ok, {n_fail} failed, {(time.time()-t_start)/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
