#!/usr/bin/python3

import logging
import logging.config
import logging.handlers
import json
from queue import Queue
import sys

#this library assumes that the main logger name is root. please see setup_logging() down in the class
#fuck json format for configuring the logger, DO IT FROM THE CODE...

configFilePath = './logging_conf.json'

class Logger:
    #this class won't set attrs on the class, unless you call the method setup(loggerName)

    def __init__(self, appName:str=None, configFilePath:str = None, debug:bool=False, verbosity:int=0):
        
        self.appName = appName
        self.jsonFile = configFilePath
        self.debug = debug
        self.verbosity = verbosity

        #if theres no config file, use default config
        if self.jsonFile == None: self.start()

    def __str__(self):
        string = ''
        for key, value in vars(self).items():
            string += f'{key}: {value}\n'

        return string

    def loadJsonFile(self) -> dict:
        if self.debug: print('loading and creating reference to config dict')
        with open(self.jsonFile) as f:
            config = json.load(f)
            setattr(self, 'config', conf)

    def loadConfig(self):
        logging.config.dictConfig(self.config)

    def setupRootLogger(self, handlers:list):
        if self.debug: print('creating and configuring root logger')
        root = logging.getLogger()
        for h in handlers:
            root.addHandler(h)
        setattr(self, 'root', root)

    def setupAppLogger(self, loggerName:str, level:int=10):
        if self.debug: print('creating and configuring app logger')
        logger = logging.getLogger(loggerName)
        logger.setLevel(level)
        logger.propagate = True

        setattr(self, loggerName, logger)

    def getHandlers(self) -> list:
        return self.handlers

    def addCustomLevel(self, level:int, levelName:str):
        if self.debug: print('creating new logging level: %s' % levelName)
        logging.addLevelName(level, levelName)

    def setupFormatters(self):
        if self.debug: print('creating formatter references')
        simpleFormatter = logging.Formatter("%(levelname)s: %(message)s")
        detailedFormatter = logging.Formatter("[%(levelname)s|%(module)s|%(funcName)s|%(lineno)d|] %(asctime)s: %(message)s", "%Y-%m-%dT%H:%M:%S%z")

        setattr(self, 'simpleFormatter', simpleFormatter)
        setattr(self, 'detailedFormatter', detailedFormatter)

    def newFilter(self, level:int):
        
        class CustomFilter(logging.Filter):
            def __init__(self):
                super().__init__()

            def filter(self, record):
                return record.levelno == level

        return CustomFilter()

    def setupStreamHandlers(self):
        handlers = []

        if self.debug: print('creating and configuring stream handlers')

        if self.verbosity >= 1:
            stdout = logging.StreamHandler(sys.stdout)
            stdout.setLevel(logging.INFO)
            stdout.setFormatter(self.simpleFormatter)
            stdout.addFilter(self.newFilter(20))
            handlers.append(stdout)

        if self.verbosity >= 2:
            stderr = logging.StreamHandler(sys.stderr)
            stderr.setLevel(logging.WARNING)
            stderr.setFormatter(self.simpleFormatter)
            handlers.append(stderr)

        file = logging.handlers.RotatingFileHandler('./logs/cubanman.log','a', 2000000, 3, None, False, None)
        file.setLevel(logging.DEBUG)
        file.setFormatter(self.detailedFormatter)
        handlers.append(file)

        setattr(self, 'handlers', handlers)

    def setupQueueHandler(self):
        if self.debug: print('creating queue handler and setting reference up')
        queueHandler = logging.handlers.QueueHandler(Queue(-1))
        setattr(self, 'queueHandler', queueHandler)

    def setupQueueListener(self):
        if self.debug: print('creating queue listener and setting reference up')
        listener = logging.handlers.QueueListener(self.queueHandler.queue, *self.handlers, respect_handler_level=True)
        setattr(self, 'listener', listener)

    def stopListener(self):
        if self.debug: print('stopping queue listener')
        self.listener.stop()

    def start(self):
        if self.debug: print('starting logging system')
        self.setupFormatters()
        self.setupStreamHandlers()
        self.setupQueueHandler()
        self.setupQueueListener()
        self.setupRootLogger([self.queueHandler])
        self.setupAppLogger(self.appName)
        self.listener.start()


def main():
    #test
    pass
    '''
    myLogger = Logger(appName='cubanman', debug=False, verbosity=2)

    myLogger.cubanman.info('this is an info message')
    myLogger.cubanman.warning('this is a warning message')
    myLogger.cubanman.debug('this is a debug message')
    myLogger.stopListener()
    print('exiting ...')
    '''

if __name__ == '__main__':
    main()
