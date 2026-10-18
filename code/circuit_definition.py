"""Builds HSPICE decks of the I&F neuron with (optionally) ONE injected defect.

Topology: El-Sayed et al., IOLTS 2020, Fig. 1 (= Serrano-Gotarredona et al., TCAS-I 2006, Fig. 10).
Devices: TSMC 65nm LP 3.3V MOS (nch_33_mac / pch_33_mac) and MIM capacitor (mimcap_sin).

Defect rules (El-Sayed 2020 Sec. III-A, citing Esen et al. ITC 2016):
  stuck-on  : 10 ohm short between drain and source
  stuck-off : open gate, implemented with a weak gate drive V(g,s) = 0.5 * V(d,s)
  passives  : +-50 % (capacitor, resistor)
One defect at a time; 21 transistors x 2 + capacitor x 2 + resistor x 2 = 46 defects.

Values that are NOT from a paper (device sizes, bias current, reference/reset levels, output and
Rqst load, Ack delay, input pulse timing) are design choices and are listed in DESIGN below.
"""

import os
# Licensed foundry model library (not included): set TSMC65_LIB to its path to rebuild the TSMC decks.
LIB = os.environ.get("TSMC65_LIB", "<path-to-licensed-TSMC65-HSPICE-model-library>")

# published design values (2006 paper / El-Sayed 2020) and our design choices
DESIGN = dict(
    vdd=3.3,          # El-Sayed 2020: supply 3.3 V
    cm_side_um=11.3,  # MIM side giving ~140 fF capacitor (2006 paper: Cm = 140 fF); area from PDK formula
    vreset=1.1,       # design choice; only |Eref - Ereset| = 0.5 V is published (2006 paper)
    vref=1.6,         # design choice (same note)
    ibias=10e-6,      # design choice (comparator bias reference)
    lmin=0.5e-6, wn=2e-6, wp=4e-6,   # design choice (not published)
    iamp=100e-9,      # El-Sayed 2020 Fig 2a: amplitude read from axis (0.1-0.2 uA), 10 us pulse
    tdel=5e-6, twid=10e-6, tstop=25e-6,
    rout=20e3,        # design choice: output load resistor
    rrq=100e3, crq=20e-15,   # design choice: arbiter model on Rqst
    ack_delay_r=1e3, ack_delay_c=3e-12,   # design choice: Ack follows Rqst after ~3 ns ("a few ns", 2006 paper)
)

# (name, kind, drain, gate, source, bulk)
DEVICES = [
    ("mp1", "p", "x1", "n1", "vdd", "vdd"),
    ("mp2", "p", "vm", "n4", "x1", "vdd"),
    ("mn4", "n", "vm", "n4", "vrst", "0"),
    ("mc1", "p", "cl", "cl", "vdd", "vdd"),
    ("mc2", "p", "n1", "cl", "vdd", "vdd"),
    ("mn5", "n", "cl", "vref", "tail", "0"),
    ("mn6", "n", "n1", "vm", "tail", "0"),
    ("mnr", "n", "nb", "nb", "0", "0"),
    ("mn1", "n", "tail", "nb", "0", "0"),
    ("mn2", "n", "tail", "n4", "0", "0"),
    ("mn3", "n", "tail", "n2", "0", "0"),
    ("mi1", "p", "n2", "n1", "vdd", "vdd"),
    ("mi2", "n", "n2", "n1", "0", "0"),
    ("mp4", "p", "n3", "n2", "vdd", "vdd"),
    ("mna", "n", "n3", "ack", "mid", "0"),
    ("mnb", "n", "mid", "n2", "0", "0"),
    ("mpr", "p", "rqst", "n3", "vdd", "vdd"),
    ("mpa", "p", "pm", "n3", "vdd", "vdd"),
    ("mp5", "p", "n4", "ack", "pm", "vdd"),
    ("mnc", "n", "n4", "ack", "0", "0"),
    ("mp3", "p", "vspike", "ack", "vdd", "vdd"),
]

DEFECTS = ([(d[0], "on") for d in DEVICES] + [(d[0], "off") for d in DEVICES]
           + [("cm", "plus50"), ("cm", "minus50"), ("rout", "plus50"), ("rout", "minus50")])


