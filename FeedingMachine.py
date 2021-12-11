from gpiozero import Button, OutputDevice, SmoothedInputDevice, LED
from functools import partial
import threading, time

class FeedingMachineError(Exception):
    """General Exception class for FeedingMachines

    Attributes:
        machine -- input machine where the motor failed
        roundsLeft -- how many rounds were still to go
        message -- explanation of the error
    """
    def __init__(self, machine, roundsLeft, message):
        self.machine = machine
        self.roundsLeft = roundsLeft
        self.message = message

class MotorFailureError(FeedingMachineError):
    """Exception raised for motor failures
    """

class FoodDispenseError(FeedingMachineError):
    """Exception raised when no food was dispensed
    """

class FeedingMachine:
    name = None

    motorSensor = None
    motor = None
    foodSensor = None
    foodSensorTrigger = None

    motorActive = False
    foodWasDispensed = None
    motorSensorWasPressed = True

    motorThreshold = 5
    currentRound = None
    timeoutThread = None
    foodSensorThread = None

    motorPort = None
    motorSensorPort = None
    foodSensorPortOut = None
    foodSensorPortIn = None

    onFailure = None
    onFinish = None

    def __init__(self, name, motorPort, motorSensorPort, foodSensorPortOut = None, foodSensorPortIn = None):
        #gpio ports input
        self.name = name
        self.motorPort = motorPort
        self.motorSensorPort = motorSensorPort
        if foodSensorPortIn != None:
            self.foodSensorPortOut = foodSensorPortOut
            self.foodSensorPortIn = foodSensorPortIn
        def doNothing():
            return
        self.onFailure = doNothing
        self.onFinish = doNothing
        print("new FeedingMachine ("+self.name+") installed")
        self.initGpio()

    def initGpio(self):
        # init GPIO in/output
        self.motor = LED(self.motorPort)
        self.motorSensor = Button(self.motorSensorPort, None, False)
        self.motorSensor.when_pressed = self._motorSensorPressed
        if self.foodSensorPortIn != None:
            self.foodSensor = SmoothedInputDevice(self.foodSensorPortIn, pull_up=False, active_state=None, threshold=0.2, queue_len=40, sample_wait=0.1)
            self.foodSensorTrigger = LED(self.foodSensorPortOut)

    def closeAll(self):
        self.motor.close()
        self.motorSensor.close()
        if self.foodSensor != None:
            self.foodSensor.close()
            self.foodSensorTrigger.close()

    def _motorTimeout(self):
        if self.motorActive:
            print('Machine '+self.name+': Sequence was canceled, motor took too long')
            roundsLeft = self.currentRound
            self._stopSequence()
            self.onFailure(MotorFailureError(self, roundsLeft, 'Motor took too long, possibly blocked'))

    def _cancelMotorTimeout(self):
        if self.timeoutThread != None:
            self.timeoutThread.cancel()
            self.timeoutThread = None

    def _stopMotor(self):
        print('Machine '+self.name+': Stopping motor')
        self._cancelMotorTimeout()
        self.motor.off()
        self.currentRound = None
        self.motorActive = False
        self.motorSensorWasPressed = True

    def _startMotor(self):
        if not self.motorActive:
            #self.motor.on()
            print('Machine '+self.name+': Starting motor')
            self.motorActive = True
            self.motor.on()

    def _setMotorSensorListener(self):
        self.motorSensorWasPressed = False

    def _motorSensorPressed(self):
        if self.motorSensorWasPressed:
            #event was already handled
            return
        print('Machine '+self.name+': Motor sensor for was pressed')
        self.motorSensorWasPressed = True
        if self.currentRound is None:
            self._cancelMotorTimeout()
            self._stopSequence()
        self.currentRound = self.currentRound - 1;
        self._cancelMotorTimeout()
        if (not self.motorActive) or self.currentRound <= 0:
            #stop the motor just a bit later, so the sensor button will be released
            threading.Timer(0.3, self._stopSequence).start()
        else:
            self._nextSequence()

    def _startFoodSensor(self):
        self.foodSensorTrigger.on()
        self.foodWasDispensed = True

    def _stopFoodSensor(self):
        self.foodSensorTrigger.off()

    def _nextSequence(self):
        try:
            print('Machine '+self.name+': Next round sequence (still '+str(self.currentRound - 1)+' rounds to go)')
            self.timeoutThread = threading.Timer(self.motorThreshold, self._motorTimeout)
            self.timeoutThread.start()
            threading.Timer(0.5, self._setMotorSensorListener).start()
            self._startFoodSensor()
            self._startMotor()
        except Exception as err:
            print('Something went wrong')
            self._stopSequence()
            self.onFailure(err)
            raise

    def _stopSequence(self):
        print('Machine '+self.name+': Ending sequence')
        self._stopFoodSensor()
        self._stopMotor()
        self.onFinish()

    def runSequence(self, rounds = 1):
        self.currentRound = rounds
        if self.currentRound > 0:
            print('Machine '+self.name+': Starting sequence of '+str(self.currentRound)+' rounds')
            threading.Thread(target=self._nextSequence).start()
        else:
            print('Machine '+self.name+': Rounds must be at least 1')
