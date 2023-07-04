import schedule, time, logging, datetime
import pytz
import json
from functools import partial
from gpiozero import Button, LED
from Config import Config
from FeedJob import FeedJob
from Daemon import Daemon
from Display import Display
from FeedingMachine import FeedingMachine
from MQTTClient import MQTTClient

logger = logging.getLogger(__name__)
tz = pytz.timezone('Europe/Amsterdam')

class CatFeeder(Daemon):

    lastJob = None
    lastJobRun = None
    lastJobStatus = "successful"

    statusLed = None
    display = None
    mqttClient = None

    statusLedActive = False
    feedingMachines = []
    feedJobs = []

    manualFeedingButton = None
    jobIsRunning = False

    def __init__(self):
        super(CatFeeder, self).__init__()

    def _setup(self):
        logger.info('Starting CatFeeder service')
        self._reloadConfig()

    def _runUser1Handler(self):
        self._feedPortions()

    def _initDisplay(self):
        self.display = Display(self.config)
        self.display.onManualFeed = self._feedPortions

    def _initManualFeedingButton(self):
        if self.config.manualFeedingButtonPort != None:
            self.manualFeedingButton = Button(self.config.manualFeedingButtonPort)
            self.manualFeedingButton.when_held = self._feedPortions
            self.manualFeedingButton.when_pressed = self._timeUntilNextFeeding

    def _initMqtt(self):
        def feeding_callback(portions):
            self._feedPortions(portions)

        def status_callback():
            nextJob = min(schedule.get_jobs('feeding'))
            feedJob = nextJob.job_func.keywords['feedJob']
            status = {
                "last_feed": None,
                "last_feed_portions": None,
                "last_feed_status": None,
                "next_feed": nextJob.next_run.replace(microsecond=0).astimezone().isoformat(),
                "next_feed_portions": feedJob.portions,
                "schedule_enabled": True
            }
            if self.lastJob != None:
                status["last_feed"] = self.lastJobRun.replace(microsecond=0).astimezone().isoformat()
                status["last_feed_portions"] = self.lastJob.portions
                status["last_feed_status"] = self.lastJobStatus
            return status

        def update_callback():
            pass

        def displaytest_callback(method, params):
            self.display.sendSignal(method, params)

        if self.mqttClient != None:
            self.mqttClient.disconnect()

        self.mqttClient = MQTTClient(self.config, {
            "feeding_callback": feeding_callback,
            "status_callback": status_callback,
            "update_callback": update_callback,
            "displaytest_callback": displaytest_callback
        })

        self.mqttClient.connect()
        self.mqttClient.send_status_message()

    def _timeUntilNextFeeding(self):
        next_job = min(schedule.get_jobs('feeding')).next_run
        if not next_job:
            logger.debug('no next feeding')
            return None;
        n = (next_job - datetime.datetime.now()).total_seconds()
        if n > 0:
            n = round(n / 60, 1)
            logger.info(str(n) + " minutes until the next feeding")
            return n;
        else:
            return 0;

    def _reloadConfig(self, config = None):
        if(config is None):
            config = Config()
            self.config = config
        self.config.readConfig()

        self._initManualFeedingButton()
        self._initDisplay()
        self._initStatusLed()
        self._reloadFeedingMachines()
        self._setupScheduler()
        self._initMqtt()
        self._timeUntilNextFeeding()

    def _reloadFeedingMachines(self):
        if self.statusLed != None:
            self.statusLed.blink(0.5,0.5,3)
        else:
            logger.debug('Reloading machines')
        for machine in self.feedingMachines:
            machine.closeAll()
        del self.feedingMachines[:]
        for machine in self.config.feedingMachines:
            if not machine['enabled']:
                logger.info('Machine '+machine['name']+' is disabled')
                continue
            newFeedingMachine = FeedingMachine(machine['name'], machine['motorPort'], machine['motorSensorPort'], machine['foodSensorPortOut'], machine['foodSensorPortIn'])
            self.feedingMachines.append(newFeedingMachine)

    def _initStatusLed(self):
        if self.config.statusLedPort != None:
            if self.statusLed:
                self.statusLed.close()
            self.statusLed = LED(self.config.statusLedPort)

    def _createFeedJob(self, portions = 1, time = None):
        feedJob = FeedJob(portions, time, self.feedingMachines)
        feedJob.onError = partial(self._jobErrorHandler, feedJob)
        feedJob.onFinish = partial(self._jobFinished, feedJob)
        feedJob.onSuccessful = partial(self._jobSuccessfulHandler, feedJob)
        return feedJob

    def _feedPortions(self, portions = 1):
        logger.debug('Manual feeding')
        feedJob = self._createFeedJob(portions)
        wasFed = self._runFeedJob(feedJob)
        if not wasFed:
            logger.warning('Cannot feed now, another feeding sequence is already running')

    def _runFeedJob(self, feedJob: FeedJob):
        if not self.jobIsRunning:
            self.jobIsRunning = True
            self.lastJob = feedJob
            self.lastJobRun = datetime.datetime.now()
            self.lastJobStatus = "running"
            self.mqttClient.send_status_message()
            feedJob.feed()
            self.display.sendTime()
            self._timeUntilNextFeeding()
            self.statusLedActive = True
            if self.statusLed != None:
                self.statusLed.on()
            return True
        else:
            return False

    def _jobSuccessfulHandler(self, feedJob, machine):
        self.lastJobStatus = "successful"

    def _jobErrorHandler(self, feedJob, machine, error):
        self.statusLedActive = True
        if error.code != None:
            self.lastJobStatus = error.code
        else:
            self.lastJobStatus = "error"
        if self.statusLed != None:
            self.statusLed.blink(0.1,0.2,30,False)
        self.statusLedActive = False

    def _jobFinished(self, feedJob):
        if self.statusLed != None:
            self.statusLed.off()
        self.statusLedActive = False
        self.jobIsRunning = False
        self.display.sendFeedingSuccessful(feedJob)
        logger.debug('Job has finished')
        self._timeUntilNextFeeding()
        self.mqttClient.send_status_message()

    def _heartbeat(self):
        if self.statusLed != None:
            if not self.statusLedActive:
                self.statusLed.blink(0.1,1,1)
        else:
            logger.debug('Heartbeat')

    def _setupScheduler(self):
        schedule.clear()
        self.feedJobs = []
        if self.statusLed != None:
            schedule.every(10).seconds.do(self._heartbeat).tag('debug')
        schedule.every().day.at("00:00").do(self.display.sendTime).tag('display')
        for feeding in self.config.schedule:
            logger.info("I will feed " + str(feeding['portions']) + " portions at " + feeding['time'])
            feedJob = self._createFeedJob(feeding['portions'], feeding['time'])
            schedule.every().day.at(feeding['time']).do(self._runFeedJob, feedJob=feedJob).tag('feeding')
            self.feedJobs.append(feedJob)

    def _unload(self):
        logger.info('Stopping CatFeeder service')
        schedule.clear()
        for machine in self.feedingMachines:
            machine.closeAll()
        if self.manualFeedingButton != None:
            self.manualFeedingButton.close()
        if self.statusLed != None:
            self.statusLed.close()
        if self.display != None:
            self.display.unload()
        if self.mqttClient != None:
            self.mqttClient.disconnect()

    def run(self):
        try:
            if self.isReloadSignal:
                self._reloadConfig()
                self.isReloadSignal = False
            else:
                schedule.run_pending()
        except Exception:
            raise
