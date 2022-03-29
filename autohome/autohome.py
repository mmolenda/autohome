#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import configparser
import logging
import os
import sys
import time
from datetime import datetime
from collections import namedtuple
from datetime import datetime
import RPi.GPIO as GPIO
from IntegraPy import Integra
from suntime import Sun

HERE = os.path.abspath(os.path.dirname(__file__))
COMMAND = 'command'
sys.stdout.flush()
log = logging.getLogger(__name__)


DCSensor = namedtuple('DCSensor', ['id', 'label', 'correction'])
ReadTemperature = namedtuple('ReadTemperature', ['label', 'value'])


class AutoHome:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read(os.path.join(HERE, '..', 'integra.ini'))
        self.integra = Integra(config['Integra']['pin'], config['Integra']['host'])
        GPIO.setmode(GPIO.BCM)
        self.SLEEP_ENTRANCE = 4
        self.SLEEP_GATE = 0.5
        self.SLEEP_GARAGE = 2
        self.RELAY_1_GATE = 18
        self.RELAY_2_ENTRANCE = 23
        self.RELAY_3_HEATING = 24
        self.RELAY_4_GARAGE = 25
        self.ALARM_ZONE_GARAGE = 8
        self.ALARM_ZONES = {
            self.ALARM_ZONE_GARAGE: 'Garaz brama',
            9: 'Garaz drzwi'
        }
        self.DC_SENSOR_PATH = '/sys/bus/w1/devices/{}/w1_slave'
        self.DC_SENSORS = (
            DCSensor(id='28-8a20285896ff', label='Zewnatrz', correction=1),
            DCSensor(id='28-03199779455d', label='Parter', correction=1.06),
            DCSensor(id='28-03179779ca7d', label='Pietro', correction=1.06),
            DCSensor(id='28-031897792d45', label='Piwnica', correction=1.06),
            DCSensor(id='28-03199779139e', label='Strych', correction=1.06)
        )
        self.COORDINATES = (51.21, 21.01)  # Warsaw, PL

    def command_gate(self):
        GPIO.setup(self.RELAY_1_GATE, GPIO.OUT, initial=GPIO.LOW)
        self._sleep(self.SLEEP_GATE)
        GPIO.output(self.RELAY_1_GATE, GPIO.HIGH)
        GPIO.cleanup()
        return 'Otwieram lub zamykam brame'

    def command_entrance(self):
        GPIO.setup(self.RELAY_2_ENTRANCE, GPIO.OUT, initial=GPIO.LOW)
        self._sleep(self.SLEEP_ENTRANCE)
        GPIO.output(self.RELAY_2_ENTRANCE, GPIO.HIGH)
        GPIO.cleanup()
        return 'Otwieram furtke'

    def command_garage(self, opened=None):
        GPIO.setup(self.RELAY_4_GARAGE, GPIO.OUT, initial=GPIO.LOW)
        self._sleep(self.SLEEP_GARAGE)
        GPIO.output(self.RELAY_4_GARAGE, GPIO.HIGH)
        GPIO.cleanup()
        return 'Otwieram lub zamykam garaz.'

    def command_garage_close(self):
        try:
            opened = self._is_garage_open()
        except (ConnectionRefusedError, IOError) as e:
            return 'Nie mozna sprawdzic stanu bramy garazu. Nie zamykam.'
        else:
            if self._is_after_sunset() and opened is True:
                self.command_garage(opened=opened)

    def _is_garage_open(self):
        return self.ALARM_ZONE_GARAGE in self.integra.get_violated_zones()

    def _is_after_sunset(self):
        sun = Sun(*self.COORDINATES)
        ss = sun.get_sunset_time()
        return datetime.utcnow() > datetime(ss.year, ss.month, ss.day, ss.hour, ss.minute)

    def command_heatingoff(self):
        GPIO.setup(self.RELAY_3_HEATING, GPIO.OUT, initial=GPIO.LOW)
        return 'Kociol w trybie antryfreeze'

    def command_heatingon(self):
        GPIO.setup(self.RELAY_3_HEATING, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.cleanup()
        return 'Kociol w trybie normalnym'

    def command_violated_zones(self):
        retval = []
        violated_zones = self.integra.get_violated_zones()
        for zone_id, zone_name in self.ALARM_ZONES.items():
            retval.append('{} [{}]'.format(zone_name, '*' if zone_id in violated_zones else ' '))
        return '\n'.join(retval)

    def command_temperature(self):
        retval = []
        for temperature in self._get_temperatures():
            value = f'{temperature.value}°C' if temperature.value else '-'
            retval.append(f'{temperature.label}: {value}')
        return '\n'.join(retval)

    def command_temperature_csv(self):
        retval = []
        now = datetime.now()
        line = [datetime.strftime(now, '%Y-%m-%d %H:%M:%S'), datetime.strftime(now, '%s')]
        line.extend(i.value or '' for i in self._get_temperatures())
        retval.append(','.join([str(i) for i in line]))
        return '\n'.join(retval)

    def _get_temperatures(self):
        for dc_sensor in self.DC_SENSORS:
            try:
                with open(self.DC_SENSOR_PATH.format(dc_sensor.id)) as fh:
                    raw_temperature = fh.readlines()[-1].strip().split('=')[1]
                    temperature = round(int(raw_temperature) * dc_sensor.correction / 1000, 1)
                    if temperature > 60:
                        log.warn(f'Temp powyzej 60 st: {dc_sensor.label}')
                        temperature = None
            except (FileNotFoundError, IndexError, ValueError) as e:
                log.error(f'Nie można odczytc temperatury dla: {dc_sensor.label}. {e}')
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
        stream=sys.stderr,
        level={0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}.get(args.verbose, logging.DEBUG),
        format='%(asctime)s %(levelname)s: %(message)s')
    logging.getLogger('IntegraPy').setLevel(logging.CRITICAL)

    autohome = AutoHome()
    print(getattr(autohome, f'{COMMAND}_{getattr(args, COMMAND)}')())
