#!/usr/bin/env python3
"""
Run the T1/T2/T3 protocol simulation and print a Table-3-shaped result.

This is a SIMULATION of the flood-relay protocol's logic (seen-set dedup,
hop counting, TTL), not a physical-device trial. Treat the output as a
model-based estimate to sanity-check against, not as Section 7 Table 3
itself -- that table is filled only from real BatteryStatsManager /
Logcat data captured on physical phones (see EVALUATION-PROTOCOL.md in
the main app repo).
"""
import argparse
import csv
import random
import sys

from sim.metrics import BatteryModel, aggregate
from sim.protocol import LinkModel, run_flood_trial
from sim.topologies import TOPOLOGIES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=200, help="trials per topology")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--csv", type=str, default=None, help="optional path to write CSV")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    link_model = LinkModel()
    battery = BatteryModel()

    rows = []
    print(f"{'Metric':28s} | {'T1_line':>10s} | {'T2_clique':>10s} | {'T3_room_scale':>13s}")
    print("-" * 70)

    per_topology = {}
    for name, builder in TOPOLOGIES.items():
        graph = builder()
        nodes = list(graph.keys())
        results = []
        for _ in range(args.trials):
            sender = rng.choice(nodes)
            results.append(run_flood_trial(graph, sender, link_model, rng))
        per_topology[name] = aggregate(results, n_nodes=len(nodes))

    def fmt_row(label, key, formatter=lambda v: f"{v:.3f}"):
        vals = [formatter(getattr(per_topology[t], key)) for t in TOPOLOGIES]
        print(f"{label:28s} | {vals[0]:>10s} | {vals[1]:>10s} | {vals[2]:>13s}")
        rows.append([label] + vals)

    fmt_row("Delivery ratio (mean)", "delivery_ratio_mean")
    fmt_row("Latency median (ms)", "latency_median_ms", lambda v: f"{v:.0f}")
    fmt_row("Latency 95th pct (ms)", "latency_p95_ms", lambda v: f"{v:.0f}")
    fmt_row("Hop-count mode", "hop_count_mode", lambda v: f"{v:d}")
    fmt_row("Dup-suppress rate", "dup_suppress_rate")

    idle_off = battery.window_mah(30, screen_on=False)
    idle_on = battery.window_mah(30, screen_on=True)
    active_off = battery.window_mah(30, screen_on=False, messages_sent=30)
    active_on = battery.window_mah(30, screen_on=True, messages_sent=30)
    print(f"{'Battery idle (mAh/30min)':28s} | screen-off={idle_off:.2f}  screen-on={idle_on:.2f}")
    print(f"{'Battery active (mAh/30min)':28s} | screen-off={active_off:.2f}  screen-on={active_on:.2f}")
    rows.append(["Battery idle (mAh/30min) screen-off", idle_off])
    rows.append(["Battery idle (mAh/30min) screen-on", idle_on])
    rows.append(["Battery active (mAh/30min) screen-off", active_off])
    rows.append(["Battery active (mAh/30min) screen-on", active_on])

    print("\nHop-count distributions:")
    for name in TOPOLOGIES:
        print(f"  {name}: {per_topology[name].hop_count_distribution}")

    print(
        "\nNOTE: these numbers come from a protocol-level simulation with "
        "assumed link parameters (sim/protocol.py:LinkModel), not from "
        "physical BLE hardware. Do not present them as Table 3 results."
    )

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", *TOPOLOGIES.keys()])
            writer.writerows(rows)
        print(f"\nWrote {args.csv}")


if __name__ == "__main__":
    sys.exit(main())
