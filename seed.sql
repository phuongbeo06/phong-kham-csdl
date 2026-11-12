-- CHỈ CHẠY MỘT LẦN sau schema.sql trên cơ sở dữ liệu mới, chưa có dữ liệu mẫu.
USE phong_kham;
INSERT INTO salary_config (id,doctor_base,nurse_base,doctor_bonus,nurse_bonus) VALUES (1,7000000,5000000,1000000,200000);
INSERT INTO doctors (code,identity_no,full_name,birth_date,address,grade,years_experience,education,specialty) VALUES
('BS01','001090000001','Nguyễn Minh An','1984-05-12','Hà Nội','Bác sĩ chính',14,'Thạc sĩ','Nội khoa'),
('BS02','001090000002','Trần Thu Hà','1988-09-20','Hà Nội','Bác sĩ',10,'Đại học','Tai mũi họng');
INSERT INTO nurses (employee_code,identity_no,full_name,qualification,years_experience,birth_date,address,phone) VALUES
('YT01','001090000011','Lê Mai','Cao đẳng điều dưỡng',8,'1992-04-11','Hà Nội','0901000001'),
('YT02','001090000012','Phạm Bình','Đại học điều dưỡng',6,'1994-07-19','Hà Nội','0901000002');
INSERT INTO patients (patient_code,identity_no,full_name,birth_date,address,phone) VALUES
('BN01','001090000021','Đỗ Lan','2000-02-10','Hà Nội','0911000001'),
('BN02','001090000022','Vũ Nam','1998-11-03','Bắc Ninh','0911000002'),
('BN03','001090000023','Hoàng Huy','2004-06-15','Hà Nội','0911000003');
INSERT INTO diseases (name) VALUES ('Viêm họng'),('Cảm cúm'),('Viêm dạ dày');
INSERT INTO drugs (name,unit,current_price) VALUES ('Paracetamol','viên',2000),('Amoxicillin','viên',5000),('Oresol','gói',3500);
-- Thêm lần khám khi đợt còn mở, sau đó mới đánh dấu khỏi.
INSERT INTO episodes (patient_id,disease_id,doctor_id,started_on) VALUES (1,1,2,'2026-10-02');
INSERT INTO visits (episode_id,visit_no,admitted_on,discharged_on,consultation_fee,notes) VALUES (1,1,'2026-10-02','2026-10-02',150000,'Khám lần đầu');
INSERT INTO visits (episode_id,visit_no,admitted_on,discharged_on,consultation_fee,notes) VALUES (1,2,'2026-11-01','2026-11-01',100000,'Đã khỏi');
UPDATE episodes SET status='da_khoi', cured_on='2026-11-01' WHERE id=1;
INSERT INTO episodes (patient_id,disease_id,doctor_id,started_on) VALUES (1,1,2,'2026-11-02');
INSERT INTO visits (episode_id,visit_no,admitted_on,discharged_on,consultation_fee,notes) VALUES (2,1,'2026-11-02','2026-11-02',150000,'Tái mắc sau khi đã khỏi');
INSERT INTO visits (episode_id,visit_no,admitted_on,discharged_on,consultation_fee,notes) VALUES (2,2,'2026-11-06',NULL,100000,'Tái khám');
INSERT INTO episodes (patient_id,disease_id,doctor_id,started_on) VALUES (2,2,1,'2026-11-03');
INSERT INTO visits (episode_id,visit_no,admitted_on,discharged_on,consultation_fee,notes) VALUES (3,1,'2026-11-03','2026-11-03',120000,'Khám lần đầu');
INSERT INTO visits (episode_id,visit_no,admitted_on,discharged_on,consultation_fee,notes) VALUES (3,2,'2026-11-06','2026-11-06',100000,'Đã khỏi');
UPDATE episodes SET status='da_khoi', cured_on='2026-11-06' WHERE id=3;
INSERT INTO episodes (patient_id,disease_id,doctor_id,started_on) VALUES (3,3,1,'2026-11-04');
INSERT INTO visits (episode_id,visit_no,admitted_on,discharged_on,consultation_fee,notes) VALUES
(4,1,'2026-11-04',NULL,180000,'Đang theo dõi');
INSERT INTO visit_nurses (visit_id,nurse_id,action_type) VALUES
(1,1,'tiep_don'),(2,1,'cham_soc'),(3,2,'tiep_don'),(4,2,'cap_thuoc'),
(5,1,'tiep_don'),(6,1,'cham_soc'),(7,2,'tiem_thuoc');
INSERT INTO prescriptions (visit_id,drug_id,quantity,unit_price) VALUES
(1,2,10,5000),(3,2,10,5000),(4,1,6,2000),(5,1,10,2000),(7,3,5,3500);
