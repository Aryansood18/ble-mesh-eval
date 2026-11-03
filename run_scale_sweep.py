#!/usr/bin/env python3
"""
Sweep the device count N and plot how each metric changes, using the same
protocol simulation as run_table3.py, over the `scaled_room` topology
(bridged cliques that grow with N -- see sim/topologies.py).

Outputs:
  out/scale_sweep.csv
  out/delivery_ratio_vs_n.png
  out/latency_vs_n.png
  out/dup_suppress_vs_n.png
  out/hop_count_vs_n.png
"""
import argparse
import csv
import os
import random

import matplotlib.pyplot as plt

from sim.metrics import aggregate
from sim.protocol import LinkModel, run_flood_trial
from sim.topologies import scaled_room


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-n", type=int, default=3)
    parser.add_argument("--max-n", type=int, default=40)
    parser.add_argument("--step", type=int, default=2)
    parser.add_argument("--trials", type=int, default=100, help="trials per N")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=str, default="out")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    rng = random.Random(args.seed)
    link_model = LinkModel()

    ns = list(range(args.min_n, args.max_n + 1, args.step))
    rows = []
    for n in ns:
        graph = scaled_room(n)
        nodes = list(graph.keys())
        results = []
        for _ in range(args.trials):
            sender = rng.choice(nodes)
            results.append(run_flood_trial(graph, sender, link_model, rng))
        m = aggregate(results, n_nodes=len(nodes))
        rows.append(
            {
                "n": n,
                "delivery_ratio_mean": m.delivery_ratio_mean,
                "latency_median_ms": m.latency_median_ms,
                "latency_p95_ms": m.latency_p95_ms,
                "hop_count_mode": m.hop_count_mode,
                "dup_suppress_rate": m.dup_suppress_rate,
            }
        )
        print(f"n={n:3d}  DR={m.delivery_ratio_mean:.3f}  "
              f"lat_med={m.latency_median_ms:6.0f}ms  "
              f"lat_p95={m.latency_p95_ms:6.0f}ms  "
              f"dup_suppress={m.dup_suppress_rate:.3f}  "
              f"hop_mode={m.hop_count_mode}")

    csv_path = os.path.join(args.out, "scale_sweep.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {csv_path}")

    ns_plot = [r["n"] for r in rows]

    def plot(metric_key, ylabel, title, filename, extra=None):
        plt.figure(figsize=(7, 4.5))
        plt.plot(ns_plot, [r[metric_key] for r in rows], marker="o")
        if extra:
            extra()
        plt.xlabel("Number of devices (N)")
        plt.ylabel(ylabel)
        plt.title(title + "\n(simulation, not physical-device measurement)")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        path = os.path.join(args.out, filename)
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"Wrote {path}")

    plot("delivery_ratio_mean", "Delivery ratio (mean)",
         "Delivery ratio vs device count", "delivery_ratio_vs_n.png")

    plt.figure(figsize=(7, 4.5))
    plt.plot(ns_plot, [r["latency_median_ms"] for r in rows], marker="o", label="median")
    plt.plot(ns_plot, [r["latency_p95_ms"] for r in rows], marker="s", label="95th pct")
    plt.xlabel("Number of devices (N)")
    plt.ylabel("End-to-end latency (ms)")
    plt.title("Latency vs device count\n(simulation, not physical-device measurement)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(args.out, "latency_vs_n.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Wrote {path}")

    plot("dup_suppress_rate", "Duplicate-suppression rate",
         "Dup-suppress rate vs device count", "dup_suppress_vs_n.png")

    plot("hop_count_mode", "Hop-count mode",
         "Hop-count mode vs device count", "hop_count_vs_n.png")


if __name__ == "__main__":
    main()
