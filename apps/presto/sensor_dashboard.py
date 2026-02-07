"""Sensor dashboard for Presto - displays all available sensors.

Instantiates every sensor mock and displays live readings.
Use the emulator sensor panel sliders to change values.
"""

from presto import Presto, Buzzer
import time

# Initialize Presto
presto = Presto()
display = presto.display
WIDTH, HEIGHT = display.get_bounds()

# Initialize I2C bus
from machine import I2C, Pin
i2c = I2C(0, sda=Pin(4), scl=Pin(5))

# --- Initialize all sensors ---

from breakout_bme280 import BreakoutBME280
bme280 = BreakoutBME280(i2c)

from breakout_bme68x import BreakoutBME68X
bme68x = BreakoutBME68X(i2c, address=0x77)

from breakout_bmp280 import BreakoutBMP280
bmp280 = BreakoutBMP280(i2c)

from breakout_ltr559 import BreakoutLTR559
ltr559 = BreakoutLTR559(i2c)

from lsm6ds3 import LSM6DS3
imu = LSM6DS3(i2c)

import breakout_scd41
breakout_scd41.init(i2c)
breakout_scd41.start()

from breakout_sgp30 import BreakoutSGP30
sgp30 = BreakoutSGP30(i2c)

from breakout_rtc import BreakoutRTC
rtc = BreakoutRTC(i2c)
rtc.setup()

from breakout_icp10125 import BreakoutICP10125
icp = BreakoutICP10125(i2c)

from breakout_bh1745 import BreakoutBH1745
colour = BreakoutBH1745(i2c)

from breakout_msa301 import BreakoutMSA301
accel = BreakoutMSA301(i2c)

from breakout_potentiometer import BreakoutPotentiometer
pot = BreakoutPotentiometer(i2c)

from breakout_encoder import BreakoutEncoder
enc = BreakoutEncoder(i2c)

from breakout_vl53l5cx import BreakoutVL53L5CX
tof = BreakoutVL53L5CX(i2c)
tof.start_ranging()

from emulator import get_state
battery = get_state().get("battery")

# Buzzer
buzzer = Buzzer()
buzzer_on = False
buzzer_timer = 0

# --- Colors ---
BG = display.create_pen(20, 20, 25)
WHITE = display.create_pen(255, 255, 255)
HEADER_BG = display.create_pen(40, 60, 90)
ROW_EVEN = display.create_pen(28, 28, 33)
ROW_ODD = display.create_pen(35, 35, 40)
GREEN = display.create_pen(80, 220, 100)
YELLOW = display.create_pen(255, 200, 50)
CYAN = display.create_pen(80, 200, 220)
RED = display.create_pen(220, 80, 80)
ORANGE = display.create_pen(255, 160, 50)
PURPLE = display.create_pen(180, 100, 255)
DIM = display.create_pen(120, 120, 130)

# --- Layout ---
MARGIN = 4
COL1 = MARGIN
COL2 = WIDTH // 2 + 2
ROW_H = 17
HEADER_H = 20
GAP = 2


def draw_header(x, y, w, title):
    display.set_pen(HEADER_BG)
    display.rectangle(x, y, w, HEADER_H)
    display.set_pen(CYAN)
    display.set_font("bitmap8")
    display.text(title, x + 4, y + 3, w, 2)
    return y + HEADER_H + 1


