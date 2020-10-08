#!/usr/bin/env python3

import argparse
import logging
import sys
import time
from collections import namedtuple
from datetime import datetime
import RPi.GPIO as GPIO

COMMAND = 'command'
sys.stdout.flush()
log = logging.getLogger(__name__)


DCSensor = namedtuple('DCSensor', ['id', 'label', 'correction'])
ReadTemperature = namedtuple('ReadTemperature', ['label', 'value'])


class AutoHome:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        self.SLEEP_ENTRANCE = 3
        self.SLEEP_GATE = 0.5
        self.RELAY_1_GATE = 18
        self.RELAY_2_ENTRANCE = 23
        self.RELAY_3_HEATING = 24
        self.RELAY_4 = 25
        self.DC_SENSOR_PATH = '/sys/bus/w1/devices/{}/w1_slave'
        self.DC_SENSORS = (
            DCSensor(id='28-8a20285896ff', label='Zewnątrz', correction=1),
            DCSensor(id='28-03199779455d', label='Parter', correction=1.06),
            DCSensor(id='28-03179779ca7d', label='Piętro', correction=1.06),
            DCSensor(id='28-031897792d45', label='Piwnica', correction=1.06)
        )

    def command_gate(self):
        self._print('Otwieram lub zamykam bramę')
        GPIO.setup(self.RELAY_1_GATE, GPIO.OUT, initial=GPIO.LOW)
        self._sleep(self.SLEEP_GATE)
        GPIO.output(self.RELAY_1_GATE, GPIO.HIGH)
        self._print('OK')
        GPIO.cleanup()

    def command_entrance(self):
        self._print('Otwieram furtkę')
        GPIO.setup(self.RELAY_2_ENTRANCE, GPIO.OUT, initial=GPIO.LOW)
        self._sleep(self.SLEEP_ENTRANCE)
        GPIO.output(self.RELAY_2_ENTRANCE, GPIO.HIGH)
        self._print('Zamykam')
        GPIO.cleanup()

    def command_heatingoff(self):
        self._print('Kocioł w trybie antryfreeze')
        GPIO.setup(self.RELAY_3_HEATING, GPIO.OUT, initial=GPIO.LOW)
        self._print('OK')

    def command_heatingon(self):
        self._print('Kocioł w trybie normalnym')
        GPIO.setup(self.RELAY_3_HEATING, GPIO.OUT, initial=GPIO.HIGH)
        self._print('OK')
        GPIO.cleanup()

    def command_temperature(self):
        for temperature in self._get_temperatures():
            value = f'{temperature.value}°C' if temperature.value else '-'
            self._print(f'{temperature.label}: {value}')

    def command_temperature_csv(self):
        line = [datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')]
        line.extend(i.value or '' for i in self._get_temperatures())
        self._print(','.join([str(i) for i in line]))

    def _get_temperatures(self):
        for dc_sensor in self.DC_SENSORS:
            try:
                with open(self.DC_SENSOR_PATH.format(dc_sensor.id)) as fh:
                    raw_temperature = fh.readlines()[-1].strip().split('=')[1]
                    temperature = round(int(raw_temperature) * dc_sensor.correction / 1000, 1)
            except (FileNotFoundError, IndexError, ValueError) as e:
                log.error(f'Nie można odczytać temperatury dla: {dc_sensor.label}. {e}')
                temperature = None
            finally:
                yield ReadTemperature(label=dc_sensor.label, value=temperature)

    def _print(self, message):
        print(message, flush=True)

    def _sleep(self, seconds):
        if seconds <= 1:
            time.sleep(seconds)
        else:
            for i in reversed(range(1, int(seconds) + 1)):
                self._print(f'{i}...')
                time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(COMMAND, choices=[i.replace(f'{COMMAND}_', '') for i in dir(AutoHome) if i.startswith(COMMAND)])
    parser.add_argument('-v', '--verbose', action='count', default=0)
    args = parser.parse_args()

    logging.basicConfig(
        stream=sys.stdout,
        level={0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}.get(args.verbose, logging.DEBUG),
        format='%(asctime)s %(levelname)s: %(message)s')

    autohome = AutoHome()
    getattr(autohome, f'{COMMAND}_{getattr(args, COMMAND)}')()

