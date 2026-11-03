"""
Discrete-event model of the SafeSphere BLE flood-relay protocol.

Mirrors the real implementation in the Android app:
  - BlePacket.kt:    msgId, ttl, hopCount, reachCount fields; relayed() does
                      ttl-1, hopCount+1, reachCount+1
  - BleMeshManager.kt: seen-set (LinkedHashSet) deduplication, capped at 500
                      entries (BleMeshManager.addSeen); DEFAULT_TTL=10,
                      REACH_CAP=100 (BleConstants.kt)

This is a protocol-level simulation, not a radio-level one: each edge in the
topology graph is an "in BLE range" link, and a single hop over that edge
takes a random delay drawn from a per-link distribution (connect + MTU
negotiate + write), with a per-hop delivery probability representing BLE
loss. Nothing here is a measurement of physical hardware.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

DEFAULT_TTL = 10
SEEN_SET_CAP = 500


@dataclass
class LinkModel:
    """Per-hop radio behaviour. Defaults are mid-range BLE assumptions,
    not measurements -- override them to match whatever real trial data
    you eventually collect."""

    # One-hop delivery probability (BLE loss on a clean 2.4GHz channel).
    delivery_prob: float = 0.92
    # One-hop latency distribution (ms): connect + MTU negotiate + write.
    latency_mean_ms: float = 550.0
    latency_sd_ms: float = 180.0

    def attempt(self, rng: random.Random) -> tuple[bool, float]:
        delivered = rng.random() < self.delivery_prob
        latency = max(20.0, rng.gauss(self.latency_mean_ms, self.latency_sd_ms))
        return delivered, latency


@dataclass
class SimResult:
    send_time: float
    # node -> (first display time, hop count at first display) for nodes that displayed
    displays: dict
    # count of (dropped, admitted) decisions across all nodes/edges in this trial
    dropped: int
    admitted: int


class SeenSet:
    """Mirrors BleMeshManager's LinkedHashSet seen-set with its 500-entry cap."""

    def __init__(self, cap: int = SEEN_SET_CAP):
        self._order: list[str] = []
        self._set: set[str] = set()
        self._cap = cap

    def add(self, msg_id: str) -> bool:
        """Returns True if newly added (admitted), False if already seen (dropped)."""
        if msg_id in self._set:
            return False
        self._set.add(msg_id)
        self._order.append(msg_id)
        if len(self._order) > self._cap:
            oldest = self._order.pop(0)
            self._set.discard(oldest)
        return True


def run_flood_trial(
    graph: dict,
    sender: str,
    link_model: LinkModel,
    rng: random.Random,
    ttl: int = DEFAULT_TTL,
) -> SimResult:
    """
    Simulate one flood of a single SOS packet from `sender` across `graph`
    (adjacency dict: node -> list of neighbour nodes).

    Matches BleMeshManager semantics: a node that has already admitted a
    msgId does not re-process or re-relay it (seen-set), hopCount increments
    per relay, and the flood stops at `ttl`.
    """
    msg_id = "sim-msg"
    seen = {node: SeenSet() for node in graph}
    displays: dict[str, tuple[float, int]] = {}
    dropped = 0
    admitted = 0

    # event queue: (arrival_time, node, hop_count, ttl_remaining)
    send_time = 0.0
    queue: list[tuple[float, str, int, int]] = [(send_time, sender, 0, ttl)]
    seen[sender].add(msg_id)
    admitted += 1
    displays[sender] = (send_time, 0)

    while queue:
        queue.sort(key=lambda e: e[0])
        t, node, hop_count, ttl_remaining = queue.pop(0)
        if ttl_remaining <= 0:
            continue
        for neighbour in graph.get(node, []):
            delivered, latency = link_model.attempt(rng)
            if not delivered:
                continue
            arrival = t + latency
            if seen[neighbour].add(msg_id):
                admitted += 1
                displays.setdefault(neighbour, (arrival, hop_count + 1))
                queue.append((arrival, neighbour, hop_count + 1, ttl_remaining - 1))
            else:
                dropped += 1

    return SimResult(send_time=send_time, displays=displays, dropped=dropped, admitted=admitted)
