-- CHỈ CHẠY MỘT LẦN trên cơ sở dữ liệu mới. Không chạy lại khi đã có bảng.
CREATE DATABASE IF NOT EXISTS phong_kham CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE phong_kham;

CREATE TABLE doctors (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(20) NOT NULL UNIQUE,
  identity_no VARCHAR(20) NOT NULL UNIQUE,
  full_name VARCHAR(120) NOT NULL,
  birth_date DATE NOT NULL,
  address VARCHAR(255) NOT NULL,
  grade VARCHAR(50) NOT NULL,
  years_experience SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  education VARCHAR(120) NOT NULL,
  specialty VARCHAR(120) NOT NULL
);
CREATE TABLE nurses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  employee_code VARCHAR(20) NOT NULL UNIQUE,
  identity_no VARCHAR(20) NOT NULL UNIQUE,
  full_name VARCHAR(120) NOT NULL,
  qualification VARCHAR(120) NOT NULL,
  years_experience SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  birth_date DATE NOT NULL,
  address VARCHAR(255) NOT NULL,
  phone VARCHAR(20) NOT NULL
);
CREATE TABLE patients (
  id INT AUTO_INCREMENT PRIMARY KEY,
  patient_code VARCHAR(20) NOT NULL UNIQUE,
  identity_no VARCHAR(20) NOT NULL UNIQUE,
  full_name VARCHAR(120) NOT NULL,
  birth_date DATE NOT NULL,
  address VARCHAR(255) NOT NULL,
  phone VARCHAR(20) NOT NULL
);
CREATE TABLE diseases (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE
);
CREATE TABLE drugs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  unit VARCHAR(30) NOT NULL,
  current_price DECIMAL(12,2) NOT NULL,
  CONSTRAINT ck_drug_price CHECK (current_price >= 0)
);
-- Một đợt = một lần mắc bệnh. Tái mắc tạo đợt mới, dù cùng bệnh nhân và bệnh.
CREATE TABLE episodes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  patient_id INT NOT NULL,
  disease_id INT NOT NULL,
  doctor_id INT NOT NULL,
  started_on DATE NOT NULL,
  cured_on DATE NULL,
  status ENUM('dang_dieu_tri','da_khoi') NOT NULL DEFAULT 'dang_dieu_tri',
  CONSTRAINT fk_episode_patient FOREIGN KEY (patient_id) REFERENCES patients(id),
  CONSTRAINT fk_episode_disease FOREIGN KEY (disease_id) REFERENCES diseases(id),
  CONSTRAINT fk_episode_doctor FOREIGN KEY (doctor_id) REFERENCES doctors(id),
  CONSTRAINT ck_episode_dates CHECK (cured_on IS NULL OR cured_on >= started_on),
  CONSTRAINT ck_episode_status CHECK ((status='dang_dieu_tri' AND cured_on IS NULL) OR (status='da_khoi' AND cured_on IS NOT NULL)),
  INDEX ix_episode_cured (cured_on),
  INDEX ix_episode_patient (patient_id, status)
);
CREATE TABLE visits (
  id INT AUTO_INCREMENT PRIMARY KEY,
  episode_id INT NOT NULL,
  visit_no SMALLINT UNSIGNED NOT NULL,
  admitted_on DATE NOT NULL,
  discharged_on DATE NULL,
  consultation_fee DECIMAL(12,2) NOT NULL DEFAULT 0,
  notes VARCHAR(255) NULL,
  CONSTRAINT fk_visit_episode FOREIGN KEY (episode_id) REFERENCES episodes(id),
  CONSTRAINT uq_visit_no UNIQUE (episode_id, visit_no),
  CONSTRAINT ck_visit_dates CHECK (discharged_on IS NULL OR discharged_on >= admitted_on),
  CONSTRAINT ck_visit_fee CHECK (consultation_fee >= 0),
  INDEX ix_visit_date (admitted_on)
);
CREATE TABLE visit_nurses (
  visit_id INT NOT NULL,
  nurse_id INT NOT NULL,
  action_type ENUM('tiep_don','cap_thuoc','tiem_thuoc','cham_soc') NOT NULL,
  PRIMARY KEY (visit_id, nurse_id),
  FOREIGN KEY (visit_id) REFERENCES visits(id),
  FOREIGN KEY (nurse_id) REFERENCES nurses(id)
);
CREATE TABLE prescriptions (
  visit_id INT NOT NULL,
  drug_id INT NOT NULL,
  quantity INT UNSIGNED NOT NULL,
  unit_price DECIMAL(12,2) NOT NULL,
  PRIMARY KEY (visit_id, drug_id),
  FOREIGN KEY (visit_id) REFERENCES visits(id),
  FOREIGN KEY (drug_id) REFERENCES drugs(id),
  CONSTRAINT ck_rx_quantity CHECK (quantity > 0),
  CONSTRAINT ck_rx_price CHECK (unit_price >= 0)
);
CREATE TABLE salary_config (
  id TINYINT PRIMARY KEY,
  doctor_base DECIMAL(12,2) NOT NULL DEFAULT 7000000,
  nurse_base DECIMAL(12,2) NOT NULL DEFAULT 5000000,
  doctor_bonus DECIMAL(12,2) NOT NULL DEFAULT 1000000,
  nurse_bonus DECIMAL(12,2) NOT NULL DEFAULT 200000,
  CONSTRAINT ck_salary_amounts CHECK (doctor_base >= 0 AND nurse_base >= 0 AND doctor_bonus >= 0 AND nurse_bonus >= 0)
);

DELIMITER //
CREATE TRIGGER trg_episode_no_parallel BEFORE INSERT ON episodes FOR EACH ROW
BEGIN
  IF EXISTS (SELECT 1 FROM episodes WHERE patient_id=NEW.patient_id AND disease_id=NEW.disease_id AND status='dang_dieu_tri') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Benh nhan da co dot dieu tri dang mo cho benh nay';
  END IF;
END//
CREATE TRIGGER trg_visit_sequence BEFORE INSERT ON visits FOR EACH ROW
BEGIN
  DECLARE first_day DATE;
  DECLARE episode_status VARCHAR(20);
  DECLARE next_no INT;
  SELECT started_on, status INTO first_day, episode_status FROM episodes WHERE id=NEW.episode_id;
  IF episode_status <> 'dang_dieu_tri' OR NEW.admitted_on < first_day THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Lan kham khong thuoc dot dieu tri dang mo';
  END IF;
  SELECT COALESCE(MAX(visit_no),0)+1 INTO next_no FROM visits WHERE episode_id=NEW.episode_id;
  IF NEW.visit_no <> next_no THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='So lan kham phai tang lien tiep';
  END IF;
END//
CREATE TRIGGER trg_episode_cure_date BEFORE UPDATE ON episodes FOR EACH ROW
BEGIN
  DECLARE last_visit DATE;
  IF NEW.status='da_khoi' AND OLD.status='dang_dieu_tri' THEN
    SELECT MAX(admitted_on) INTO last_visit FROM visits WHERE episode_id=OLD.id;
    IF last_visit IS NULL OR NEW.cured_on < last_visit THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Ngay khoi phai sau lan kham cuoi va dot phai co lan kham';
    END IF;
  END IF;
END//
DELIMITER ;
