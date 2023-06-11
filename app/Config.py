import json
from os.path import abspath, dirname

class Config:
    file = ""
    schedule = []
    loglevel = "ERROR"
    feedingMachines = []
    manualFeedingButtonPort = None
    statusLedPort = None
    mqtt = {}
    device = {}

    def __init__(self, file = None):
        if(file is None):
            file = dirname(abspath(__file__)) + "/config.json"
        self.file = file
        self.readConfig()

    def readConfig(self):
        f = open(self.file, "r")
        data = json.loads(f.read())
        self.schedule = data["schedule"]
        self.loglevel = data["loglevel"]
        self.feedingMachines = data["feedingMachines"]
        self.manualFeedingButtonPort = data["manualFeedingButtonPort"]
        self.statusLedPort = data["statusLedPort"]
        self.mqtt = data["mqtt"]
        self.device = data["device"]
        f.close() 
