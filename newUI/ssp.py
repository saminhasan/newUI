import os
import time
import serial
import numpy as np
from parser import Parser, decodePayload
from more_itertools import chunked
from Hexlink.commands import *
from multiprocessing import Process, Queue
from threading import Thread, Event


import logging

logger = logging.getLogger(__name__)


class Teensy:
    def __init__(self):
        self.teensy: serial.Serial = serial.Serial(port=None, timeout=None)
        self.log = logger.getChild(self.__class__.__name__)
        self.
    @property
    def connected(self) -> bool:
        try:
            return self.port.is_open and self.serial_worker is not None
        except Exception as e:
            # self.log.exception(f"{e}")
            self.log.error(f"{e}")
            return False

