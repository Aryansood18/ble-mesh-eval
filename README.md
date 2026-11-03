# ble-mesh-eval

A protocol-level **simulation** of the SafeSphere BLE flood-relay mesh
(see the [capstone app](https://github.com/)), used to evaluate the metrics
defined in the paper's Section 7 evaluation protocol:

- delivery ratio
- end-to-end latency (median, 95th percentile)
- hop-count distribution
- duplicate-suppression rate
- a simple battery-draw model

and to show how each metric scales as the number of devices grows.

## What this is, and isn't

This is **not** a substitute for physical-device trials. It simulates the
protocol's actual logic — the seen-set deduplication, hop-count increment,
and TTL decrement from `BlePacket.kt` / `BleMeshManager.kt` in the Android
app — over graph topologies, with randomised per-hop latency and loss
standing in for real BLE radio behaviour. The link-level parameters
(`sim/protocol.py:LinkModel`) are reasonable assumptions, not measurements.

Use this to:
- sanity-check the protocol's dedup/hop-count logic before running real trials,
- see expected *trends* as device count scales,
- get a reproducible, labelled starting point to compare real trial data against.

Do **not** use this to fill in a paper's results table as if it were
hardware data. Every script and plot in this repo prints/labels itself as
simulation output for that reason.

## Layout

```
sim/
  protocol.py     # flood-relay simulation core, mirrors BleMeshManager semantics
  topologies.py   # T1 line / T2 clique / T3 bridged-cliques / scalable N-device topology
  metrics.py      # delivery ratio, latency percentiles, hop-count dist, dup-suppress, battery model
run_table3.py     # one fixed run of T1/T2/T3, prints + optional CSV
run_scale_sweep.py# sweeps N devices, writes CSV + PNG graphs to out/
```

## Usage

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Table-3-shaped simulation output (not real trial data)
python3 run_table3.py --trials 200 --csv out/table3_simulated.csv

# Scale sweep with graphs
python3 run_scale_sweep.py --min-n 3 --max-n 40 --step 2 --trials 100
```

## Calibrating against real trials

Once physical-device trials are run (see `EVALUATION-PROTOCOL.md` in the
app repo), update `LinkModel.delivery_prob`, `latency_mean_ms`,
`latency_sd_ms` in `sim/protocol.py`, and the constants in
`metrics.py:BatteryModel`, to match the measured values. Re-running the
sweep then shows how the protocol is expected to behave at device counts
you haven't physically tested, anchored to real data instead of a guess.
