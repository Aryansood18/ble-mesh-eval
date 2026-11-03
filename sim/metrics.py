"""Aggregate SimResult trials into the metrics defined in the paper's
Section 7 (delivery ratio, latency, hop-count distribution, dup-suppress
rate), plus a simple battery-draw model."""
from __future__ import annotations

import statistics
from dataclasses import dataclass

from .protocol import SimResult


@dataclass
class AggregateMetrics:
    delivery_ratio_mean: float
    latency_median_ms: float
    latency_p95_ms: float
    hop_count_mode: int
    hop_count_distribution: dict
    dup_suppress_rate: float
    n_trials: int


def aggregate(results: list[SimResult], n_nodes: int) -> AggregateMetrics:
    ratios = []
    latencies = []
    hop_counts = []
    total_dropped = 0
    total_admitted = 0

    for r in results:
        eligible = n_nodes - 1
        delivered = len(r.displays) - 1  # exclude the sender itself
        ratios.append(delivered / eligible if eligible > 0 else 0.0)

        for node, (t_display, hops) in r.displays.items():
            if t_display == r.send_time and hops == 0:
                continue  # sender itself
            latencies.append(t_display - r.send_time)
            hop_counts.append(hops)

        total_dropped += r.dropped
        total_admitted += r.admitted

    latencies.sort()
    hop_mode = statistics.mode(hop_counts) if hop_counts else 0
    hop_dist = {h: hop_counts.count(h) for h in sorted(set(hop_counts))}

    def percentile(data: list[float], pct: float) -> float:
        if not data:
            return 0.0
        k = (len(data) - 1) * pct
        f, c = int(k), min(int(k) + 1, len(data) - 1)
        if f == c:
            return data[f]
        return data[f] + (data[c] - data[f]) * (k - f)

    return AggregateMetrics(
        delivery_ratio_mean=statistics.mean(ratios) if ratios else 0.0,
        latency_median_ms=statistics.median(latencies) if latencies else 0.0,
        latency_p95_ms=percentile(latencies, 0.95),
        hop_count_mode=hop_mode,
        hop_count_distribution=hop_dist,
        dup_suppress_rate=total_dropped / (total_dropped + total_admitted)
        if (total_dropped + total_admitted) > 0
        else 0.0,
        n_trials=len(results),
    )


@dataclass
class BatteryModel:
    """Simple duty-cycle battery draw model, parameterised so it can be
    swapped for BatteryStatsManager readings once real trials are run.
    Defaults are a rough order-of-magnitude guess for a modern phone doing
    continuous BLE advertise+scan, NOT a measurement."""

    idle_draw_ma_screen_off: float = 1.3
    idle_draw_ma_screen_on: float = 2.6
    per_message_mah: float = 0.012  # extra cost per SOS write/relay

    def window_mah(self, minutes: float, screen_on: bool, messages_sent: int = 0) -> float:
        base_ma = self.idle_draw_ma_screen_on if screen_on else self.idle_draw_ma_screen_off
        return base_ma * (minutes / 60.0) + messages_sent * self.per_message_mah
