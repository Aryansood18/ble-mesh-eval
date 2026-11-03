# ble-mesh-eval

A reproducible **simulation** of the SafeSphere BLE flood-relay mesh protocol, built to
evaluate the metrics defined in the paper's Section 7 evaluation protocol:

- delivery ratio
- end-to-end latency (median, 95th percentile)
- hop-count distribution
- duplicate-suppression rate
- battery draw

across the paper's three trial topologies (T1 line, T2 clique, T3 room-scale), and across
a sweep of device counts from 3 to 29.

> **Simulation, not a hardware measurement.** This repo models the protocol's real logic —
> the seen-set deduplication, hop counting, and TTL handling from `BlePacket.kt` /
> `BleMeshManager.kt` in the Android app — and runs it over simulated radio links with
> assumed delivery probability and latency parameters (`sim/protocol.py:LinkModel`).
> Every number below comes from that model. It is a rigorous, labelled way to predict and
> reason about the protocol's behaviour before/alongside physical-device trials, not a
> replacement for them. See `EVALUATION-PROTOCOL.md` in the main app repo for the physical
> trial design these simulations are built to mirror.

---

## 1. Results — T1 / T2 / T3 (200 trials each)

| Metric | T1 line | T2 clique | T3 room-scale |
|---|---|---|---|
| Delivery ratio (mean) | 0.873 | **1.000** | 0.877 |
| Latency median (ms) | 625 | 575 | 780 |
| Latency 95th pct (ms) | 1 323 | 914 | 1 835 |
| Hop-count mode | 1 | 1 | 1 |
| Dup-suppress rate | 0.375 | 0.743 | 0.403 |
| Battery idle (mAh/30 min) | screen-off 0.65 / screen-on 1.30 | — | — |
| Battery active (mAh/30 min) | screen-off 1.01 / screen-on 1.66 | — | — |

Raw output: [`out/table3_simulated.csv`](out/table3_simulated.csv).

**Reading the results.** T2 (a tight 5-device clique) reaches perfect delivery because
every device is within one hop of every other — there's no relay to fail. T1 and T3 sit
a little lower because each depends on a specific relay path (the single middle device in
T1's line, the single bridge device in T3's two cliques) rather than many redundant paths.
T3's 95th-percentile latency (1 835 ms) is the highest of the three, which tracks with it
needing the most hops to fully cross — each extra hop re-pays the full connect + MTU +
write cost, so latency compounds with hop count rather than staying flat.

Dup-suppress rate also follows topology shape directly: it's lowest in the sparse line
(0.375, few redundant paths to produce duplicates) and highest in the dense clique (0.743,
where most devices hear the same packet from several neighbours and all but one copy gets
correctly dropped).

---

## 2. Results — scaling device count (3 → 29 devices, 100 trials per step)

Topology: `scaled_room(n)` — the T3 shape generalised, i.e. bridged cliques whose number
and size both grow with `n` (see `sim/topologies.py`).

| N | Delivery ratio | Latency median (ms) | Latency 95th pct (ms) | Dup-suppress rate | Hop-count mode |
|---|---|---|---|---|---|
| 3 | 0.910 | 763 | 1 744 | 0.402 | 1 |
| 5 | 0.873 | 763 | 1 758 | 0.402 | 1 |
| 7 | 0.858 | 1 077 | 2 564 | 0.428 | 1 |
| 9 | 0.880 | 1 317 | 2 956 | 0.580 | 1 |
| 11 | 0.905 | 1 233 | 2 911 | 0.576 | 1 |
| 13 | 0.873 | 1 544 | 3 764 | 0.583 | 1 |
| 15 | 0.910 | 1 578 | 3 861 | 0.580 | 1 |
| 17 | 0.891 | 1 609 | 3 831 | 0.686 | 1 |
| 19 | 0.909 | 1 651 | 3 915 | 0.686 | 1 |
| 21 | 0.911 | 1 991 | 4 889 | 0.682 | 1 |
| 23 | 0.881 | 1 938 | 4 763 | 0.684 | **3** |
| 25 | 0.843 | 1 854 | 4 555 | 0.750 | **3** |
| 27 | 0.858 | 1 847 | 4 660 | 0.750 | **3** |
| 29 | 0.816 | 1 900 | 4 827 | 0.749 | 1 |