def draw_row(x, y, w, label, value, color=WHITE, idx=0):
    bg = ROW_EVEN if idx % 2 == 0 else ROW_ODD
    display.set_pen(bg)
    display.rectangle(x, y, w, ROW_H)
    display.set_pen(DIM)
    display.set_font("bitmap8")
    display.text(label, x + 4, y + 2, w, 2)
    display.set_pen(color)
    display.text(str(value), x + w // 2, y + 2, w, 2)
    return y + ROW_H


# --- Main loop ---
frame = 0
while True:
    display.set_pen(BG)
    display.clear()

    half_w = WIDTH // 2 - MARGIN - 2

    # ========== LEFT COLUMN ==========
    y = MARGIN

    # BME280
    y = draw_header(COL1, y, half_w, "BME280")
    t, p, h = bme280.read()
    y = draw_row(COL1, y, half_w, "Temp", f"{t:.1f}C", GREEN, 0)
    y = draw_row(COL1, y, half_w, "Press", f"{p:.0f}hPa", YELLOW, 1)
    y = draw_row(COL1, y, half_w, "Humid", f"{h:.0f}%", CYAN, 2)

    y += GAP

    # BME68X
    y = draw_header(COL1, y, half_w, "BME68X")
    t2, p2, h2, gas, status, _, _ = bme68x.read()
    y = draw_row(COL1, y, half_w, "Temp", f"{t2:.1f}C", GREEN, 0)
    y = draw_row(COL1, y, half_w, "Gas", f"{gas:.0f}R", ORANGE, 1)

    y += GAP

    # SCD41
    y = draw_header(COL1, y, half_w, "SCD41 CO2")
    if breakout_scd41.ready():
        co2, st, sh = breakout_scd41.measure()
        co2_color = GREEN if co2 < 800 else YELLOW if co2 < 1200 else RED
        y = draw_row(COL1, y, half_w, "CO2", f"{co2}ppm", co2_color, 0)
    else:
        y = draw_row(COL1, y, half_w, "CO2", "wait...", DIM, 0)

    y += GAP

    # Light & Proximity
    y = draw_header(COL1, y, half_w, "LTR559")
    lux = ltr559.get_lux()
    prox = ltr559.get_proximity()
    y = draw_row(COL1, y, half_w, "Lux", f"{lux:.0f}", YELLOW, 0)
    y = draw_row(COL1, y, half_w, "Prox", f"{prox:.0f}", PURPLE, 1)

    y += GAP

    # IMU (LSM6DS3)
    y = draw_header(COL1, y, half_w, "LSM6DS3 IMU")
    ax, ay, az = imu.get_accel()
    y = draw_row(COL1, y, half_w, "Acc X", f"{ax:.2f}g", GREEN, 0)
    y = draw_row(COL1, y, half_w, "Acc Y", f"{ay:.2f}g", GREEN, 1)
    y = draw_row(COL1, y, half_w, "Acc Z", f"{az:.2f}g", GREEN, 2)

    y += GAP

    # MSA301
    y = draw_header(COL1, y, half_w, "MSA301")
    mx, my, mz = accel.read()
    y = draw_row(COL1, y, half_w, "Acc X", f"{mx:.2f}g", GREEN, 0)
    y = draw_row(COL1, y, half_w, "Acc Y", f"{my:.2f}g", GREEN, 1)

    # ========== RIGHT COLUMN ==========
    y = MARGIN

    # Battery
    y = draw_header(COL2, y, half_w, "Battery")
    if battery:
        level = battery.get_level()
        volts = battery._voltage
        charging = battery._charging
        level_color = GREEN if level > 60 else YELLOW if level > 30 else RED
        y = draw_row(COL2, y, half_w, "Level", f"{level}%", level_color, 0)
        y = draw_row(COL2, y, half_w, "Volts", f"{volts:.2f}V", CYAN, 1)
        chg_str = "YES" if charging else "no"
        y = draw_row(COL2, y, half_w, "Chg", chg_str, YELLOW if charging else DIM, 2)
    else:
        y = draw_row(COL2, y, half_w, "N/A", "---", DIM, 0)

    y += GAP

    # RTC
    y = draw_header(COL2, y, half_w, "RTC")
    rtc.update_time()
    y = draw_row(COL2, y, half_w, "Time", rtc.string_time(), WHITE, 0)
    y = draw_row(COL2, y, half_w, "Date", rtc.string_date(), DIM, 1)

    y += GAP

    # Air Quality
    y = draw_header(COL2, y, half_w, "SGP30")
    eco2, tvoc = sgp30.get_air_quality()
    y = draw_row(COL2, y, half_w, "eCO2", f"{eco2}ppm", GREEN, 0)
    y = draw_row(COL2, y, half_w, "TVOC", f"{tvoc}ppb", CYAN, 1)

    y += GAP

    # ICP10125 Pressure
    y = draw_header(COL2, y, half_w, "ICP10125")
    icp_t, icp_p, _ = icp.measure()
    y = draw_row(COL2, y, half_w, "Temp", f"{icp_t:.1f}C", GREEN, 0)
    y = draw_row(COL2, y, half_w, "Press", f"{icp_p:.0f}hPa", YELLOW, 1)

    y += GAP

    # Colour sensor
    y = draw_header(COL2, y, half_w, "BH1745")
    cr, cg, cb, cc = colour.read()
    y = draw_row(COL2, y, half_w, "R/G/B", f"{cr}/{cg}/{cb}", WHITE, 0)
    y = draw_row(COL2, y, half_w, "Clear", f"{cc}", DIM, 1)

    y += GAP

    # Potentiometer + Encoder
    y = draw_header(COL2, y, half_w, "Controls")
    y = draw_row(COL2, y, half_w, "Pot", f"{pot.read():.2f}", CYAN, 0)
    y = draw_row(COL2, y, half_w, "Enc", f"{enc.get_count()}", PURPLE, 1)

    # ========== Bottom: ToF mini heatmap ==========
    tof_y = HEIGHT - 48
    display.set_pen(HEADER_BG)
    display.rectangle(COL1, tof_y - 2, WIDTH - MARGIN * 2, 46)
    display.set_pen(CYAN)
    display.text("VL53L5CX ToF", COL1 + 4, tof_y, WIDTH, 2)

    if tof.data_ready():
        data = tof.get_data()
        res = 4
        cell = 10
        ox = COL1 + half_w + 20
        oy = tof_y + 3
        for row in range(res):
            for col in range(res):
                dist = data.distance_mm[row * res + col]
                # Map 0-2000mm to blue-green-red
                ratio = min(1.0, dist / 2000.0)
                r = int(255 * ratio)
                g = int(255 * (1 - abs(ratio - 0.5) * 2))
                b = int(255 * (1 - ratio))
                display.set_pen(display.create_pen(r, g, b))
                display.rectangle(ox + col * cell, oy + row * cell, cell - 1, cell - 1)

    # Buzzer beep every 60 frames
    if frame % 60 == 0 and not buzzer_on:
        buzzer.set_tone(440, 0.5)
        buzzer_on = True
        buzzer_timer = frame
    if buzzer_on and frame - buzzer_timer > 5:
        buzzer.stop()
        buzzer_on = False

    display.update()
    presto.update()
    time.sleep(0.05)
    frame += 1
