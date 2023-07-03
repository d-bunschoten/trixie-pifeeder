import sys
import os
import logging
from logging.handlers import TimedRotatingFileHandler

def initLogger(logger):
    LOG_DIR = "/var/log/voerautomaat/"
    os.makedirs(LOG_DIR, exist_ok=True)  # Creates the directory if it doesn't exist

    ALL_LOG_FILE = os.path.join(LOG_DIR, "voerautomaat.log")
    ERROR_LOG_FILE = os.path.join(LOG_DIR, "error.log")

    formatter = logging.Formatter('%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d|PID:%(process)d] %(message)s', datefmt='%d-%m-%Y %H:%M:%S')

    console_handler = logging.StreamHandler(sys.stdout)  # sys.stdout sends output to the console
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    # Set up the handler for all logs
    handler_all = TimedRotatingFileHandler(
        ALL_LOG_FILE,
        when="w0",
        interval=1,
        backupCount=5
    )
    handler_all.setFormatter(formatter)
    handler_all.setLevel(logging.DEBUG)  # Set level to DEBUG to capture all logs
    logger.addHandler(handler_all)

    # Set up the handler for error logs
    handler_error = TimedRotatingFileHandler(
        ERROR_LOG_FILE,
        when="w0",
        interval=1,
        backupCount=5
    )
    handler_error.setFormatter(formatter)
    handler_error.setLevel(logging.ERROR)  # Set level to ERROR to capture only error logs
    logger.addHandler(handler_error)

    # Set the overall logger level to DEBUG
    logger.setLevel(logging.DEBUG)