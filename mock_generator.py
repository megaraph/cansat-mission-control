# ─────────────────────────────────────────────
#  CanSat Ground Station  |  mock_generator.py
#  Simulates a realistic CanSat flight arc:
#  IDLE → LAUNCH → ASCENT → APOGEE → DESCENT → LANDED
# ─────────────────────────────────────────────

import time
import math
import random
import threading
import queue

import config

# ── Flight profile phases ─────────────────────────────────────────────────────
#  Each phase: (name, duration_s, alt_start_m, alt_end_m)
PHASES = [
    ("IDLE", 5, 80.0, 80.0),
    ("LAUNCH", 2, 80.0, 95.0),
    ("ASCENT", 20, 95.0, 450.0),
    ("APOGEE", 3, 450.0, 450.0),
    ("DESCENT", 30, 450.0, 80.0),
    ("LANDED", 999, 80.0, 80.0),
]

GROUND_ALT_ABS = 81.0  # realistic absolute altitude (m) matching sample data
BASE_PRESSURE = 100365.0
BASE_LAT = 14.5995  # Manila, Philippines approx
BASE_LON = 120.9842


def _noise(scale: float) -> float:
    return random.gauss(0, scale)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


class MockDataGenerator(threading.Thread):
    """
    Runs in a background thread. Emits parsed data dicts into `out_queue`
    at MOCK_RATE_HZ. Stops when stop() is called or the last phase ends.
    """

    def __init__(self, out_queue: queue.Queue):
        super().__init__(daemon=True)
        self.out_queue = out_queue
        self._stop_event = threading.Event()
        self._t_start = None
        self._timestamp_ms = 0

    def stop(self):
        self._stop_event.set()

    def _get_phase(self, elapsed: float):
        t = 0.0
        for name, dur, alt_s, alt_e in PHASES:
            if elapsed < t + dur:
                progress = (elapsed - t) / dur if dur > 0 else 1.0
                return name, progress, alt_s, alt_e
            t += dur
        # Past all phases — hold LANDED
        return "LANDED", 1.0, 80.0, 80.0

    def run(self):
        interval = 1.0 / config.MOCK_RATE_HZ
        self._t_start = time.time()

        while not self._stop_event.is_set():
            t0 = time.time()
            elapsed = t0 - self._t_start
            self._timestamp_ms = int(elapsed * 1000)

            phase, progress, alt_s, alt_e = self._get_phase(elapsed)

            # ── Altitude ──────────────────────────────────────────────────────
            # Use smooth easing for ascent/descent
            if phase == "ASCENT":
                ease = math.sin(progress * math.pi / 2)  # ease-in
            elif phase == "DESCENT":
                ease = 1.0 - math.sin((1 - progress) * math.pi / 2)  # ease-out
            else:
                ease = progress

            alt_rel = _lerp(alt_s - GROUND_ALT_ABS, alt_e - GROUND_ALT_ABS, ease)
            alt_abs = alt_rel + GROUND_ALT_ABS + _noise(0.15)

            # ── Pressure (inversely related to altitude) ─────────────────────
            # ~12 Pa per meter near sea level
            pressure = BASE_PRESSURE - (alt_abs - GROUND_ALT_ABS) * 12.0 + _noise(2.0)

            # ── Temperature ───────────────────────────────────────────────────
            # Lapse rate ~6.5°C per 1000m
            ntc_ms5611 = 27.0 - (alt_abs - GROUND_ALT_ABS) * 0.0065 + _noise(0.05)
            ntc_thermistor = ntc_ms5611 + _noise(0.1)

            # ── IMU ───────────────────────────────────────────────────────────
            if phase == "IDLE":
                ax, ay, az = 0.0 + _noise(0.02), 0.0 + _noise(0.02), -1.0 + _noise(0.02)
                gx = gy = gz = 0.0
                gx += _noise(0.5)
                gy += _noise(0.5)
                gz += _noise(0.5)

            elif phase == "LAUNCH":
                thrust_g = _lerp(0.0, 4.5, progress)
                ax = _noise(0.1)
                ay = _noise(0.1)
                az = thrust_g + _noise(0.2)
                gx = _noise(3.0)
                gy = _noise(3.0)
                gz = _noise(1.0)

            elif phase == "ASCENT":
                thrust_g = max(0.0, 4.5 * (1.0 - progress * 1.5))
                ax = _noise(0.05)
                ay = _noise(0.05)
                az = 1.0 + thrust_g + _noise(0.1)
                gx = _noise(1.5)
                gy = _noise(1.5)
                gz = _noise(0.5)

            elif phase == "APOGEE":
                ax = _noise(0.3)
                ay = _noise(0.3)
                az = _noise(0.2)
                gx = _noise(5.0)
                gy = _noise(5.0)
                gz = _noise(5.0)

            elif phase == "DESCENT":
                drag_decel = 0.3
                ax = _noise(0.05)
                ay = _noise(0.05)
                az = -(1.0 - drag_decel) + _noise(0.05)
                gx = _noise(2.0)
                gy = _noise(2.0)
                gz = _noise(1.0)

            else:  # LANDED
                ax = _noise(0.01)
                ay = _noise(0.01)
                az = -1.0 + _noise(0.01)
                gx = gy = gz = 0.0

            # ── GPS ───────────────────────────────────────────────────────────
            # GPS fixed only after IDLE phase; drifts slightly during flight
            if phase in ("IDLE", "LAUNCH"):
                lat = lon = 0.0
                gps_date = "0/0/0"
            else:
                drift_factor = alt_rel / 450.0 * 0.001
                lat = (
                    BASE_LAT + drift_factor * math.sin(elapsed * 0.3) + _noise(0.00005)
                )
                lon = (
                    BASE_LON + drift_factor * math.cos(elapsed * 0.3) + _noise(0.00005)
                )
                now = time.localtime()
                gps_date = f"{now.tm_mday}/{now.tm_mon}/{now.tm_year}"

            packet = {
                "phase": phase,
                "timestamp_ms": self._timestamp_ms,
                "pressure": round(pressure, 2),
                "ntc_thermistor": round(ntc_thermistor, 2),
                "ntc_ms5611": round(ntc_ms5611, 2),
                "alt_absolute": round(alt_abs, 2),
                "alt_relative": round(alt_rel, 2),
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "gps_date": gps_date,
                "ax": round(ax, 3),
                "ay": round(ay, 3),
                "az": round(az, 3),
                "gx": round(gx, 3),
                "gy": round(gy, 3),
                "gz": round(gz, 3),
            }

            try:
                self.out_queue.put_nowait(packet)
            except queue.Full:
                pass  # drop packet rather than block

            # Precise sleep to hit target rate
            elapsed_work = time.time() - t0
            sleep_time = interval - elapsed_work
            if sleep_time > 0:
                time.sleep(sleep_time)
