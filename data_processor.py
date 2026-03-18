# ─────────────────────────────────────────────
#  CanSat Ground Station  |  data_processor.py
#  Runs in a background QThread.
#  Pulls packets from queue, applies Madgwick,
#  computes derived values, emits Qt signal.
# ─────────────────────────────────────────────

import csv
import math
import os
import queue
import time
from collections import deque
from datetime import datetime

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

import config


# ── Minimal Madgwick implementation (no ahrs dependency required) ─────────────
class MadgwickFilter:
    """
    Lightweight Madgwick AHRS. Operates on raw gyro (rad/s) and accel (g).
    Maintains quaternion state [w, x, y, z].
    """

    def __init__(self, beta: float = 0.1, sample_rate: float = 5.0):
        self.beta = beta
        self.dt = 1.0 / sample_rate
        self.q = np.array([1.0, 0.0, 0.0, 0.0])

    def update(self, ax, ay, az, gx, gy, gz):
        q = self.q
        qw, qx, qy, qz = q

        # Normalise accelerometer
        norm = math.sqrt(ax * ax + ay * ay + az * az)
        if norm < 1e-10:
            return self.q.copy()
        ax /= norm
        ay /= norm
        az /= norm

        # Gradient descent step (simplified — no magnetometer)
        f1 = 2 * (qx * qz - qw * qy) - ax
        f2 = 2 * (qw * qx + qy * qz) - ay
        f3 = 2 * (0.5 - qx * qx - qy * qy) - az

        J = np.array(
            [
                [-2 * qy, 2 * qz, -2 * qw, 2 * qx],
                [2 * qx, 2 * qw, 2 * qz, 2 * qy],
                [0, -4 * qx, -4 * qy, 0],
            ]
        )

        step = J.T @ np.array([f1, f2, f3])
        n = np.linalg.norm(step)
        if n > 1e-10:
            step /= n

        # Rate of change of quaternion from gyro
        qdot = (
            0.5
            * np.array(
                [
                    -qx * gx - qy * gy - qz * gz,
                    qw * gx + qy * gz - qz * gy,
                    qw * gy - qx * gz + qz * gx,
                    qw * gz + qx * gy - qy * gx,
                ]
            )
            - self.beta * step
        )

        self.q += qdot * self.dt
        self.q /= np.linalg.norm(self.q)
        return self.q.copy()