def defect_id(dev, kind):
    return f"{dev}_{kind}"


def build(defect=None, mc_runs=None, tag="neuron", tstop=None, probes=True, tap_cf=None, tap_ron=1e3):
    """Return deck text. defect = (device, kind) or None. mc_runs = int for Monte Carlo.
    tap_cf: ADC input capacitance (F) of the readout tap on Vm (None = no tap); tap_ron: multiplexer on-resistance."""
    D = DESIGN
    tstop = tstop or D["tstop"]
    dev_fault = {}
    cm_mf, rout = 1.0, D["rout"]
    if defect:
        dev, kind = defect
        if dev == "cm":
            cm_mf = 1.5 if kind == "plus50" else 0.5
        elif dev == "rout":
            rout = D["rout"] * (1.5 if kind == "plus50" else 0.5)
        else:
            dev_fault[dev] = kind
    L = []
    a = L.append
    a(f"* {tag}: I&F neuron (El-Sayed 2020 Fig.1), TSMC 65nm LP 3.3V; defect = {defect}")
    a(".option post=2 ingold=2 numdgt=7")
    a(".temp 25")
    a(".param par1fn_mc=0 par1fn_p_mc=0")
    if mc_runs:
        for lib in ("mc_33", "stat", "MC_MIM", "stat_mim"):
            a(f".lib '{LIB}' {lib}")
    else:
        for lib in ("TT_33", "TT_MIM"):
            a(f".lib '{LIB}' {lib}")
    a(f".param vddv={D['vdd']} vrst={D['vreset']} vrefv={D['vref']} ibv={D['ibias']:.4g} "
      f"iamp={D['iamp']:.4g} tdel={D['tdel']:.4g} twid={D['twid']:.4g}")
    a(f".param lmin={D['lmin']:.4g} wn={D['wn']:.4g} wp={D['wp']:.4g}")
    a("vdd vdd 0 'vddv'\nvrs vrst 0 'vrst'\nvrf vref 0 'vrefv'")
    a(f"xcm vm 0 mimcap_sin lt={D['cm_side_um']}u wt={D['cm_side_um']}u mf={cm_mf}")
    a("isyn 0 vm pwl(0 0 'tdel' 0 'tdel+10n' 'iamp' 'tdel+twid' 'iamp' 'tdel+twid+10n' 0)")
    extra = []
    for name, kind, d, g, s, b in DEVICES:
        model = "nch_33_mac" if kind == "n" else "pch_33_mac"
        w = "wn" if kind == "n" else "wp"
        gate = g
        f = dev_fault.get(name)
        if f == "on":
            extra.append(f"rsc_{name} {d} {s} 10")
        elif f == "off":
            gate = f"gf_{name}"
            extra.append(f"eof_{name} {gate} {s} {d} {s} 0.5")
        a(f"x{name} {d} {gate} {s} {b} {model} l=lmin w={w}")
    L += extra
    if tap_cf is not None:   # readout tap on the membrane node: multiplexer on-resistance + ADC input capacitance
        a(f"rtap vm tapn {tap_ron:.4g}")
        a(f"ctap tapn 0 {tap_cf:.4g}")
    a("ib vdd nb 'ibv'")
    a(f"rrq rqst 0 {D['rrq']:.4g}\ncrq rqst 0 {D['crq']:.4g}")
    a(f"rout vspike 0 {rout:.6g}")
    a("eack acki 0 vol='vddv*(1-0.5*(1+tanh(40*(v(rqst)-vddv/2))))'")
    a(f"rd acki ack {D['ack_delay_r']:.4g}\ncd ack 0 {D['ack_delay_c']:.4g}")
    a(".nodeset v(n1)=3.3 v(n2)=0 v(n3)=3.3 v(n4)=0 v(ack)=3.3 v(acki)=3.3 v(cl)=2.0 v(nb)=0.8 v(mid)=0 v(pm)=3.3")
    a(".ic v(vm)=1.1")
    if probes:
        a(".probe tran v(vm) v(vspike) v(rqst) v(n1) v(n2) v(n4) v(ack)")
    sweep = f" sweep monte={mc_runs}" if mc_runs else ""
    a(f".tran 1n {tstop:.4g}{sweep}")
    a(".meas tran tfs1 when v(vspike)=1.65 rise=1")
    a(".meas tran tfs2 when v(vspike)=1.65 rise=2")
    a(".meas tran tfs1b param='tfs1-tdel'")
    a(".meas tran vtrip find v(vm) when v(n1)=3.0 fall=1")
    a(".end")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    import os, sys
    out = sys.argv[1] if len(sys.argv) > 1 else "decks/defects"
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "healthy.sp"), "w").write(build(None, tag="healthy"))
    for dev, kind in DEFECTS:
        i = defect_id(dev, kind)
        open(os.path.join(out, f"{i}.sp"), "w").write(build((dev, kind), tag=i))
    print(len(DEFECTS), "defects +healthy written to", out)


