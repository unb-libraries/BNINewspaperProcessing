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
(2,'FAILSIZETIF'),
(3,'PASSSIZETIF'),
(4,'FAILJPGEXIST'),
(5,'PASSJPGEXIST'),
(6,'FAILSIZEJPG'),
(7,'PASSSIZEJPG'),
(8,'GENERATEHOCR'),
(9,'FAILHOCR'),
(10,'PASSHOCR'),
(11,'GENERATEOCR'),
(12,'FAILOCR'),
(13,'PASSOCR'),
(14,'ARCHIVEBNI'),
(15,'ARCHIVELIB'),
(16,'REMOVEORIGINAL'),
(17,'COMPLETE');
