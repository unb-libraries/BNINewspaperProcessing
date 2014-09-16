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
  latest_datestamp DATETIME,
  UNIQUE (filepath)
);

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
(10,'FAILHOCR'),
(11,'PASSHOCR'),
(12,'GENERATEOCR'),
(13,'FAILOCR'),
(14,'PASSOCR'),
(15,'ARCHIVEBNI'),
(16,'ARCHIVELIB'),
(17,'REMOVEORIGINAL'),
(18,'COMPLETE');
