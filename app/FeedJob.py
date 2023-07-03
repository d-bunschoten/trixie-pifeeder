import time, logging
from functools import partial

logger = logging.getLogger(__name__)

class FeedJob:
    portions = 0
    feedingMachines = []

    machinesDone = 0
    time = None

    onError = None
    onSuccessful = None
    onFinish = None

    def __init__(self, portions, time, feedingMachines):
        self.portions = portions
        self.time = time
        self.feedingMachines = feedingMachines
        def doNothing():
            return
        self.onError = doNothing
        self.onFinish = doNothing
        self.onSuccessful = doNothing

    def _failureHandler(self, machine, error):
        currentRound = (self.portions - error.roundsLeft) + 1
        logger.error('Machine '+machine.name+' failed on portion #'+str(currentRound)+': '+error.message)
        self.onError(machine, error)
        # possibly send Notification here

    def _finishHandler(self, machine):
        self.machinesDone += 1
        if self.machinesDone >= len(self.feedingMachines):
            self.onFinish()

    def feed(self):
        # do feeding here
        machinesDone = 0
        logger.debug("I'm going to feed " + str(self.portions) + " portions now. Here kitty kitty...")
        for machine in self.feedingMachines:
            machine.onFailure = partial(self._failureHandler, machine)
            machine.onSuccessful = partial(self.onSuccessful, machine)
            machine.onFinish = partial(self._finishHandler, machine)
            machine.runSequence(self.portions)
