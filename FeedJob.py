import time, logging
from functools import partial

class FeedJob:
    portions = 0
    feedingMachines = []

    machinesDone = 0

    onError = None
    onFinish = None

    def __init__(self, portions, feedingMachines):
        self.portions = portions
        self.feedingMachines = feedingMachines
        def doNothing():
            return
        self.onError = doNothing
        self.onFinish = doNothing

    def _failureHandler(self, machine, error):
        currentRound = (self.portions - error.roundsLeft) + 1
        logging.error('Machine '+machine.name+' failed on portion #'+str(currentRound)+': '+error.message)
        self.onError(machine, error)
        # possibly send Notification here

    def _finishHandler(self, machine):
        self.machinesDone += 1
        if self.machinesDone >= len(self.feedingMachines):
            self.onFinish()

    def feed(self):
        # do feeding here
        machinesDone = 0
        logging.debug("I'm going to feed " + str(self.portions) + " portions now. Here kitty kitty...")
        for machine in self.feedingMachines:
            machine.onFailure = partial(self._failureHandler, machine)
            machine.onFinish = partial(self._finishHandler, machine)
            machine.runSequence(self.portions)
