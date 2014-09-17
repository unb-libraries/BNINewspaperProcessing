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
(9,'GENERATESURROG'),
(10,'PASSSURROGATE'),
(11,'FAILSURROGATE'),
(12,'GENERATEHOCR'),
(13,'TIMEOUTHOCR'),
(14,'FAILHOCR'),
(15,'PASSHOCR'),
(16,'GENERATEOCR'),
(17,'FAILOCR'),
(18,'PASSOCR'),
(19,'ARCHIVEFILES'),
(20,'ARCHIVEOK'),
(21,'ARCHIVEFAIL'),
(22,'GENERATESHA1SUM'),
(23,'PASSSHA1SUM'),
(24,'FAILSHA1SUM'),
(25,'REMOVEORIGINAL'),
(26,'COMPLETE');
