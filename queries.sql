USE phong_kham;
-- Đổi các biến này để tra cứu tháng/khoảng ngày khác.
SET @month_start = '2026-11-01';
SET @month_end = DATE_ADD(@month_start, INTERVAL 1 MONTH);
SET @patient_code = 'BN01';
SET @from_date = '2026-11-01';
SET @to_date = '2026-11-30';

-- 1. Bệnh trong tháng: một đợt điều trị chỉ tính một lần, tái mắc là đợt mới.
SELECT d.name AS benh, COUNT(DISTINCT e.id) AS so_dot_mac,
       COUNT(DISTINCT e.patient_id) AS so_benh_nhan
FROM visits v JOIN episodes e ON e.id=v.episode_id
JOIN diseases d ON d.id=e.disease_id
WHERE v.admitted_on >= @month_start AND v.admitted_on < @month_end
GROUP BY d.id,d.name ORDER BY so_dot_mac DESC,d.name;

-- 2a. Lương bác sĩ: thưởng khi đợt được ghi nhận đã khỏi trong tháng.
SELECT d.code,d.full_name,s.doctor_base AS luong_co_ban,
       COUNT(e.id) AS so_dot_khoi,s.doctor_base+COUNT(e.id)*s.doctor_bonus AS tong_luong
FROM doctors d CROSS JOIN salary_config s LEFT JOIN episodes e ON e.doctor_id=d.id
 AND e.status='da_khoi' AND e.cured_on >= @month_start AND e.cured_on < @month_end
WHERE s.id=1 GROUP BY d.id,d.code,d.full_name,s.doctor_base,s.doctor_bonus ORDER BY d.code;

-- 2b. Một y tá được thưởng một lần cho mỗi lần khám có hỗ trợ.
SELECT n.employee_code,n.full_name,s.nurse_base AS luong_co_ban,
       COUNT(CASE WHEN v.admitted_on >= @month_start AND v.admitted_on < @month_end THEN 1 END) AS so_lan_ho_tro,
       s.nurse_base+COUNT(CASE WHEN v.admitted_on >= @month_start AND v.admitted_on < @month_end THEN 1 END)*s.nurse_bonus AS tong_luong
FROM nurses n CROSS JOIN salary_config s LEFT JOIN visit_nurses vn ON vn.nurse_id=n.id
LEFT JOIN visits v ON v.id=vn.visit_id
WHERE s.id=1 GROUP BY n.id,n.employee_code,n.full_name,s.nurse_base,s.nurse_bonus ORDER BY n.employee_code;

-- 3a. Hồ sơ, lịch sử và số lần khám theo từng đợt.
SELECT p.patient_code,p.full_name,p.identity_no,p.birth_date,p.address,p.phone,
       d.name AS benh,e.id AS dot_dieu_tri,e.status,e.started_on,e.cured_on,
       v.visit_no,v.admitted_on,v.discharged_on,v.consultation_fee,v.notes,
       doc.full_name AS bac_si
FROM patients p LEFT JOIN episodes e ON e.patient_id=p.id
LEFT JOIN diseases d ON d.id=e.disease_id
LEFT JOIN doctors doc ON doc.id=e.doctor_id
LEFT JOIN visits v ON v.episode_id=e.id
WHERE p.patient_code=@patient_code
ORDER BY e.started_on DESC,v.visit_no DESC;

-- 3b. Bệnh đang mắc và lần khám hiện tại.
SELECT p.patient_code,p.full_name,d.name AS benh,e.id AS dot_dieu_tri,
       COALESCE(MAX(v.visit_no),0) AS da_kham_lan_thu
FROM patients p JOIN episodes e ON e.patient_id=p.id AND e.status='dang_dieu_tri'
JOIN diseases d ON d.id=e.disease_id LEFT JOIN visits v ON v.episode_id=e.id
WHERE p.patient_code=@patient_code
GROUP BY p.id,p.patient_code,p.full_name,d.name,e.id;

-- 4. Doanh thu, tách tiền khám và thuốc để tránh nhân đôi khi có nhiều thuốc.
SELECT COALESCE((SELECT SUM(consultation_fee) FROM visits WHERE admitted_on BETWEEN @from_date AND @to_date),0) AS tien_kham,
       COALESCE((SELECT SUM(p.quantity*p.unit_price) FROM prescriptions p JOIN visits v ON v.id=p.visit_id WHERE v.admitted_on BETWEEN @from_date AND @to_date),0) AS tien_thuoc,
       COALESCE((SELECT SUM(consultation_fee) FROM visits WHERE admitted_on BETWEEN @from_date AND @to_date),0)
       + COALESCE((SELECT SUM(p.quantity*p.unit_price) FROM prescriptions p JOIN visits v ON v.id=p.visit_id WHERE v.admitted_on BETWEEN @from_date AND @to_date),0) AS tong_doanh_thu;