Raw output: [`out/scale_sweep.csv`](out/scale_sweep.csv). Graphs:
[`delivery_ratio_vs_n.png`](out/delivery_ratio_vs_n.png) ·
[`latency_vs_n.png`](out/latency_vs_n.png) ·
[`dup_suppress_vs_n.png`](out/dup_suppress_vs_n.png) ·
[`hop_count_vs_n.png`](out/hop_count_vs_n.png)

**Trends.**

- **Delivery ratio stays roughly flat** (0.82–0.91) across the full 3→29 range. Growing the
  mesh doesn't meaningfully degrade reachability in this model, because `scaled_room`
  keeps the same bridged-clique shape at every size rather than stretching into one long,
  fragile chain.
- **Latency roughly triples** from N=3 (median 763 ms) to N=29 (median 1 900 ms), and the
  95th percentile grows faster still (1 744 ms → 4 827 ms). More devices means more
  cliques to cross and more hops end-to-end, and each hop adds a full connect-cost, so
  latency compounds with network diameter, not device count directly.
- **Dup-suppress rate nearly doubles**, from 0.40 at N=3 to ~0.75 by N=25+. Denser meshes
  mean a device hears the same flooded packet from more neighbours, so a larger share of
  arrivals are correctly-dropped duplicates rather than new deliveries.
- **Hop-count mode shifts from 1 to 3** once the network grows past ~21 devices — enough
  cliques now exist that the *most common* path length is no longer a single hop, a sign
  the flood is genuinely spanning a multi-clique structure rather than staying local.

---

## 3. What generated these numbers

The simulation reuses the protocol's actual rules, not a simplified stand-in:

- **Seen-set deduplication** — a `LinkedHashSet`-style cap at 500 entries, identical to
  `BleMeshManager.addSeen()`.
- **Hop counting and TTL** — each relay increments hop count and decrements TTL exactly as
  `BlePacket.relayed()` does (`ttl-1, hopCount+1, reachCount+1`).
- **Topologies** — T1 (two edge devices + one relay), T2 (one clique within range), and T3
  (two cliques joined by a single bridge device) are built exactly to the paper's trial
  design in `sim/topologies.py`.

The one modelled (not measured) piece is the radio link itself: each hop has a configurable
delivery probability and a latency distribution (`sim/protocol.py:LinkModel`, currently
92% delivery, ~550 ms mean per hop). These are reasonable placeholder assumptions for BLE
GATT connect + MTU negotiate + write, and the whole point of labelling them is so they can
be swapped for real figures the moment physical trial data exists — at which point every
result in this README can be regenerated from measured inputs instead of assumed ones.

---

## 4. Layout

```
sim/
  protocol.py     # flood-relay simulation core, mirrors BleMeshManager semantics
  topologies.py   # T1 line / T2 clique / T3 bridged-cliques / scalable N-device topology
  metrics.py      # delivery ratio, latency percentiles, hop-count dist, dup-suppress, battery model
run_table3.py     # one fixed run of T1/T2/T3, prints + optional CSV
run_scale_sweep.py# sweeps N devices, writes CSV + PNG graphs to out/
out/              # generated CSVs and graphs (this README's numbers)
```

## 5. Reproducing these results

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python3 run_table3.py --trials 200 --csv out/table3_simulated.csv
python3 run_scale_sweep.py --min-n 3 --max-n 29 --step 2 --trials 100
```

## 6. Calibrating against physical trials

Once physical-device trials are run, update `LinkModel.delivery_prob`, `latency_mean_ms`,
`latency_sd_ms` in `sim/protocol.py`, and the constants in `metrics.py:BatteryModel`, to
match the measured values, then re-run both scripts. The simulation's shape (how metrics
move with topology and device count) stays useful even after calibration — it's the two
link parameters that get replaced with real numbers.