# ── Processing thread ─────────────────────────────────────────────────────────
class DataProcessor(QThread):
    """
    Consumes raw packets from in_queue, applies sensor fusion,
    emits processed_data signal to the UI thread.
    """

    processed_data = pyqtSignal(dict)

    def __init__(self, in_queue: queue.Queue, parent=None):
        super().__init__(parent)
        self.in_queue = in_queue
        self._running = True

        self._madgwick = MadgwickFilter(
            beta=config.MADGWICK_BETA,
            sample_rate=config.MOCK_RATE_HZ,
        )

        # Rolling buffers
        n = config.BUFFER_SIZE
        self.buf_time = deque(maxlen=n)
        self.buf_alt_a = deque(maxlen=n)
        self.buf_alt_r = deque(maxlen=n)
        self.buf_ax = deque(maxlen=n)
        self.buf_ay = deque(maxlen=n)
        self.buf_az = deque(maxlen=n)
        self.buf_gx = deque(maxlen=n)
        self.buf_gy = deque(maxlen=n)
        self.buf_gz = deque(maxlen=n)
        self.buf_temp1 = deque(maxlen=n)
        self.buf_temp2 = deque(maxlen=n)
        self.buf_press = deque(maxlen=n)
        self.buf_accel_mag = deque(maxlen=n)
        self.buf_gyro_mag = deque(maxlen=n)

        # Velocity (simple finite difference on altitude)
        self._prev_alt = None
        self._prev_time = None
        self.buf_vel = deque(maxlen=n)

        # Packet stats
        self._packet_times = deque(maxlen=20)
        self.packet_rate = 0.0
        self.total_packets = 0
        self.bad_packets = 0

        # CSV logger state
        self._csv_file = None
        self._csv_writer = None
        self.logging = False

    # ── CSV logging ──────────────────────────────────────────────────────────

    def start_logging(self):
        os.makedirs(config.LOG_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(config.LOG_DIR, f"cansat_{ts}.csv")
        self._csv_file = open(path, "w", newline="")
        self._csv_writer = csv.DictWriter(
            self._csv_file,
            fieldnames=config.CSV_FIELDS,
            extrasaction="ignore",
        )
        self._csv_writer.writeheader()
        self.logging = True
        return path

    def stop_logging(self):
        self.logging = False
        if self._csv_file:
            self._csv_file.flush()
            self._csv_file.close()
            self._csv_file = None
            self._csv_writer = None

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        while self._running:
            try:
                raw = self.in_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            now = time.time()
            self._packet_times.append(now)
            self.total_packets += 1

            # Packet rate estimate
            if len(self._packet_times) >= 2:
                span = self._packet_times[-1] - self._packet_times[0]
                if span > 0:
                    self.packet_rate = (len(self._packet_times) - 1) / span

            # ── Sensor fusion ─────────────────────────────────────────────────
            gx_rad = raw["gx"] * config.DEG2RAD
            gy_rad = raw["gy"] * config.DEG2RAD
            gz_rad = raw["gz"] * config.DEG2RAD

            q = self._madgwick.update(
                raw["ax"],
                raw["ay"],
                raw["az"],
                gx_rad,
                gy_rad,
                gz_rad,
            )

            # ── Derived values ────────────────────────────────────────────────
            t_ms = raw["timestamp_ms"]
            t_s = t_ms / 1000.0

            accel_mag = math.sqrt(raw["ax"] ** 2 + raw["ay"] ** 2 + raw["az"] ** 2)
            gyro_mag = math.sqrt(raw["gx"] ** 2 + raw["gy"] ** 2 + raw["gz"] ** 2)

            # Vertical velocity via finite difference
            if self._prev_alt is not None and self._prev_time is not None:
                dt_v = t_s - self._prev_time
                velocity = (
                    (raw["alt_absolute"] - self._prev_alt) / dt_v if dt_v > 0 else 0.0
                )
            else:
                velocity = 0.0
            self._prev_alt = raw["alt_absolute"]
            self._prev_time = t_s

            # ── Buffer append ─────────────────────────────────────────────────
            self.buf_time.append(t_s)
            self.buf_alt_a.append(raw["alt_absolute"])
            self.buf_alt_r.append(raw["alt_relative"])
            self.buf_ax.append(raw["ax"])
            self.buf_ay.append(raw["ay"])
            self.buf_az.append(raw["az"])
            self.buf_gx.append(raw["gx"])
            self.buf_gy.append(raw["gy"])
            self.buf_gz.append(raw["gz"])
            self.buf_temp1.append(raw["ntc_thermistor"])
            self.buf_temp2.append(raw["ntc_ms5611"])
            self.buf_press.append(raw["pressure"])
            self.buf_accel_mag.append(accel_mag)
            self.buf_gyro_mag.append(gyro_mag)
            self.buf_vel.append(velocity)

            # ── Build output dict ─────────────────────────────────────────────
            processed = {
                **raw,
                "qw": float(q[0]),
                "qx": float(q[1]),
                "qy": float(q[2]),
                "qz": float(q[3]),
                "accel_magnitude": round(accel_mag, 3),
                "gyro_magnitude": round(gyro_mag, 3),
                "velocity": round(velocity, 2),
                "packet_rate": round(self.packet_rate, 1),
                "total_packets": self.total_packets,
                # snapshot arrays for plots (converted to list for signal passing)
                "plot_time": list(self.buf_time),
                "plot_alt_a": list(self.buf_alt_a),
                "plot_alt_r": list(self.buf_alt_r),
                "plot_ax": list(self.buf_ax),
                "plot_ay": list(self.buf_ay),
                "plot_az": list(self.buf_az),
                "plot_gx": list(self.buf_gx),
                "plot_gy": list(self.buf_gy),
                "plot_gz": list(self.buf_gz),
                "plot_temp1": list(self.buf_temp1),
                "plot_temp2": list(self.buf_temp2),
                "plot_press": list(self.buf_press),
                "plot_vel": list(self.buf_vel),
            }

            # ── CSV write ─────────────────────────────────────────────────────
            if self.logging and self._csv_writer:
                try:
                    self._csv_writer.writerow(processed)
                except Exception:
                    pass

            self.processed_data.emit(processed)

    def stop(self):
        self._running = False
        self.stop_logging()
        self.wait()
