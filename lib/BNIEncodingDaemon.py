"""BNIEncodingDemon

Core demon class for spawning workers for BNINewspaperProcessing.
"""

import ConfigParser
import logging
from lib.simpleDaemon import Daemon
from lib.BNIEncodingWorker import BNIEncodingWorker
import threading
import time
import os


class BNIEncodingDaemon(Daemon):
    def __init__(self, config_file, pid_filepath, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        super(BNIEncodingDaemon, self).__init__(pid_filepath, stdin, stdout, stderr)
        self.init_config(config_file)
        self.init_logger()
        self.queue = set()
        self.max_workers = self.config.getint('Threading', 'number_workers')
        self.sleep_time = self.config.getint('Threading', 'sleep_time')
        self.input_path = self.config.get('Locations', 'input_path')

    def run(self):
        while True:
            self.logger.info('Updating Queue.')
            self.update_queue()
            self.logger.info('Daemon looking for jobs for workers.')
            for worker_id in range(self.max_workers):
                queue_length = len(self.queue)
                self.logger.info('Daemon reports queue length is currently %s.', queue_length)
                if not queue_length is 0:
                    self.logger.info('Daemon found job(s) - deploying to worker %s.', worker_id)
                    worker = BNIEncodingWorker(
                        worker_id,
                        self.config,
                        self.logger,
                        self.queue,
                    )
                    worker.start()
                    # Sleep on initial worker spin-up to let previous worker get job from queue and stagger queue
                    # grabs. It currently is 'safe' but throw exceptions if two workers try to grab at the same time.
                    # Making it 100% thread safe with blocking is a whole thing, so we do this.
                    time.sleep(3)
            for thread in threading.enumerate():
                if thread is not threading.currentThread():
                    thread.join()
            self.logger.info('All workers retired, daemon sleeping for %s seconds.', self.sleep_time)
            time.sleep(self.sleep_time)

    def init_config(self, config_filepath):
        self.config = ConfigParser.SafeConfigParser()
        self.config.read(config_filepath)

    def init_logger(self):
        self.logger = logging.getLogger('bni_encoding')
        self.hdlr = logging.FileHandler(self.config.get('Logging', 'log_file'))
        log_level_value = getattr(
            logging,
            self.config.get('Logging', 'log_level')
        )
        self.logger.setLevel(log_level_value)
        self.hdlr.setLevel(log_level_value)
        self.formatter = logging.Formatter(self.config.get('Logging', 'log_format'))
        self.hdlr.setFormatter(self.formatter)
        self.logger.addHandler(self.hdlr)

    def update_queue(self):
        self.logger.info('Daemon looking for jobs for workers.')
        for root, subFolders, files in os.walk(self.input_path):
            files = [fi for fi in files if fi.endswith(".tif")]
            for cur_file in files:
                self.queue.update([os.path.join(root, cur_file)])
