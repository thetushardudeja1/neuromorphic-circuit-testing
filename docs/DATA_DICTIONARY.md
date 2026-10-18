# Data dictionary

All tables are CSV (UTF-8, comma separated, gzip-compressed). An empty cell or NaN means the quantity was not measurable (for example no spike occurred); it is information, not a missing record.
Time columns are in **seconds**, voltages in **volts**, currents in **amperes**, charges in **coulombs**. The supply convention makes `qdd_*` and `ipk` negative (current drawn from Vdd).

## Keys and labels
| Column | Tables | Meaning |
|---|---|---|
| `task` (GF180) / `deck` (TSMC) | all | unique id of the simulation job (GF180: one neuron; TSMC: one deck = one class of one die) |
| `neuron` | GF180 | integer neuron number inside the run |
| `kind` | all | `main` (the dataset), `sens` (sensitivity), `drift` (parametric drift), `tap` (readout-tap loading) |
| `variant` | GF180 | label of the extension condition (empty for `main`); severity sweep: `R=<ohm>` or `b=<blend>` |
| `label` | TSMC | condition label inside the deck (class name, or an extension condition such as `drift_mn1_+10mV`, `healthy_tap25fF`, `dvt_mn2_+10mV`) |
| `die` | all | die index; neurons of one die share the global process draw. The GF180 sensitivity group uses die 900000 |
| `corner` | all | `MC` (global + local variation), `TT`, `SS`, `FF` |
| `seed` | TSMC | HSPICE seed of the deck |
| `mc_run` | TSMC | Monte Carlo run index inside the deck (1 = nominal sample, 2-9 independent draws) |
| `is_nominal` | TSMC | 1 for the nominal sample (exclude from independent-sample statistics) |
| `defect_dev`, `defect_kind` | GF180 | device (or `cm`, `rout`) and `on` / `off` / `plus50` / `minus50`; empty for healthy |
| `defect_id` | all | `healthy` or `<device>_on`, `<device>_off`, `cm_plus50`, `cm_minus50`, `rout_plus50`, `rout_minus50` (46 defects) |
| `stim_nA` | all | input pulse amplitude in nA (50, 100, 200, 400) |
| `window_us` | GF180 | simulated window (25, or 7 for five continuously firing defects) |
| `x_dv_<device>` | TSMC | explicit threshold shift applied to that device in an extension condition (V) |
| `x_cmf`, `x_ibv`, `x_vrefv`, `x_vrst`, `x_tapcf` | TSMC | Cm scale factor, bias current (A), Vref (V), Vreset (V), tap capacitance (F) of an extension condition; empty for the main set |

## Readouts
| Column | Unit | Definition | Tables |
|---|---|---|---|
| `t1, t2, t3, t6, t12` | s | time of the 1st / 2nd / 3rd / 6th / 12th rising edge of the output through 1.65 V | all |
| `tf1` | s | time of the first falling edge through 1.65 V | all |
| `tl_avg, tl_min, tl_max` | V | mean / min / max of the output in the last 2 us of the window | all |
| `tcmp` | s | Rqst rise (1.65 V) to output rise: comparator-to-spike delay | all |
| `ttrip` | s | membrane crossing the reference to Rqst rise | all |
| `vtrip` | V | membrane voltage when the comparator output n1 falls through 3.0 V (the trip instant) | all |
| `vpk` | V | maximum membrane voltage | all |
| `vidle` | V | membrane voltage at 4.9 us (before the pulse) | all |
| `vmin` | V | minimum membrane voltage | all |
| `vrst` | V | membrane voltage right after the first spike (TSMC: 60 ns after t1; GF180: at the first output fall) | all |
| `qdd_all` | C | charge drawn from Vdd, 5-25 us (integral of i(Vdd)) | TSMC, GF180 extra |
| `qdd_sp` | C | same, 5-15 us (the stimulus pulse) | TSMC, GF180 extra |
| `ipk` | A | peak supply current (most negative i(Vdd)) | TSMC, GF180 extra |
| `tail_t, n3_t, mid_t, n4_t` | V | voltage of nodes tail, n3, mid, n4 at the Rqst rise | TSMC, GF180 extra |
| `n3min, midpk, tailmax, tailmin, n4pk` | V | min / max of those nodes over the run | TSMC, GF180 extra |

Derived quantities used in the analyses (not stored): first-spike latency `lat = t1 - 5e-6`, period `per = t2 - t1`, spike width `width = tf1 - t1`.
In TSMC `t12` is mostly empty (fewer than 12 spikes in the window) and the `tl_*` columns depend on the window.

## Other files
- `data/gf180/neuron_parameters.jsonl.gz`: one JSON object per neuron: `task, kind, variant, extra, die, corner, die_seed, neuron, defect, dvt` (threshold shift of each of the 21 transistors, in V), `window_us, seconds, status`.
- `data/gf180/solver_status.csv`: `status` is `ok` or `ok_relaxed` (simulated with relaxed solver tolerances after the default run did not converge; 166 neurons, flagged in `relaxed_solver`).
- `data/tsmc65/raw_hspice_measurements.tgz`: raw HSPICE `.mt*` measure files, `manifest.json` (seed, global draw, full condition list) and `EXIT` of every deck.
- `results/tsmc65_miss_rate_per_defect.csv`, `results/tsmc65_behavioural_fault_model.csv`: per-defect miss rate by readout set, and the derived behaviour class and look-alike group of each defect.
