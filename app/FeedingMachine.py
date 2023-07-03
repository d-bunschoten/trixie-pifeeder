from gpiozero import Button, OutputDevice, SmoothedInputDevice, LED
from functools import partial
import threading, time
import logging

logger = logging.getLogger(__name__)

class FeedingMachineError(Exception):
    """General Exception class for FeedingMachines

    Attributes:
        machine -- input machine where the motor failed
        roundsLeft -- how many rounds were still to go
        message -- explanation of the error
    """
    code = "error"

    def __init__(self, machine, roundsLeft, message):
        self.machine = machine
        self.roundsLeft = roundsLeft
        self.message = message

class MotorFailureError(FeedingMachineError):
    """Exception raised for motor failures
    """
    code = "blocked"

class FoodDispenseError(FeedingMachineError):
    """Exception raised when no food was dispensed
    """
    code = "empty"

class FeedingMachine:
    name = None

    motorSensor = None
    motor = None
    fakeMotor = None
    foodSensor = None
    foodSensorTrigger = None

    motorActive = False
    foodWasDispensed = None
    noFoodCounter = 0
    motorSensorWasPressed = True

    motorThreshold = 5
    maxAttempts = 5
    currentRound = None
    timeoutThread = None
    foodSensorThread = None

    motorPort = None
    motorSensorPort = None
    foodSensorPortOut = None
    foodSensorPortIn = None

    onFailure = None
    onFinish = None
    onSuccessful = None

    def __init__(self, name, motorPort = None, motorSensorPort = None, foodSensorPortOut = None, foodSensorPortIn = None):
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
        self.onSuccessful = doNothing
        logger.debug("new FeedingMachine ("+self.name+") installed")
        self.initGpio()

    def initGpio(self):
        # init GPIO in/output
        if self.motorSensorPort != None:
            self.motor = LED(self.motorPort)
            self.motorSensor = Button(self.motorSensorPort, None, False)
            self.motorSensor.when_pressed = self._motorSensorPressed
        if self.foodSensorPortIn != None:
            self.foodSensor = SmoothedInputDevice(self.foodSensorPortIn, pull_up=False, active_state=None, threshold=0.2, queue_len=40, sample_wait=0.1)
            self.foodSensorTrigger = LED(self.foodSensorPortOut)

    def closeAll(self):
        if self.motor != None:
            self.motor.close()
        if self.motorSensor != None:
            self.motorSensor.close()
        if self.foodSensor != None:
            self.foodSensor.close()
        if self.foodSensorTrigger != None:
            self.foodSensorTrigger.close()

    def _motorTimeout(self):
        if self.motorActive:
            logger.error('Machine '+self.name+': Sequence was canceled, motor took too long')
            roundsLeft = self.currentRound
            self.onFailure(MotorFailureError(self, roundsLeft, 'Motor took too long, possibly blocked'))
            self._stopSequence()

    def _cancelMotorTimeout(self):
        if self.timeoutThread != None:
            self.timeoutThread.cancel()
            self.timeoutThread = None

    def _stopMotor(self):
        logger.debug('Machine '+self.name+': Stopping motor')
        self._cancelMotorTimeout()
        if self.motor != None:
            self.motor.off()
        elif self.fakeMotor != None:
            self.fakeMotor.cancel()
        self.currentRound = None
        self.motorActive = False
        self.motorSensorWasPressed = True

    def _startMotor(self):
        if not self.motorActive:
            logger.debug('Machine '+self.name+': Starting motor')
            self.motorActive = True
            if self.motor != None:
                self.motor.on()
        if self.motor == None:
            #install fake motor
            self.fakeMotor = threading.Timer(3, self._motorSensorPressed)
            self.fakeMotor.start()

    def _setMotorSensorListener(self):
        self.motorSensorWasPressed = False

    def _motorSensorPressed(self):
        if self.motorSensorWasPressed:
            #event was already handled
            return
        logger.debug('Machine '+self.name+': Motor sensor for was pressed')
        self._cancelMotorTimeout()
        self.motorSensorWasPressed = True
        if self.foodWasDispensed == False:
            self.noFoodCounter = self.noFoodCounter + 1
            logger.debug(f"No food came out, trying again. (attempt {self.noFoodCounter}/{self.maxAttempts})")
            if self.noFoodCounter >= self.maxAttempts:
                logger.debug('Dispenser must be empty')
                self.onFailure(FoodDispenseError(self, self.currentRound, 'To many attempts, dispenser possibly empty'))
                self._stopSequence()
            else:
                self._nextSequence()
        else:
            self.currentRound = self.currentRound - 1;
            if self.currentRound is None or (not self.motorActive) or self.currentRound <= 0:
                #Finished! Stop the motor just a bit later, so the sensor button will be released
                threading.Timer(0.3, self._stopSequence).start()
                self.onSuccessful()
            else:
                self._nextSequence()

    def _startFoodSensor(self):
        if self.foodSensorTrigger != None:
            self.foodSensorTrigger.on()
        self.foodWasDispensed = True
        #temporary solution until I figured out how the sensor is working

    def _stopFoodSensor(self):
        if self.foodSensorTrigger != None:
            self.foodSensorTrigger.off()

    def _nextSequence(self):
        try:
            logger.debug('Machine '+self.name+': Next round sequence (still '+str(self.currentRound - 1)+' rounds to go)')
            self.timeoutThread = threading.Timer(self.motorThreshold, self._motorTimeout)
            self.timeoutThread.start()
            threading.Timer(0.5, self._setMotorSensorListener).start()
            self._startFoodSensor()
            self._startMotor()
        except Exception as err:
            logger.error('Something went wrong')
            self.onFailure(err)
            self._stopSequence()
            raise

    def _stopSequence(self):
        logger.debug('Machine '+self.name+': Ending sequence')
        self._stopFoodSensor()
        self._stopMotor()
        self.onFinish()

    def runSequence(self, rounds = 1):
        self.currentRound = rounds
        self.noFoodCounter = 0
        if self.currentRound > 0:
            logger.debug('Machine '+self.name+': Starting sequence of '+str(self.currentRound)+' rounds')
            threading.Thread(target=self._nextSequence).start()
        else:
            logger.error('Machine '+self.name+': Rounds must be at least 1')
