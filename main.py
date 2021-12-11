#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import logging
from logging.handlers import TimedRotatingFileHandler
from CatFeeder import CatFeeder

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%d-%m-%Y:%H:%M:%S',
    level=logging.DEBUG
)

handler = TimedRotatingFileHandler(
    "voerautomaat.log",
    when="m",
    interval=1,
    backupCount=5
)
logger.addHandler(handler)


#----------------------------------------------------------------------------------------------------
# the main section
if __name__ == "__main__":
    daemon = CatFeeder()
    usageMessage = f"Usage: {sys.argv[0]} (start|stop|restart|status|reload|version|feed|nodaemon)"
    if len(sys.argv) == 2:
        choice = sys.argv[1]
        if choice == "start":
            daemon.start()
        elif choice == "stop":
            daemon.stop()
        elif choice == "restart":
            daemon.restart()
        elif choice == "status":
            daemon.status()
        elif choice == "reload":
            daemon.reload()
        elif choice == "version":
            daemon.version()
        elif choice == "feed":
            daemon.user1Signal()
        elif choice == "nodaemon":
            daemon.setDaemon(False)
            daemon.install()
            daemon.run()
        else:
            print("Unknown command.")
            print(usageMessage)
            sys.exit(1)
        sys.exit(0)
    else:
        print(usageMessage)
        sys.exit(1)