# ---------------------------------------------------------------------------------------------
# Die builder: N independent neurons that share ONE global process draw (same HSPICE Monte Carlo
# run) and each have their own local mismatch. Used for the large dataset.
# ---------------------------------------------------------------------------------------------
INTERNAL = ["x1", "n1", "n2", "n3", "n4", "cl", "tail", "nb", "mid", "pm", "rqst", "vm", "ack", "acki",
            "vspike", "tapn"]
SHARED = {"vdd", "vrst", "vref", "0"}


def _ren(node, pfx):
    return node if node in SHARED else f"{pfx}{node}"


CORNER_LIBS = {
    "MC": ["mc_33", "stat", "MC_MIM", "stat_mim"],   # global statistical draw per die + local mismatch
    "TT": ["TT_33", "TT_MIM"],                        # lot at typical corner, local mismatch only
    "SS": ["SS_33", "SS_MIM"],                        # lot at slow corner, local mismatch only
    "FF": ["FF_33", "FF_MIM"],                        # lot at fast corner, local mismatch only
}

MEASURES = [  # (name, template) ; {v} = output node, {m} = membrane node, {n1}, {rq}; formats resolved in build_die
    ("t1", "when v({sp})=1.65 rise=1"),
    ("t2", "when v({sp})=1.65 rise=2"),
    ("t3", "when v({sp})=1.65 rise=3"),
    ("t6", "when v({sp})=1.65 rise=6"),
    ("t12", "when v({sp})=1.65 rise=12"),
    ("tf1", "when v({sp})=1.65 fall=1"),
    ("tl_avg", "avg v({sp}) from=23u to=25u"),
    ("tl_min", "min v({sp}) from=23u to=25u"),
    ("tl_max", "max v({sp}) from=23u to=25u"),
    ("tcmp", "trig v({rq}) val=1.65 rise=1 targ v({sp}) val=1.65 rise=1"),
    ("ttrip", "trig v({vm}) val='vrefv' rise=1 targ v({rq}) val=1.65 rise=1"),
    ("vtrip", "find v({vm}) when v({n1})=3.0 fall=1"),
    ("vpk", "max v({vm})"),
    ("vidle", "find v({vm}) at=4.9u"),
    ("vmin", "min v({vm})"),
    ("vrst", "find v({vm}) at='t1_{k}+60n'"),
]


