import logging
from unittest.mock import MagicMock
import sys
MockGPIO = MagicMock()
OUT = MockGPIO.GPIO.OUT
LOW = MockGPIO.GPIO.LOW
HIGH = MockGPIO.GPIO.HIGH

sys.modules['RPi'] = MockGPIO
sys.modules['RPi.GPIO'] = MockGPIO
mockX = MagicMock()
mockX.__getitem__.side_effect = lambda x: {'pin': '0000', 'host': '0.0.0.0'}
mockCp = MagicMock()
mockCp.ConfigParser.return_value = mockX
sys.modules['configparser'] = mockCp
from autohome.autohome import AutoHome

autohome = AutoHome()
autohome._sleep = lambda x: x

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s')


def test_gate():
    autohome.command_gate()
    MockGPIO.GPIO.setup.assert_called_with(autohome.RELAY_1_GATE, OUT, initial=LOW)
    MockGPIO.GPIO.output(autohome.RELAY_1_GATE, HIGH)
    MockGPIO.GPIO.cleanup.assert_called()


def test_entrance():
    autohome.command_entrance()
    MockGPIO.GPIO.setup.assert_called_with(autohome.RELAY_2_ENTRANCE, OUT, initial=LOW)
    MockGPIO.GPIO.output(autohome.RELAY_2_ENTRANCE, HIGH)
    MockGPIO.GPIO.cleanup.assert_called()


def test_garage_opened():
    autohome.integra.get_violated_zones = lambda: [8]
    autohome.command_garage()
    MockGPIO.GPIO.setup.assert_called_with(autohome.RELAY_4_GARAGE, OUT, initial=LOW)
    MockGPIO.GPIO.output(autohome.RELAY_4_GARAGE, HIGH)
    MockGPIO.GPIO.cleanup.assert_called()

