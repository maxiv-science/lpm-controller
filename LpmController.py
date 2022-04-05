"""
Interface to the SLJUS "LPM" reactor. Keeps a constant stream
of traffic open in a threaded listener which updates the
latest temperature value. Other features can be added.

The device doesn't use newline characters for commands, and
instead there is a delay between writing the last character
and the device taking the command. Very sophisticated.

Also defines a contrast Motor which can be used for changing
the temperature and recording the snapshot.
"""

import serial
import time
import threading
from queue import Queue
from contrast.motors import Motor
from contrast.detectors import Detector

SLEEP = 2.

class Communicator(threading.Thread):
    def __init__(self, latest_T, port, baudrate=115200, timeout=.1):
        super(Communicator, self).__init__()
        self._stop_event = threading.Event()
        self.latest_T = latest_T
        self.q = Queue()
        self.s = serial.Serial(port, baudrate=baudrate, timeout=timeout)
        time.sleep(SLEEP)
        self.write('sam 5') # streaming at this rate

    def run(self):
        while not self._stop_event.isSet():
            if self.q.qsize():
                cmd = self.q.get()
                self.write(cmd)
                time.sleep(SLEEP)
            self.parse()
            time.sleep(1.)

    def join(self):
        self._stop_event.set()
        super(Communicator, self).join()

    def write(self, msg):
        self.s.write(bytes(msg, 'utf-8'))

    def read(self):
        return self.s.read(1000000).decode('utf-8')

    def parse(self):
        try:
            s = self.read()
            self.latest_T[0] = float(s.split('T: ')[-1].split(' ')[0])
        except:
            pass

class LpmController(object):

    def __init__(self, port='/dev/ttyACM1'):
        self._current_tmp = [None]
        self.comm = Communicator(port=port, latest_T=self._current_tmp)
        self.comm.start()
        self.comm.q.put('off')
        self.comm.q.put('tune 1.18 1.18 0.79')
        self.comm.q.put('pid')

    def set_temp(self, val):
        self.comm.q.put('set %f'%val)

    def get_temp(self):
        return self._current_tmp[0]

class LpmMotor(Motor):
    def __init__(self, dev, **kwargs):
        super(LpmMotor, self).__init__(**kwargs)
        self.lpm = dev

    @property
    def dial_position(self):
        return self.lpm.get_temp()

    @dial_position.setter
    def dial_position(self, pos):
        self.lpm.set_temp(pos)

    def busy(self):
        return False

class LpmDetector(Detector):
    def __init__(self, dev, **kwargs):
        super(LpmDetector, self).__init__(**kwargs)
        self.lpm = dev

    def initialize(self):
        pass

    def stop(self):
        pass

    def busy(self):
        return False

    def read(self):
        return self.lpm.get_temp()


# reactor = LpmController(port='/dev/ttyACM1')
reactor = LpmController(port='/dev/ttyUSB0')
reactor_motor = LpmMotor(name='reactor_mot', dev=reactor)
reactor_detector = LpmDetector(name='reactor_det', dev=reactor)

