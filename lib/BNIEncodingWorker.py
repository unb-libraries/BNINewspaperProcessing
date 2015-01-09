"""BNIEncodingWorker

Core worker class for generating OCR for BNINewspaperMicroservices.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from bs4 import BeautifulSoup
import errno
import pymysql

import os
import re
import subprocess
import threading


class BNIEncodingWorker(threading.Thread):
    def __init__(self, worker_id, config, logger, tree_base_path):
        threading.Thread.__init__(self)
        self.init_config(config)
        self.logger = None
        self.cur_tif = ''
        self.cur_jpg = ''
        self.tmp_tif = ''
        self.tmp_jpg = ''
        self.tmp_filepath_stem = ''
        self.relative_tmp_filepath_stem = ''
        self.hocr_surrogate_filepath = ''
        self.tmp_file_dir = ''
        self.tree_target_dir = ''
        self.file_stem = ''
        self.db = self.init_mysql()
        self.db_cur = self.db.cursor()
        self.tree_base_path = tree_base_path
        self.worker_id = worker_id
        self.init_logger(logger)
        self.tmp_path = self.config.get('Locations', 'tmp_path')
        self.bni_output_path = self.config.get('Locations', 'bni_output_path')
        self.lib_output_path = self.config.get('Locations', 'lib_output_path')
        self.language = self.config.get('Tesseract', 'tesseract_language')
        self.tmp_root = self.config.get('Locations', 'tmp_path')

    def run(self):
        self.logger.info('Worker %s Initializing MySQL Connection.', self.worker_id)
        while True:
            self.logger.info('Worker %s does not have a task assigned. Looking for one.', self.worker_id)
            try:
                self.setup_next_image()
                self.logger.info('Worker %s set to work on %s.', self.worker_id, self.cur_tif)
                self.process_file()
            except:
                self.remove_tempfiles()
                break

    def process_file(self):
        if (self.check_tif_size() and
            self.check_jpg_exits() and
            self.check_jpg_size() and
            self.generate_hocr() and
            self.generate_ocr() and
            self.archive_files(self.bni_output_path, ['txt', 'tif']) and
            self.archive_files(self.lib_output_path, ['hocr', 'txt', 'jpg'])
        ):
            self.remove_tempfiles()
            self.remove_originals()
            self.log_worker_stage(26)

    def generate_hocr(self):
        self.logger.info('Worker %s generating HOCR for %s.', self.worker_id, self.cur_tif)
        self.hocr_surrogate_filepath = os.path.join(
            self.tmp_root,
            self.tree_target_dir,
            self.file_stem + '-grayscale.tif'
        )
        gm_call = [
            self.config.get('GraphicsMagick', 'gm_bin_path'),
            "convert",
            self.tmp_tif
        ]
        self.log_worker_stage(9)
        self.append_additional_encode_options(gm_call, 'gm_surrogate_convert_options', 'GraphicsMagick')
        gm_call.append(self.hocr_surrogate_filepath)

        if subprocess.call(gm_call) == 0:
            self.log_encode_success()
            self.logger.info('Worker %s succeeded in encoding HOCR surrogate to tesseract input file %s.',
                             self.worker_id,
                             self.hocr_surrogate_filepath)
            self.log_worker_stage(10)
        else:
            self.logger.info('Worker %s failed encoding HOCR surrogate to tesseract input file %s.',
                             self.worker_id,
                             self.hocr_surrogate_filepath)
            self.log_worker_stage(11)
            return False

        self.log_worker_stage(12)
        tesseract_call = [
            'timeout',
            self.config.get('Tesseract', 'tesseract_timeout'),
            self.config.get('Tesseract', 'tesseract_bin_path'),
            self.hocr_surrogate_filepath,
            self.tmp_filepath_stem,
            "-l", self.language,
            'hocr',
        ]

        self.log_encode_begin()
        tesseract_return = subprocess.call(tesseract_call)
        if tesseract_return is 0:
            self.log_worker_stage(15)
            return True
        elif tesseract_return is 124: # Timeout terminates with status 124
            self.log_encode_fail()
            self.log_worker_stage(13)
            return False
        self.log_encode_fail()
        self.log_worker_stage(14)
        return False

    def init_config(self, config):
        self.config = config

    def init_logger(self, logger):
        self.logger = logger
        self.logger.info('Worker %s appears!', self.worker_id)

    def archive_files(self, output_path, extensions):
        sha1_files_to_check=[]
        rsyncCall = [
            'rsync',
            '-a',
            '-L',
            '--relative',
        ]
        for cur_extension in extensions:
            rsyncCall.append('.'.join((self.relative_tmp_filepath_stem, cur_extension)))
            sha1_files_to_check.append('.'.join((self.file_stem, cur_extension)))

        rsyncCall.append(output_path + '/')
        self.log_worker_stage(19)
        if subprocess.call(rsyncCall, cwd=self.tmp_path) == 0:
            self.log_worker_stage(20)
            return self.generate_sha1(
                output_path + '/' + self.tree_target_dir,
                '.'.join((self.file_stem, 'sha1')),
                sha1_files_to_check
            )
        self.log_worker_stage(21)
        return False

    def generate_sha1(self, path, output_file, filenames):
        sha1sum_filep = open(os.path.join(path,output_file), "w")

        sha1sum_call = [
            '/usr/bin/sha1sum',
        ]

        self.log_worker_stage(22)
        sha1sum_call.extend(filenames)
        if subprocess.call(sha1sum_call, stdout=sha1sum_filep, cwd=path) == 0:
            self.log_worker_stage(23)
            self.logger.info('Worker %s succeded in calculating SHA1sum of files for %s.', self.worker_id, path)
            return True
        self.log_worker_stage(24)
        self.logger.info('Worker %s failed in calculating SHA1sum of files for %s.', self.worker_id, path)
        return False

    def generate_ocr(self):
        self.log_worker_stage(16)

        with open('.'.join((self.tmp_filepath_stem, 'hocr')), "r") as hocr_file_p:
            hocr_file_string = hocr_file_p.read().replace('\n', '')
        self.log_worker_stage(17)

        with open('.'.join((self.tmp_filepath_stem, 'txt')), 'w') as ocr_file_p:
            ocr_file_p.write(self.distill_hocr_to_ocr(hocr_file_string))
        self.log_worker_stage(18)

        return True

    def append_additional_encode_options(self, call_list, extra_options_variable, encoder_name):
        extra_options = self.config.get('HOCR', extra_options_variable)
        if not extra_options == '':
            self.logger.info('Worker %s appending extra options %s to %s for HOCR', self.worker_id, self.convert_comma_separated_options_to_list(extra_options), encoder_name)
            call_list.extend(self.convert_comma_separated_options_to_list(extra_options))

    def convert_comma_separated_options_to_list(self, options_string):
        return re.split("[ ,]+", options_string)

    def log_encode_begin(self):
        self.logger.info('Worker %s encoding %s surrogate.', self.worker_id, self.cur_tif)

    def log_encode_fail(self):
        self.logger.error('Worker %s encoding surrogate of %s has failed.', self.worker_id, self.cur_tif)

    def log_encode_success(self):
        self.logger.info('Worker %s encoding surrogate of %s has succeeded.', self.worker_id,self.cur_tif)

    def distill_hocr_to_ocr(self, hocr_string):
        ocr_string=''
        soup = BeautifulSoup(hocr_string)
        for p_item in soup.findAll('p'):
            ocr_string += ' '.join(
                ''.join(
                    p_item.findAll(text=True)
                ).encode('utf-8').split()
            ) + "\n"
        return ocr_string

    def check_tif_size(self):
        cur_min_size = int(self.config.get('MinimumSizes', 'min_size_tif'))
        cur_tif_size = os.path.getsize(self.cur_tif)
        self.logger.info('Worker %s checking TIF Size %s vs %s.', self.worker_id, cur_min_size, cur_tif_size)
        if self.check_file_size(self.cur_tif, cur_min_size):
            self.log_worker_stage(4)
            return True
        self.log_worker_stage(3)
        return False


    def check_jpg_exits(self):
        self.logger.info('Worker %s checking If JPG exists %s.', self.worker_id, self.cur_jpg)
        if os.path.isfile(self.cur_jpg):
            self.log_worker_stage(6)
            return True
        self.log_worker_stage(5)
        return False

    def check_jpg_size(self):
        cur_min_size = int(self.config.get('MinimumSizes', 'min_size_jpg'))
        cur_jpg_size = os.path.getsize(self.cur_jpg)
        self.logger.info('Worker %s checking JPG Size %s vs %s.', self.worker_id, cur_min_size, cur_jpg_size)
        if self.check_file_size(self.cur_jpg, cur_min_size):
            self.log_worker_stage(8)
            return True
        self.log_worker_stage(7)
        return False

    def check_file_size(self, file_path, minimum_size):
        if int(os.path.getsize(file_path)) > int(minimum_size):
            return True
        return False

    def remove_originals(self):
        os.unlink(self.cur_tif)
        os.unlink(self.cur_jpg)
        self.log_worker_stage(25)
        return True

    def remove_tempfiles(self):
        self.unlink_if_exists(self.tmp_tif)
        self.unlink_if_exists(self.tmp_jpg)
        self.unlink_if_exists(self.hocr_surrogate_filepath)
        self.unlink_if_exists('.'.join((self.tmp_filepath_stem, 'hocr')))
        self.unlink_if_exists('.'.join((self.tmp_filepath_stem, 'txt')))

    def unlink_if_exists(self, file_path):
        try:
            os.unlink(file_path)
        except OSError:
            pass

    def setup_next_image(self):
        # Get image from queue
        self.cur_tif = self.get_next_queue_item()
        if not self.cur_tif:
            self.logger.info('Worker %s could not find any more queue items, retiring.', self.worker_id)
            raise Exception("No queue items left!")

        self.cur_tif = os.path.join(
            self.tree_base_path,
            self.cur_tif.replace(os.path.basename(self.cur_tif), 'Tiffs/' + os.path.basename(self.cur_tif))
        )
        self.file_stem = os.path.basename(
            self.cur_tif[0:self.cur_tif.rindex('.')]
        )
        self.cur_jpg = os.path.normpath(
            os.path.dirname(self.cur_tif) + '/' +
            self.config.get('Locations', 'relative_location_jpg') +
            '.'.join((self.file_stem, 'jpg'))
        )

        # Determine where the file SHOULD live in the tree
        self.tree_target_dir = os.path.normpath(
            os.path.dirname(self.cur_tif) + '/../'
        ).replace(
            self.tree_base_path + '/', ''
        )

        # Copy TIF to tmp directory, creating folders as we go.
        self.init_tmp_path()

        # Set Tmp FilePathStem
        self.tmp_filepath_stem = os.path.join(self.tmp_file_dir, self.file_stem)

        # Set the relative TmpFilePathStem
        self.relative_tmp_filepath_stem = '/'.join((self.tree_target_dir, self.file_stem))

    def log_worker_stage(self, status_id, file_path=''):
        if status_id is 2:
            self.db_cur.execute("UPDATE images SET status_id=" + str(status_id) + ", start_datestamp=NOW(), latest_datestamp=NOW() WHERE filepath='" + file_path + "'")
            self.db.commit()
        else:
            tree_filepath = self.tree_target_dir + '/' + self.file_stem + ".tif"
            self.db_cur.execute("UPDATE images SET status_id=" + str(status_id) + ", latest_datestamp=NOW() WHERE filepath='" + tree_filepath + "'")
            self.db.commit()
        return True

    def init_mysql(self):
        return pymysql.connect(
            host=self.config.get('MySQL', 'mysql_host'),
            user=self.config.get('MySQL', 'mysql_user'),
            passwd=self.config.get('MySQL', 'mysql_pw'),
            db=self.config.get('MySQL', 'mysql_db'),
            charset="utf8"
        )

    def init_tmp_path(self):
        self.tmp_file_dir = os.path.join(
            self.tmp_root,
            self.tree_target_dir
        )
        self.mkdir_p(self.tmp_file_dir)
        self.tmp_tif = os.path.join(
            self.tmp_root,
            self.tree_target_dir,
            self.file_stem + '.tif'
        )
        self.unlink_if_exists(self.tmp_tif)
        os.symlink(
            self.cur_tif,
            self.tmp_tif
        )
        self.tmp_jpg = os.path.join(
            self.tmp_root,
            self.tree_target_dir,
            self.file_stem + '.jpg'
        )
        self.unlink_if_exists(self.tmp_jpg)
        os.symlink(
            self.cur_jpg,
            self.tmp_jpg
        )

    def mkdir_p(self, path):
        try:
            os.makedirs(path)
        except OSError as exc: # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    def get_next_queue_item(self):
        self.db_cur.execute("SELECT filepath FROM images where status_id=1 ORDER BY id ASC LIMIT 1")
        row = self.db_cur.fetchone()
        if row is None:
            return False
        self.log_worker_stage(2, row[0])
        return row[0]
