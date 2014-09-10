"""BNIEncodingWorker

Core worker class for generating OCR for BNINewspaperMicroservices.
"""

import threading
import subprocess

class BNIEncodingWorker(threading.Thread):
    def __init__(self, worker_id, config, logger, queue):
        self.worker_id = worker_id
        self.init_config(config)
        self.init_logger(logger)
        self.tmp_path = self.config.get('Locations', 'tmp_path')
        self.bni_output_path = self.config.get('Locations', 'bni_output_path')
        self.lib_output_path = self.config.get('Locations', 'lib_output_path')
        self.queue = queue

    def run(self):
        while True:
            self.logger.info('Worker %s does not have a task assigned. Looking for one.', self.worker_id)
            self.logger.info('Worker %s reports queue length is currently %s.', self.worker_id, len(self.queue))
            try:
                self.process_file(self.queue.pop())
            except:
                break

    def process_file(self, file_to_process):
        self.generate_sha1()
        self.generate_ocr()
        self.copy_tif_out()
        self.copy_jpg_out()

    def generate_ocr(self, filename):
        output_base_name = self.temp_filepath[0:self.temp_filepath.rindex('.')]
        output_filename = '.'.join((output_base_name, self.file_extension))
        surrogate_output_filepath = '.'.join( (output_base_name, 'tif'))

        gm_call = [
                  self.config.get('GraphicsMagick', 'gm_bin_path'),
                  "convert",
                  self.temp_filepath
                  ]
        self.append_additional_encode_options(gm_call, 'gm_surrogate_convert_options', 'GraphicsMagick')
        gm_call.append(surrogate_output_filepath)
        if subprocess.call(gm_call) == 0:
            self.log_encode_success()
            self.logger.info('Worker %s succeded in encoding %s %s surrogate to tesseract input file %s.', self.worker_id, self.pid, self.dsid, surrogate_output_filepath)
        else:
            self.logger.info('Worker %s failed encoding %s %s surrogate to tesseract input file %s.', self.worker_id, self.pid, self.dsid, surrogate_output_filepath)
            return False

        tesseractCall = [
                      self.config.get('Tesseract', 'tesseract_bin_path'),
                      surrogate_output_filepath,
                      output_base_name,
                      "-l", self.language
                      ]
        if self.use_hocr: tesseractCall.append('hocr')
        self.log_encode_begin(output_filename)
        if subprocess.call(tesseractCall) == 0:
            self.converted_file_path = output_filename
            self.log_encode_success()
            return True
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
        pass
