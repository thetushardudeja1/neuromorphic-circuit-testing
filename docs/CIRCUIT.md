# Circuit

Source: El-Sayed et al., IOLTS 2020 Fig. 1 = Serrano-Gotarredona et al., TCAS-I 2006 Fig. 10 (positive event block). 21 transistors, Cm, output resistor `rout`.
Device roles were read from the connectivity below; they are descriptive, not taken from a published table.

| Device | Type | Drain | Gate | Source | Bulk | Role |
|---|---|---|---|---|---|---|
| `mp1` | PMOS | x1 | n1 | vdd | vdd | positive-feedback current source (gate n1) |
| `mp2` | PMOS | vm | n4 | x1 | vdd | positive-feedback switch onto Vm (gate n4) |
| `mn4` | NMOS | vm | n4 | vrst | 0 | reset switch, Vm to Vreset (gate n4) |
| `mc1` | PMOS | cl | cl | vdd | vdd | comparator load, diode-connected mirror input |
| `mc2` | PMOS | n1 | cl | vdd | vdd | comparator load, mirror output to n1 |
| `mn5` | NMOS | cl | vref | tail | 0 | comparator input pair, reference side (gate Vref) |
| `mn6` | NMOS | n1 | vm | tail | 0 | comparator input pair, membrane side (gate Vm) |
| `mnr` | NMOS | nb | nb | 0 | 0 | bias mirror reference (diode-connected, Ibias) |
| `mn1` | NMOS | tail | nb | 0 | 0 | comparator tail current source (gate nb) |
| `mn2` | NMOS | tail | n4 | 0 | 0 | extra tail branch, gated by n4 (reset/ack state) |
| `mn3` | NMOS | tail | n2 | 0 | 0 | extra tail branch, gated by n2 (comparator output state) |
| `mi1` | PMOS | n2 | n1 | vdd | vdd | inverter pull-up (n1 to n2) |
| `mi2` | NMOS | n2 | n1 | 0 | 0 | inverter pull-down (n1 to n2) |
| `mp4` | PMOS | n3 | n2 | vdd | vdd | request stage pull-up (gate n2, node n3) |
| `mna` | NMOS | n3 | ack | mid | 0 | ack-gated pull-down, upper device |
| `mnb` | NMOS | mid | n2 | 0 | 0 | ack-gated pull-down, lower device (gate n2) |
| `mpr` | PMOS | rqst | n3 | vdd | vdd | Rqst output driver (gate n3) |
| `mpa` | PMOS | pm | n3 | vdd | vdd | ack handshake pull-up onto pm (gate n3) |
| `mp5` | PMOS | n4 | ack | pm | vdd | pm to n4 path, gated by Ack |
| `mnc` | NMOS | n4 | ack | 0 | 0 | n4 pull-down, gated by Ack |
| `mp3` | PMOS | vspike | ack | vdd | vdd | output stage, drives the spike output |

## Design values
| Quantity | Value | Basis |
|---|---|---|
| Supply Vdd | 3.3 V | published (El-Sayed 2020) |
| Membrane capacitor Cm | about 140 fF (MIM side 11.3 um) | published (Serrano-Gotarredona 2006) |
| Vref - Vreset | 0.5 V | published; absolute Vreset = 1.1 V and Vref = 1.6 V are our choice |
| Bias current | 10 uA | design choice |
| Device sizes | L = 0.5 um, Wn = 2 um, Wp = 4 um | design choice |
| Output resistor | 20 kohm | design choice |
| Rqst arbiter model | 100 kohm / 20 fF | design choice |
| Ack delay | 1 kohm / 3 pF (about 3 ns) | design choice ("a few ns" in the 2006 paper) |
| Stimulus | 10 us current pulse at 50/100/200/400 nA | published range (0.1-0.2 uA), extended |
