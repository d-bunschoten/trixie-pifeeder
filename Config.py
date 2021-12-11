import json

class Config:
    file = ""
    schedule = []
    loglevel = "ERROR"
    notify = ""
    email = ""
    feedingMachines = []
    manualFeedingButtonPort = None
    statusLedPort = None

    def __init__(self, file = None):
        if(file is None):
            file = "/home/pi/voerautomaat/config.json"
        self.file = file
        self.readConfig()

    def readConfig(self):
        f = open(self.file, "r")
        data = json.loads(f.read())
        self.schedule = data["schedule"]
        self.loglevel = data["loglevel"]
        self.notify = data["notify"]
        self.email = data["email"]
        self.feedingMachines = data["feedingMachines"]
        self.manualFeedingButtonPort = data["manualFeedingButtonPort"]
        self.statusLedPort = data["statusLedPort"]
        f.close()
