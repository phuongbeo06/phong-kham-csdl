-- Chạy một lần trên CSDL đã tạo trước khi có tính năng sửa lương.
USE phong_kham;
CREATE TABLE IF NOT EXISTS salary_config (
  id TINYINT PRIMARY KEY,
  doctor_base DECIMAL(12,2) NOT NULL DEFAULT 7000000,
  nurse_base DECIMAL(12,2) NOT NULL DEFAULT 5000000,
  doctor_bonus DECIMAL(12,2) NOT NULL DEFAULT 1000000,
  nurse_bonus DECIMAL(12,2) NOT NULL DEFAULT 200000,
  CONSTRAINT ck_salary_amounts CHECK (doctor_base >= 0 AND nurse_base >= 0 AND doctor_bonus >= 0 AND nurse_bonus >= 0)
);
INSERT IGNORE INTO salary_config (id,doctor_base,nurse_base,doctor_bonus,nurse_bonus)
VALUES (1,7000000,5000000,1000000,200000);
