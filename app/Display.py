import serial, logging, threading
from time import sleep, localtime
from functools import partial

class Display:

    ser = None
    config = None
    ownAddress = [255,255]
    displayAddress = [255,252]

    onManualFeed = None

    def __init__(self, config):
        self.config = config
        try:
            self.ser = serial.Serial ("/dev/ttyS0", 2400, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE)
            self.onManualFeed = self._void
            threading.Thread(target=self._startListener).start()
            self.install()
        except serial.SerialException as err:
            pass

    def _void(self):
        pass

    def install(self):
        self.sendStatus()
        self.sendTime()
        self.sendFeedingJobs()

    def sendTime(self):
        now=localtime()
        self.sendSignal(9, [0, 0, 0, now.tm_hour, now.tm_min, now.tm_sec])

    def sendFeedingJobs(self):
        self.sendSignal(2, [0, 0, 0, 0, 0, 0, 0])
        maxSlots = 6
        counter = 1
        while counter <= maxSlots:
            if len(self.config.schedule) >= counter:
                feeding = self.config.schedule[counter-1]
                feedingTime = feeding['time'].split(":")
                portions = int(feeding['portions'])
                enabled = 16
                if portions > 0:
                    enabled = 17
                data = [int(feedingTime[0]), int(feedingTime[1]), portions, 0, enabled, counter, 1]
            else:
                data = [0, 0, 0, 0, 16, counter, 1]
            self.sendSignal(2, data)
            counter+=1
        self.sendSignal(2, [0, 0, 0, 0, 0, 0, 0])

    def sendFeedingSuccessful(self):
        self.sendSignal(12, [0])

    def sendStatus(self):
        self.sendSignal(5, [0])

    def sendSignal(self, method, data = []):
        line = self.displayAddress.copy()
        line.append(method)
        if len(data) > 0:
            line.append(len(data))
            line = line + data
        checksum = int(sum(line) & 0xFF)
        line.append(checksum)
        if self.ser is not None:
            self.ser.write(bytearray(line))

    def _interpretInput(self, method, data = []):
#        match method:
#            case 1:
        if method == 1 and len(data) > 1:
            self.sendSignal(1, [170])
            if data[1:] == [0,1,0,1,0,1]:
                self.onManualFeed()
            elif data[0] <= 24:
                #TODO: update feedingtime
                if data[5] == 6:
                    sleep(1)
                    self.sendFeedingJobs()
        elif method == 2:
            self.sendFeedingJobs()
        elif method == 5:
            #TODO: check status
            self.sendStatus()
        elif method == 6:
            self.sendSignal(6, [170])
            sleep(1)
            self.sendTime()
        elif method == 9:
            if len(data) > 0 and data[0] == 255:
                self.sendTime()
        elif method == 16:
            pass
            #TODO: play 'touch' sound
        elif method == 17 and len(data) > 0:
            if data[0] == 255:
                logging.debug('start recording')
            elif data[0] == 0:
                logging.debug('stop recording')
        elif method == 18:
            logging.debug('play recording')
        else:
            logging.warning("unknown UART signal received: ", [method, data])
        return

    def _validateInput(self, mth, len, data, checksum):
        calculatedChecksum = sum(self.ownAddress + [mth, len] + data) & 0xFF
        checksumSuccesful = checksum == calculatedChecksum
        if checksumSuccesful:
            self._interpretInput(mth, data)
        else:
            raise Exception('Checksum invalid', [mth, len, data, checksum])

    def _startListener(self):
        while True:
            try:
                self.ser.read_until(bytearray(self.ownAddress))
                meta = self.ser.read(2)
                mth = meta[0]
                len = meta[1]
                data = []
                if len > 0:
                    data = list(self.ser.read(len))
                checksum = self.ser.read(1)
                checksum = checksum[0]
                threading.Thread(target=partial(self._validateInput, mth, len, data, checksum)).start()
            except Exception:
                continue