def _block(k, defect, tap_cf, tap_ron):
    """Lines for neuron k (nodes prefixed nK_). Returns lines."""
    D = DESIGN
    p = f"n{k:02d}_"
    R = lambda x: _ren(x, p)
    dev_fault, cm_mf, rout = {}, 1.0, D["rout"]
    if defect:
        dev, kind = defect
        if dev == "cm":
            cm_mf = 1.5 if kind == "plus50" else 0.5
        elif dev == "rout":
            rout = D["rout"] * (1.5 if kind == "plus50" else 0.5)
        else:
            dev_fault[dev] = kind
    L = [f"* neuron {k} defect={defect}"]
    a = L.append
    a(f"x{p}cm {R('vm')} 0 mimcap_sin lt={D['cm_side_um']}u wt={D['cm_side_um']}u mf={cm_mf}")
    a(f"i{p}syn 0 {R('vm')} pwl(0 0 'tdel' 0 'tdel+10n' 'iamp' 'tdel+twid' 'iamp' 'tdel+twid+10n' 0)")
    extra = []
    for name, kind, d, g, s, b in DEVICES:
        model = "nch_33_mac" if kind == "n" else "pch_33_mac"
        w = "wn" if kind == "n" else "wp"
        gate = R(g)
        f = dev_fault.get(name)
        if f == "on":
            extra.append(f"r{p}sc_{name} {R(d)} {R(s)} 10")
        elif f == "off":
            gate = f"{p}gf_{name}"
            extra.append(f"e{p}of_{name} {gate} {R(s)} {R(d)} {R(s)} 0.5")
        a(f"x{p}{name} {R(d)} {gate} {R(s)} {R(b)} {model} l=lmin w={w}")
    L += extra
    if tap_cf is not None:
        a(f"r{p}tap {R('vm')} {R('tapn')} {tap_ron:.4g}")
        a(f"c{p}tap {R('tapn')} 0 {tap_cf:.4g}")
    a(f"i{p}b vdd {R('nb')} 'ibv'")
    a(f"r{p}rq {R('rqst')} 0 {D['rrq']:.4g}\nc{p}rq {R('rqst')} 0 {D['crq']:.4g}")
    a(f"r{p}out {R('vspike')} 0 {rout:.6g}")
    a(f"e{p}ack {R('acki')} 0 vol='vddv*(1-0.5*(1+tanh(40*(v({R('rqst')})-vddv/2))))'")
    a(f"r{p}d {R('acki')} {R('ack')} {D['ack_delay_r']:.4g}\nc{p}d {R('ack')} 0 {D['ack_delay_c']:.4g}")
    a(f".nodeset v({R('n1')})=3.3 v({R('n2')})=0 v({R('n3')})=3.3 v({R('n4')})=0 v({R('ack')})=3.3 "
      f"v({R('acki')})=3.3 v({R('cl')})=2.0 v({R('nb')})=0.8 v({R('mid')})=0 v({R('pm')})=3.3")
    a(f".ic v({R('vm')})=1.1")
    ctx = dict(sp=R("vspike"), vm=R("vm"), n1=R("n1"), rq=R("rqst"), k=f"n{k:02d}")
    for mname, tmpl in MEASURES:
        a(f".meas tran {mname}_n{k:02d} " + tmpl.format(**ctx).replace(f"t1_n{k:02d}", f"t1_n{k:02d}"))
    return L


def build_die(assign, corner="MC", iamp=100e-9, tap_cf=None, tap_ron=1e3, n_dies=20, seed=1, tag="die"):
    """assign: list of N entries, each None (healthy) or (device, kind). One deck = n_dies Monte Carlo
    runs (dies); each die has len(assign) neurons."""
    D = DESIGN
    L = []
    a = L.append
    a(f"* {tag}: {len(assign)}-neuron dies, corner={corner}, iamp={iamp:.4g}, tap={tap_cf}, seed={seed}")
    a(".option post=0 ingold=2 numdgt=6 nopage nomod")
    a(f".option seed={seed}")
    a(".temp 25")
    a(".param par1fn_mc=0 par1fn_p_mc=0")
    for lib in CORNER_LIBS[corner]:
        a(f".lib '{LIB}' {lib}")
    a(f".param vddv={D['vdd']} vrst={D['vreset']} vrefv={D['vref']} ibv={D['ibias']:.4g} "
      f"iamp={iamp:.4g} tdel={D['tdel']:.4g} twid={D['twid']:.4g}")
    a(f".param lmin={D['lmin']:.4g} wn={D['wn']:.4g} wp={D['wp']:.4g}")
    a("vdd vdd 0 'vddv'\nvrs vrst 0 'vrst'\nvrf vref 0 'vrefv'")
    for k, d in enumerate(assign):
        L += _block(k, d, tap_cf, tap_ron)
    a(f".tran 1n {D['tstop']:.4g} sweep monte={n_dies}")
    a(".end")
    return "\n".join(L) + "\n"
