from gpiozero import Button, PWMLED
from time import sleep, time
from datetime import datetime
from enum import Enum

from RPLCD.gpio import CharLCD
from RPi import GPIO

import board
import busio
import adafruit_ahtx0


# thermostat operating modes
class ThermostatMode(Enum):
    OFF = "OFF"
    HEAT = "HEAT"
    COOL = "COOL"


class ThermostatController:

    # thermostat limits
    MIN_SETPOINT = 60
    MAX_SETPOINT = 85
    DEFAULT_SETPOINT = 72

    # timing values
    UART_INTERVAL = 30
    DISPLAY_INTERVAL = 2

    def __init__(self):

        # current thermostat state
        self.mode = ThermostatMode.OFF
        self.setpoint = self.DEFAULT_SETPOINT

        self.last_uart = time()
        self.display_toggle = True

        # initialize hardware
        self.lcd = self.setup_lcd()
        self.sensor = self.setup_sensor()

        # buttons
        self.mode_btn = Button(17)
        self.up_btn = Button(12)
        self.down_btn = Button(25)

        # status leds
        self.red_led = PWMLED(18)
        self.blue_led = PWMLED(23)

        self.assign_button_events()

    # create lcd object
    def setup_lcd(self):
        return CharLCD(
            numbering_mode=GPIO.BCM,
            cols=16,
            rows=2,
            pin_rs=22,
            pin_e=24,
            pins_data=[5, 6, 13, 19]
        )

    # create temperature sensor object
    def setup_sensor(self):
        i2c = busio.I2C(board.SCL, board.SDA)
        return adafruit_ahtx0.AHTx0(i2c)

    # connect button presses to functions
    def assign_button_events(self):
        self.mode_btn.when_pressed = self.toggle_mode
        self.up_btn.when_pressed = self.increase_setpoint
        self.down_btn.when_pressed = self.decrease_setpoint

    # switch between off, heat, and cool
    def toggle_mode(self):
        if self.mode == ThermostatMode.OFF:
            self.mode = ThermostatMode.HEAT
        elif self.mode == ThermostatMode.HEAT:
            self.mode = ThermostatMode.COOL
        else:
            self.mode = ThermostatMode.OFF

    # raise setpoint
    def increase_setpoint(self):
        if self.setpoint < self.MAX_SETPOINT:
            self.setpoint += 1

    # lower setpoint
    def decrease_setpoint(self):
        if self.setpoint > self.MIN_SETPOINT:
            self.setpoint -= 1

    # read current temperature
    def read_temperature(self):
        try:
            return self.sensor.temperature * 9 / 5 + 32
        except Exception as error:
            print(f"Sensor error: {error}")
            return None

    # update led status
    def update_leds(self, temperature):

        self.red_led.off()
        self.blue_led.off()

        if temperature is None:
            return

        if self.mode == ThermostatMode.HEAT:
            if temperature < self.setpoint:
                self.red_led.pulse()
            else:
                self.red_led.on()

        elif self.mode == ThermostatMode.COOL:
            if temperature > self.setpoint:
                self.blue_led.pulse()
            else:
                self.blue_led.on()

    # update lcd screen
    def update_display(self, temperature):
        try:

            self.lcd.clear()

            now = datetime.now().strftime("%m/%d %H:%M")

            if temperature is None:
                line2 = "Sensor Error"
            elif self.display_toggle:
                line2 = f"Temp:{temperature:.1f}F"
            else:
                line2 = f"{self.mode.value} Set:{self.setpoint}"

            self.lcd.write_string(f"{now}\n{line2[:16]}")

            self.display_toggle = not self.display_toggle

        except Exception as error:
            print(f"LCD error: {error}")

    # send serial output every 30 seconds
    def send_uart_update(self, temperature):

        if time() - self.last_uart >= self.UART_INTERVAL:

            temp_output = (
                "ERROR"
                if temperature is None
                else f"{temperature:.1f}"
            )

            print(
                f"{self.mode.value},"
                f"{temp_output},"
                f"{self.setpoint}"
            )

            self.last_uart = time()

    # main thermostat loop
    def run(self):

        try:

            while True:

                temperature = self.read_temperature()

                self.update_leds(temperature)
                self.update_display(temperature)
                self.send_uart_update(temperature)

                sleep(self.DISPLAY_INTERVAL)

        except KeyboardInterrupt:
            print("Thermostat shutting down...")

        finally:

            # turn everything off before exit
            self.red_led.off()
            self.blue_led.off()

            self.lcd.clear()

            GPIO.cleanup()


if __name__ == "__main__":

    thermostat = ThermostatController()
    thermostat.run()