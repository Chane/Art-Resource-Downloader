import logging
import sys
import argparse
import requests

from config import LASTFM_APPLICATON_NAME

class MyClass:
    def __init__(self):
        parser = argparse.ArgumentParser();
        parser.add_argument(
            '-d', '--debug',
            help = "Log debug information",
            action = "store_const", dest = "loglevel", const = logging.DEBUG,
            default = logging.WARNING
        )

        parser.add_argument(
            '-v', '--verbose',
            help = "Log verbose information",
            action = "store_const", dest = "loglevel", const = logging.INFO
        )

        args = parser.parse_args();

        logging.basicConfig(stream = sys.stdout, level = args.loglevel)
        self.logger = logging.getLogger(__name__)

    def writeMessage(self, message):
        self.logger.log(logging.INFO, message)

    def writeDebug(self, message):
        self.logger.log(logging.DEBUG, message)


    def run(self):
        self.writeMessage(LASTFM_APPLICATON_NAME)
        response = requests.get("https://api.open-notify.org/this-api-doesnt-exist")
        print(response.status_code)