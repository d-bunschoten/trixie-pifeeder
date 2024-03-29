#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import logging
from logger import initLogger

logger = logging.getLogger()
initLogger(logger)

from CatFeeder import CatFeeder

#----------------------------------------------------------------------------------------------------
# the main section
if __name__ == "__main__":
    daemon = CatFeeder()
    usageMessage = f"Usage: {sys.argv[0]} (start|stop|restart|status|reload|version|feed|verbose)"
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
        elif choice == "verbose":
            daemon.verbose()
        else:
            print("Unknown command.")
            print(usageMessage)
            sys.exit(1)
        sys.exit(0)
    else:
        print(usageMessage)
        sys.exit(1)