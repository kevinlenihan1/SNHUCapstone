from gpiozero import Button, PWMLED
from time import sleep, time
from datetime import datetime

from RPLCD.gpio import CharLCD
from RPi import GPIO

import board
import busio
import adafruit_ahtx0

# lcd setup
lcd = CharLCD(
    numbering_mode=GPIO.BCM,
    cols=16,
    rows=2,
    pin_rs=22,
    pin_e=24,
    pins_data=[5, 6, 13, 19]
)

# sensor setup
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_ahtx0.AHTx0(i2c)

# buttons
mode_btn = Button(17)
up_btn = Button(12)
down_btn = Button(25)

#leds
red = PWMLED(18)
blue = PWMLED(23)

# state
state = "OFF"
setpoint = 72

# button functions
def toggle_mode():
    global state
    if state == "OFF":
        state = "HEAT"
    elif state == "HEAT":
        state = "COOL"
    else:
        state = "OFF"

def increase_temp():
    global setpoint
    setpoint += 1

def decrease_temp():
    global setpoint
    setpoint -= 1

mode_btn.when_pressed = toggle_mode
up_btn.when_pressed = increase_temp
down_btn.when_pressed = decrease_temp

# main loop
last_uart = time()
display_toggle = True

while True:
    temp = sensor.temperature * 9/5 + 32  # convert C → F

    # led logic
    red.off()
    blue.off()

    if state == "HEAT":
        if temp < setpoint:
            red.pulse()
        else:
            red.on()

    elif state == "COOL":
        if temp > setpoint:
            blue.pulse()
        else:
            blue.on()

    # lcd display
    lcd.clear()
    now = datetime.now().strftime("%m/%d %H:%M")

    if display_toggle:
        line2 = f"Temp:{temp:.1f}F"
    else:
        line2 = f"{state} Set:{setpoint}"

    lcd.write_string(f"{now}\n{line2}")
    display_toggle = not display_toggle

    # uart output
    if time() - last_uart >= 30:
        print(f"{state},{temp:.1f},{setpoint}")
        last_uart = time()

    sleep(2)