CREATE TABLE configuration (
  config_id MEDIUMINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  hostname VARCHAR(128),
  os_id VARCHAR(64),
  os_release VARCHAR(64),
  num_workers TINYINT UNSIGNED,
  sleep_time SMALLINT UNSIGNED,
  gm_version VARCHAR(64),
  tesseract_version VARCHAR(128),
  tesseract_language VARCHAR(32),
  gm_surrogate_convert_options VARCHAR(256)
);

CREATE TABLE images (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  config_id MEDIUMINT UNSIGNED,
  filepath VARCHAR(512),
  status_id TINYINT UNSIGNED,
  queue_datestamp DATETIME,
  start_datestamp DATETIME,
  latest_datestamp DATETIME
) ENGINE = MYISAM;
ALTER TABLE images ADD INDEX (filepath);
ALTER TABLE images ADD INDEX (status_id);
ALTER TABLE images ADD INDEX (id,status_id);

CREATE TABLE status (
  status_id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
  status_string VARCHAR(16)
);

INSERT INTO status (status_id,status_string) VALUES
(1,'QUEUED'),
(2,'INPROGRESS'),
(3,'FAILSIZETIF'),
(4,'PASSSIZETIF'),
(5,'FAILJPGEXIST'),
(6,'PASSJPGEXIST'),
(7,'FAILSIZEJPG'),
(8,'PASSSIZEJPG'),
(9,'GENERATEHOCR'),
(10,'TIMEOUTOCR'),
(11,'FAILHOCR'),
(12,'PASSHOCR'),
(13,'GENERATEOCR'),
(14,'FAILOCR'),
(15,'PASSOCR'),
(16,'ARCHIVEFILES'),
(17,'ARCHIVEOK'),
(18,'ARCHIVEFAIL'),
(19,'GENERATESHA1SUM'),
(20,'PASSSHA1SUM'),
(21,'FAILSHA1SUM'),
(22,'REMOVEORIGINAL'),
(23,'COMPLETE');
