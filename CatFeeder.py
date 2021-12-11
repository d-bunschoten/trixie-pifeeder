import schedule, time, logging, datetime
from functools import partial
from Config import Config
from FeedJob import FeedJob
from Daemon import Daemon
from Display import Display
from FeedingMachine import FeedingMachine
from gpiozero import Button, LED

class CatFeeder(Daemon):

    statusLed = None
    display = None
    statusLedActive = False
    feedingMachines = []
    feedJobs = []
    manualFeedingButton = None
    withDaemon = True
    jobIsRunning = False

    def __init__(self, stdIn='/dev/null', stdOut='/var/log/voerautomaat/voerautomaat.log', stdErr='/var/log/voerautomaat/error.log'):
        return super(CatFeeder, self).__init__(stdIn, stdOut, stdErr)

    def setDaemon(self, newSetting = True):
        self.withDaemon = newSetting

    def install(self):
        self.reloadConfig()
        self.initManualFeedingButton()
        self.timeUntilNextFeeding()

    def _setup(self):
        self.install()

    def _runUser1Handler(self):
        self.feedPortions()

    def initDisplay(self):
        self.display = Display(self.config)
        self.display.onManualFeed = self.feedPortions

    def initManualFeedingButton(self):
        self.manualFeedingButton = Button(self.config.manualFeedingButtonPort)
        self.manualFeedingButton.when_held = self.feedPortions
        self.manualFeedingButton.when_pressed = self.timeUntilNextFeeding

    def timeUntilNextFeeding(self):
        next_job = min(schedule.get_jobs('feeding')).next_run
        if not next_job:
            logging.debug('no next feeding')
            return None;
        n = (next_job - datetime.datetime.now()).total_seconds()
        if n > 0:
            n = round(n / 60, 1)
            logging.info(str(n) + " minutes until the next feeding")
            return n;
        else:
            return 0;

    def feedPortions(self, portions = 1):
        logging.debug('Manual feeding button was pressed')
        feedJob = FeedJob(portions, self.feedingMachines)
        wasFed = self.runFeedJob(feedJob)
        if not wasFed:
            logging.warning('Cannot feed now, another feeding sequence is already running')

    def reloadConfig(self, config = None):
        if(config is None):
            config = Config()
            self.config = config
        self.config.readConfig()
        self.initDisplay()
        self.initStatusLed()
        self.reloadFeedingMachines()
        self.setupScheduler()

    def reloadFeedingMachines(self):
        self.statusLed.blink(0.5,0.5,3)
        for machine in self.feedingMachines:
            machine.closeAll()
        del self.feedingMachines[:]
        for machine in self.config.feedingMachines:
            if not machine['enabled']:
                logging.info('Machine '+machine['name']+' is disabled')
                continue
            newFeedingMachine = FeedingMachine(machine['name'], machine['motorPort'], machine['motorSensorPort'], machine['foodSensorPortOut'], machine['foodSensorPortIn'])
            self.feedingMachines.append(newFeedingMachine)

    def initStatusLed(self):
        if self.statusLed:
            self.statusLed.close()
        self.statusLed = LED(self.config.statusLedPort)

    def runFeedJob(self, feedJob: FeedJob):
        if not self.jobIsRunning:
            feedJob.onError = partial(self._jobErrorHandler, feedJob)
            feedJob.onFinish = self._jobFinished
            self.jobIsRunning = True
            feedJob.feed()
            self.timeUntilNextFeeding()
            self.statusLedActive = True
            self.statusLed.on()
            return True
        else:
            return False

    def _jobErrorHandler(self, feedJob, machine, error):
        self.statusLedActive = True
        self.statusLed.blink(0.1,0.2,30,False)
        self.statusLedActive = False

    def _jobFinished(self):
        self.statusLed.off()
        self.statusLedActive = False
        self.jobIsRunning = False
        self.display.sendFeedingSuccessful()

    def _heartbeat(self):
        if not self.statusLedActive:
            self.statusLed.blink(0.1,1,1)

    def setupScheduler(self):
        schedule.clear()
        self.feedJobs = []
        schedule.every(10).seconds.do(self._heartbeat).tag('debug')
        schedule.every().day.at("00:00").do(self.display.sendTime).tag('display')
        for feeding in self.config.schedule:
            logging.info("I will feed " + str(feeding['portions']) + " portions at " + feeding['time'])
            feedJob = FeedJob(feeding['portions'], self.feedingMachines)
            schedule.every().day.at(feeding['time']).do(partial(self.runFeedJob, feedJob)).tag('feeding')
            self.feedJobs.append(feedJob)

    def run(self):
        try:
            if self.isReloadSignal:
                self.reloadConfig()
                self.isReloadSignal = False
            if not self.withDaemon:
                while True:
                    schedule.run_pending()
                    time.sleep(1)
            else:
                schedule.run_pending()
        except Exception:
            raise
