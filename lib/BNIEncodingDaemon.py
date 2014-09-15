"""BNIEncodingDemon

Core demon class for spawning workers for BNINewspaperProcessing.
"""

import ConfigParser
import logging
from lib.simpleDaemon import Daemon
from lib.BNIEncodingWorker import BNIEncodingWorker
import MySQLdb
import os
import platform
import threading
import time
import socket
import subprocess


class BNIEncodingDaemon(Daemon):
    def __init__(self, pid_filepath, stdin_super='/dev/null', stdout_super='/dev/null', stderr_super='/dev/null', config_file=''):
        super(BNIEncodingDaemon, self).__init__(pid_filepath, stdin_super, stdout_super, stderr_super)
        self.init_config(config_file)
        self.db = None
        self.db_cur = None
        self.init_logger()
        self.queue = set()
        self.mysql_config_id = None
        self.max_workers = self.config.getint('Threading', 'number_workers')
        self.sleep_time = self.config.getint('Threading', 'sleep_time')
        self.input_path = self.config.get('Locations', 'input_path')
        self.log_daemon_config()

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
                        self.input_path,
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

        self.db = self.init_mysql()
        self.db_cur = self.db.cursor()

        for root, subFolders, files in os.walk(self.input_path):
            files = [fi for fi in files if fi.endswith(".tif")]
            if len(files) > 0:
                for cur_file in files:
                    if not self.file_already_queued(os.path.join(root, cur_file)):
                        self.queue.update([os.path.join(root, cur_file)])

        self.db_cur.close()
        self.db.close()

        if len(files) > 0:
            self.log_queue_insert(self.queue)

    def init_mysql(self):
        return MySQLdb.connect(
            host=self.config.get('MySQL', 'mysql_host'),
            user=self.config.get('MySQL', 'mysql_user'),
            passwd=self.config.get('MySQL', 'mysql_pw'),
            db=self.config.get('MySQL', 'mysql_db'),
            charset="utf8"
        )

    def log_queue_insert(self, files, status_id=1):
        self.db = self.init_mysql()
        self.db_cur = self.db.cursor()
        insert_queue_string = "INSERT INTO images (config_id, filepath, status_id, queue_datestamp, latest_datestamp) VALUES"

        for cur_file in files:
            file_stem = os.path.basename(cur_file)
            cur_typeless_path = os.path.normpath(os.path.dirname(cur_file) + '/../')
            cur_typeless_file = cur_typeless_path + '/' + file_stem
            cur_typeless_relative = cur_typeless_file.replace(self.input_path + '/', '')
            insert_queue_string += " (" + str(self.mysql_config_id) + "," + "'" + cur_typeless_relative + "'," + str(status_id) + "," + "NOW()," + "NOW()),"

        self.db_cur.execute(insert_queue_string.rstrip(","))
        self.db.commit()

        self.db_cur.close()
        self.db.close()

    def log_daemon_config(self):
        self.db = self.init_mysql()
        self.db_cur = self.db.cursor()
        os_lsb_data = platform.linux_distribution()
        self.db_cur.execute("INSERT INTO configuration " +
                        "(hostname, os_id, os_release, num_workers, sleep_time, gm_version, tesseract_version, tesseract_language, gm_surrogate_convert_options)" +
                        " VALUES " +
                        "(" +
                        "'" + self.get_hostname() + "'," +
                        "'" + os_lsb_data[0] + "'," +
                        "'" + os_lsb_data[1] + "'," +
                        self.config.get('Threading', 'number_workers') + "," +
                        self.config.get('Threading', 'sleep_time') + "," +
                        "'" + self.get_gm_version() + "'," +
                        "'" + self.get_tesseract_version() + "'," +
                        "'" + self.config.get('Tesseract', 'tesseract_language') + "'," +
                        "'" + self.config.get('HOCR', 'gm_surrogate_convert_options') + "')"
        )
        self.db.commit()
        self.mysql_config_id = self.db_cur.lastrowid
        self.db_cur.close()
        self.db.close()
        return True

    def file_already_queued(self, filepath):
        file_stem = os.path.basename(filepath)
        cur_typeless_path = os.path.normpath(os.path.dirname(filepath) + '/../')
        cur_typeless_file = cur_typeless_path + '/' + file_stem
        cur_typeless_relative = cur_typeless_file.replace(self.input_path + '/', '')
        check_queued_query = "SELECT COUNT(1) FROM images WHERE filepath = '" + cur_typeless_relative + "'"

        self.db_cur.execute(check_queued_query)
        if self.db_cur.fetchone()[0]:
            return True
        return False

    def get_hostname(self):
        return socket.getfqdn()

    def get_gm_version(self):
        return os.popen('GraphicsMagick-config --version').read().strip()

    def get_tesseract_version(self):
        sub_p = subprocess.Popen([self.config.get('Tesseract', 'tesseract_bin_path'),'--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (tesseract_stdout, tesseract_stderr) = sub_p.communicate()
        return tesseract_stderr.strip().replace("\n", ' ')