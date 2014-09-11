"""BNIEncodingWorker

Core worker class for generating OCR for BNINewspaperMicroservices.
"""

from bs4 import BeautifulSoup
import os
import re
import subprocess
import threading


class BNIEncodingWorker(threading.Thread):
    def __init__(self, worker_id, config, logger, queue):
        threading.Thread.__init__(self)
        self.cur_file = ''
        self.basename = ''
        self.worker_id = worker_id
        self.init_config(config)
        self.init_logger(logger)
        self.tmp_path = self.config.get('Locations', 'tmp_path')
        self.bni_output_path = self.config.get('Locations', 'bni_output_path')
        self.lib_output_path = self.config.get('Locations', 'lib_output_path')
        self.language = self.config.get('Tesseract', 'tesseract_language')
        self.queue = queue

    def run(self):
        while True:
            self.logger.info('Worker %s does not have a task assigned. Looking for one.', self.worker_id)
            self.logger.info('Worker %s reports queue length is currently %s.', self.worker_id, len(self.queue))
            try:
                self.cur_file = self.queue.pop()
                self.process_file()
            except:
                break

    def process_file(self):
        if (self.generate_basename() and
            self.generate_hocr() and
            self.generate_ocr() and
            self.generate_sha1()
        ):
            self.mv_tiff_out()
            self.cp_jpg_out()
            self.send_jpg_glacier()

    def generate_hocr(self):
        self.logger.info('Worker %s generating OCR for %s.', self.worker_id, self.cur_file)
        surrogate_output_filepath = '.'.join( (self.basename, 'tiff'))

        gm_call = [
                  self.config.get('GraphicsMagick', 'gm_bin_path'),
                  "convert",
                  self.cur_file
                  ]
        self.append_additional_encode_options(gm_call, 'gm_surrogate_convert_options', 'GraphicsMagick')
        gm_call.append(surrogate_output_filepath)
        if subprocess.call(gm_call) == 0:
            self.log_encode_success()
            self.logger.info('Worker %s succeded in encoding HOCR surrogate to tesseract input file %s.', self.worker_id, surrogate_output_filepath)
        else:
            self.logger.info('Worker %s failed encoding HOCR surrogate to tesseract input file %s.', self.worker_id, surrogate_output_filepath)
            return False
        tesseractCall = [
            self.config.get('Tesseract', 'tesseract_bin_path'),
            surrogate_output_filepath,
            self.basename,
            "-l", self.language,
            'hocr',
        ]
        self.log_encode_begin()
        if subprocess.call(tesseractCall) == 0:
            os.remove(surrogate_output_filepath)
            return True
        os.remove(surrogate_output_filepath)
        self.log_encode_fail()
        return False

    def init_config(self, config):
        self.config = config

    def init_logger(self, logger):
        self.logger = logger
        self.logger.info('Worker %s appears!', self.worker_id)

    def copy_tif_out(self):
        pass

    def copy_jpg_out(self):
        pass

    def generate_sha1(self):
        sha1sum_filename = '.'.join((self.basename, 'sha1'))
        sha1sum_filep = open(sha1sum_filename, "w")
        sha1sum_call = [
            '/usr/bin/sha1sum',
            os.path.basename(self.cur_file),
            '.'.join((os.path.basename(self.basename), 'jpg')),
            '.'.join((os.path.basename(self.basename), 'hocr')),
        ]
        if subprocess.call(sha1sum_call, stdout=sha1sum_filep, cwd=os.path.dirname(self.cur_file)) == 0:
            self.logger.info('Worker %s succeded in calculating SHA1sum of original file %s.', self.worker_id, sha1sum_filename)
            return True
        self.logger.info('Worker %s failed in calculating SHA1sum of original file %s.', self.worker_id, sha1sum_filename)
        return False

    def generate_ocr(self):
        with open('.'.join((self.basename, 'hocr')), "r") as hocr_file_p:
            hocr_file_string=hocr_file_p.read().replace('\n', '')
        ocr_file_p = open('.'.join((self.basename, 'txt')), "w")
        soup = BeautifulSoup(hocr_file_string)
        for p_item in soup.findAll(['p']):
            ocr_file_p.write(p_item.getText() + "\n")
        ocr_file_p.close()
        return True

    def generate_basename(self):
        self.basename = self.cur_file[0:self.cur_file.rindex('.')]
        return True

    def append_additional_encode_options(self, call_list, extra_options_variable, encoder_name):
        extra_options = self.config.get('HOCR', extra_options_variable)
        if not extra_options == '':
            self.logger.info('Worker %s appending extra options %s to %s for HOCR', self.worker_id, self.convert_comma_separated_options_to_list(extra_options), encoder_name)
            call_list.extend(self.convert_comma_separated_options_to_list(extra_options))

    def convert_comma_separated_options_to_list(self, options_string):
        return re.split("[ ,]+", options_string)

    def log_encode_begin(self):
        self.logger.info('Worker %s encoding %s surrogate.', self.worker_id, self.cur_file)

    def log_encode_fail(self):
        self.logger.error('Worker %s encoding surrogate of %s has failed.', self.worker_id, self.cur_file)

    def log_encode_success(self):
        self.logger.info('Worker %s encoding surrogate of %s has succeeded.', self.worker_id,self.cur_file)
