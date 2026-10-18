"""Extra-readout experiment: same neurons (same dies/seeds/dvt) as the main run, restricted to healthy + the 4 hidden defects,
with added supply-current and internal-node readouts. Usage: python gf180_supply_supplement_generator.py --out <output folder> --dies 40 --healthy 40 --per-defect 3 --workers 20"""
import re
import gf180_generator as g

HID = {"mna_on", "mn2_off", "mna_off", "mn3_off"}
EXTRA = ["qdd_all", "qdd_sp", "ipk", "tail_t", "n3_t", "mid_t", "n4_t", "n3min", "midpk", "tailmax", "tailmin", "n4pk"]
if EXTRA[0] not in g.MEAS_NAMES:
    g.MEAS_NAMES.extend(EXTRA)

_orig_build, _orig_make = g.build_netlist, g.make_tasks

def build(*a, **k):
    net = _orig_build(*a, **k)
    W = re.search(r"\.tran 20n (\d+)u", net).group(1)
    add = [f"meas tran qdd_all integ i(vdd) from=5u to={W}u", "meas tran qdd_sp integ i(vdd) from=5u to=15u", "meas tran ipk min i(vdd)",
           "meas tran tail_t find v(tail) when v(rqst)=1.65 rise=1", "meas tran n3_t find v(n3) when v(rqst)=1.65 rise=1",
           "meas tran mid_t find v(mid) when v(rqst)=1.65 rise=1", "meas tran n4_t find v(n4) when v(rqst)=1.65 rise=1",
           "meas tran n3min min v(n3)", "meas tran midpk max v(mid)", "meas tran tailmax max v(tail)", "meas tran tailmin min v(tail)", "meas tran n4pk max v(n4)"]
    marker = "meas tran vrst find v(vm) when v(vspike)=1.65 fall=1"
    return net.replace(marker, marker + "\n" + "\n".join(add))

def make(args):
    return [t for t in _orig_make(args) if t["defect"] is None or g.defect_id(*t["defect"]) in HID]

g.build_netlist, g.make_tasks = build, make

if __name__ == "__main__":
    g.main()
