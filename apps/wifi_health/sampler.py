"""Periodic sampling loop + rolling buffers.

Drives the data shown on the Current screen (latest sample) and the Log
screen (48 × 30-minute slots + a high-resolution live ping buffer).
"""

import os
import random
import time

import net
import thresholds


# ─── Defaults ──────────────────────────────────────────────────────────
GW_TARGET   = "192.168.1.1"
NET_TARGET  = "1.1.1.1"
DNS_NAME    = "cloudflare.com"

SAMPLE_PERIOD_S = 5
LOSS_WINDOW     = 20
LIVE_PING_LEN   = 300       # ~25 min @ 5s, plenty for the plot

SLOT_SECONDS    = 30 * 60
NUM_SLOTS       = 48        # 24h


def _now():
    return time.time()


def _percentile(values, pct):
    if not values:
        return None
    s = sorted(v for v in values if v is not None)
    if not s:
        return None
    idx = int(round((pct / 100.0) * (len(s) - 1)))
    return s[idx]


def _stdev(values):
    n = sum(1 for v in values if v is not None)
    if n < 2:
        return 0.0
    mean = sum(v for v in values if v is not None) / n
    var = sum((v - mean) ** 2 for v in values if v is not None) / n
    return var ** 0.5


class Sampler:
    """One Sampler covers gateway+internet. Keep instance lifetime = app."""

    def __init__(self, profile="NORMAL"):
        self.profile = profile
        self.gw_target = GW_TARGET
        self.net_target = NET_TARGET
        self.sample_period = SAMPLE_PERIOD_S
        self.dns_name = DNS_NAME

        self._last_sample_ts = 0.0
        self._gw_lat_history = []   # last LOSS_WINDOW latencies (None = lost)
        self._net_lat_history = []
        self._live_net_ping = []    # last LIVE_PING_LEN (lat or None)
        self._slots = []            # list[dict], most recent appended
        self._current_slot_start = self._slot_start(_now())
        self._current_slot_samples = {"gw": [], "net": []}

        self.latest = self._empty_sample()

        # When demoing simulated profiles in the emulator, seed plausible
        # 24h history so the Log screen has something to draw immediately.
        if os.environ.get("EMU_NETWORK_PROFILE") in {"healthy", "degraded", "down"}:
            self._seed_demo_history()

    def _seed_demo_history(self):
        profile = os.environ.get("EMU_NETWORK_PROFILE", "healthy")
        rng = random.Random(42)
        now = _now()
        seed_slot_start = self._slot_start(now) - SLOT_SECONDS * (NUM_SLOTS - 1)
        for i in range(NUM_SLOTS - 1):
            # Roll a status mixture by profile, with occasional warn/down spikes
            r = rng.random()
            if profile == "healthy":
                status = "ok" if r < 0.96 else ("warn" if r < 0.99 else "down")
            elif profile == "degraded":
                status = "warn" if r < 0.5 else ("ok" if r < 0.85 else "down")
            else:  # down
                status = "down" if r < 0.6 else ("warn" if r < 0.85 else "ok")
            # GW is generally healthier than the upstream link
            gw_status = "ok" if (status == "ok" or rng.random() < 0.7) else status
            self._slots.append({
                "ts_start": seed_slot_start + i * SLOT_SECONDS,
                "gw": gw_status,
                "net": status,
                "gw_p50_ms": None, "net_p50_ms": None,
                "gw_p99_ms": None, "net_p99_ms": None,
            })
        # Live ping seed: a wave with a couple of spikes
        for i in range(LIVE_PING_LEN):
            base = 18 if profile == "healthy" else 110 if profile == "degraded" else None
            if base is None:
                self._live_net_ping.append(None if rng.random() < 0.4 else 250)
            else:
                noise = rng.uniform(-6, 6) if profile == "healthy" else rng.uniform(-25, 60)
                spike = 200 if (profile == "degraded" and rng.random() < 0.02) else 0
                self._live_net_ping.append(base + noise + spike)

    # ─── Slot bookkeeping ───────────────────────────────────────────

    @staticmethod
    def _slot_start(ts):
        return int(ts // SLOT_SECONDS) * SLOT_SECONDS

    def _close_slot(self, slot_start):
        gw_samples = self._current_slot_samples["gw"]
        net_samples = self._current_slot_samples["net"]
        slot = {
            "ts_start": slot_start,
            "gw":  self._slot_status(gw_samples),
            "net": self._slot_status(net_samples),
            "gw_p50_ms":  _percentile([s for s in gw_samples  if s is not None], 50),
            "net_p50_ms": _percentile([s for s in net_samples if s is not None], 50),
            "gw_p99_ms":  _percentile([s for s in gw_samples  if s is not None], 99),
            "net_p99_ms": _percentile([s for s in net_samples if s is not None], 99),
        }
        self._slots.append(slot)
        if len(self._slots) > NUM_SLOTS:
            self._slots = self._slots[-NUM_SLOTS:]
        self._current_slot_samples = {"gw": [], "net": []}

    def _slot_status(self, samples):
        if not samples:
            return "down"
        ok = [s for s in samples if s is not None]
        if not ok:
            return "down"
        loss_pct = (1 - len(ok) / len(samples)) * 100
        if loss_pct > 10:
            return "down"
        p50 = _percentile(ok, 50)
        lat_status = thresholds.classify("latency", p50, self.profile)
        if loss_pct > 1 or lat_status != "ok":
            return "warn" if lat_status != "down" else "down"
        return "ok"

    # ─── Sampling ──────────────────────────────────────────────────

    def _empty_sample(self):
        return {
            "ts": _now(),
            "gateway":  self._empty_channel(self.gw_target),
            "internet": self._empty_channel(self.net_target),
        }

    def _empty_channel(self, target):
        return {
            "target": target,
            "latency_ms": None,
            "loss_pct": 0.0,
            "jitter_ms": None,
            "dns_ms": None,
            "rssi_dbm": None,
            "status": "ok",
            "metric_status": {},
        }

    def _build_channel(self, target, latency_ms, loss_history, dns_ms, rssi_dbm):
        loss = (1 - sum(1 for v in loss_history if v is not None) /
                max(1, len(loss_history))) * 100
        jitter = _stdev(loss_history) if loss_history else None

        metric_status = {
            "latency": thresholds.classify("latency", latency_ms, self.profile),
            "loss":    thresholds.classify("loss", loss, self.profile),
            "jitter":  thresholds.classify("jitter", jitter, self.profile),
            "dns":     thresholds.classify("dns", dns_ms, self.profile),
            "rssi":    thresholds.classify("rssi", rssi_dbm, self.profile),
        }
        status = thresholds.channel_status(list(metric_status.values()))
        return {
            "target": target,
            "latency_ms": latency_ms,
            "loss_pct": loss,
            "jitter_ms": jitter,
            "dns_ms": dns_ms,
            "rssi_dbm": rssi_dbm,
            "status": status,
            "metric_status": metric_status,
        }

    def tick(self, force=False):
        """Run a sample if the sample interval has elapsed.

        Returns True iff a new sample was taken.
        """
        now = _now()
        if not force and now - self._last_sample_ts < self.sample_period:
            return False
        self._last_sample_ts = now

        # DNS is a global probe — both channels share its result.
        gw_res  = net.probe(self.gw_target, port=53)
        net_res = net.probe(self.net_target, port=53, dns_name=self.dns_name)
        dns_ms  = net_res["dns_ms"]
        rssi    = net.rssi_dbm()

        # Update histories
        self._gw_lat_history.append(gw_res["latency_ms"])
        self._net_lat_history.append(net_res["latency_ms"])
        self._gw_lat_history  = self._gw_lat_history[-LOSS_WINDOW:]
        self._net_lat_history = self._net_lat_history[-LOSS_WINDOW:]
        self._live_net_ping.append(net_res["latency_ms"])
        self._live_net_ping = self._live_net_ping[-LIVE_PING_LEN:]

        # Roll the slot if 30 min boundary crossed
        slot_start = self._slot_start(now)
        if slot_start != self._current_slot_start:
            self._close_slot(self._current_slot_start)
            self._current_slot_start = slot_start
        self._current_slot_samples["gw"].append(gw_res["latency_ms"])
        self._current_slot_samples["net"].append(net_res["latency_ms"])

        self.latest = {
            "ts": now,
            "gateway":  self._build_channel(
                self.gw_target, gw_res["latency_ms"],
                self._gw_lat_history, dns_ms, rssi,
            ),
            "internet": self._build_channel(
                self.net_target, net_res["latency_ms"],
                self._net_lat_history, dns_ms, rssi,
            ),
        }
        return True

    # ─── Accessors ─────────────────────────────────────────────────

    def slots_snapshot(self):
        """The 48-slot heatmap data, padded on the left with 'down' for
        unfilled history. The right-most entry is the current (open) slot,
        previewed from samples taken so far."""
        snapshot = list(self._slots)
        # Preview the in-progress slot if we have any samples for it
        if self._current_slot_samples["gw"] or self._current_slot_samples["net"]:
            snapshot.append({
                "ts_start": self._current_slot_start,
                "gw":  self._slot_status(self._current_slot_samples["gw"]),
                "net": self._slot_status(self._current_slot_samples["net"]),
                "gw_p50_ms": None, "net_p50_ms": None,
                "gw_p99_ms": None, "net_p99_ms": None,
                "open": True,
            })
        # Left-pad with empty (not-yet-recorded) slots so the array is always
        # length NUM_SLOTS. These are visually distinct from real outages.
        if len(snapshot) < NUM_SLOTS:
            pad = NUM_SLOTS - len(snapshot)
            snapshot = [{"gw": "none", "net": "none", "open": False}] * pad + snapshot
        return snapshot

    def live_ping(self):
        """Latest live ping samples (list of ms or None)."""
        return list(self._live_net_ping)

    def stats(self):
        """Return (incidents_warn, incidents_down, uptime_pct) over recorded slots.

        Empty (not-yet-recorded) slots are excluded; uptime over zero slots
        is reported as 100%.
        """
        slots = [s for s in self.slots_snapshot() if s.get("gw") != "none"]
        if not slots:
            return 0, 0, 100.0
        warn = sum(1 for s in slots if s.get("gw") == "warn" or s.get("net") == "warn")
        down = sum(1 for s in slots if s.get("gw") == "down" or s.get("net") == "down")
        ok = sum(1 for s in slots if s.get("gw") == "ok" and s.get("net") == "ok")
        uptime = ok / len(slots) * 100
        return warn, down, uptime
