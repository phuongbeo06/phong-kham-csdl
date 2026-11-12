"""Ứng dụng minh hoạ bài tập lớn CSDL phòng khám (MySQL 8 + Flask)."""
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import pymysql
from flask import Flask, flash, redirect, render_template_string, request, url_for


def load_local_config():
    """Read simple KEY=VALUE settings without requiring another package."""
    config_file = Path(__file__).with_name(".env")
    if not config_file.exists():
        return
    allowed = {"MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE", "FLASK_SECRET_KEY"}
    for raw_line in config_file.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in allowed:
            value = value.strip().strip('"').strip("'")
            # The local .env is the source of truth for this classroom app.
            # A stale MYSQL_PASSWORD in an existing VS Code terminal must not override it.
            os.environ[key] = value


load_local_config()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "local-classroom-demo")


def connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "phong_kham"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def fetch(sql, params=()):
    with connection() as db:
        with db.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def execute(sql, params=()):
    with connection() as db:
        try:
            with db.cursor() as cur:
                affected = cur.execute(sql, params)
            db.commit()
            return affected
        except Exception:
            db.rollback()
            raise


def money(value):
    return f"{Decimal(value or 0):,.0f} ₫".replace(",", ".")


app.jinja_env.filters["money"] = money


def salary_policy():
    """Upgrade an older classroom database without resetting its records."""
    with connection() as db:
        with db.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS salary_config (
                id TINYINT PRIMARY KEY,
                doctor_base DECIMAL(12,2) NOT NULL DEFAULT 7000000,
                nurse_base DECIMAL(12,2) NOT NULL DEFAULT 5000000,
                doctor_bonus DECIMAL(12,2) NOT NULL DEFAULT 1000000,
                nurse_bonus DECIMAL(12,2) NOT NULL DEFAULT 200000,
                CONSTRAINT ck_salary_amounts CHECK (doctor_base >= 0 AND nurse_base >= 0 AND doctor_bonus >= 0 AND nurse_bonus >= 0)
            )""")
            cur.execute("""INSERT IGNORE INTO salary_config (id,doctor_base,nurse_base,doctor_bonus,nurse_bonus)
                VALUES (1,7000000,5000000,1000000,200000)""")
            cur.execute("SELECT doctor_base,nurse_base,doctor_bonus,nurse_bonus FROM salary_config WHERE id=1")
            result = cur.fetchone()
        db.commit()
        return result

BASE = """<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phòng khám An Tâm</title><link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}"></head>
<body><header><div class="wrap top"><div><span class="brand">✚ Phòng khám An Tâm</span><span class="sub">Quản lý cơ sở dữ liệu</span></div>
<nav aria-label="Điều hướng chính"><a href="/">Tổng quan</a><a href="/patients">Bệnh nhân</a><a href="/directory">Danh sách</a><a href="/reports">Báo cáo</a><a href="/manage">Nhập dữ liệu</a></nav></div></header>
<main class="wrap"><div class="page-title"><h1>{{ title }}</h1><p>{{ subtitle }}</p></div>
{% with messages=get_flashed_messages(with_categories=true) %}{% for category,message in messages %}<div role="alert" class="alert {{category}}">{{ message }}</div>{% endfor %}{% endwith %}
{{ body|safe }}</main><footer class="wrap">Dữ liệu minh hoạ • MySQL 8 • Flask</footer></body></html>"""


def page(title, subtitle, template, **data):
    return render_template_string(BASE, title=title, subtitle=subtitle, body=render_template_string(template, **data))


@app.errorhandler(pymysql.MySQLError)
def database_error(error):
    code = error.args[0] if error.args else None
    guidance = {
        1045: "MySQL từ chối đăng nhập. Hãy kiểm tra MYSQL_USER và MYSQL_PASSWORD trong file .env.",
        1049: "Chưa có cơ sở dữ liệu phong_kham. Hãy chạy schema.sql rồi seed.sql trong MySQL Workbench.",
        1146: "Cơ sở dữ liệu đang thiếu bảng. Hãy chạy lại schema.sql trong MySQL Workbench.",
        2003: "Không kết nối được MySQL. Hãy kiểm tra dịch vụ MySQL80 có đang chạy.",
    }.get(code, "Ứng dụng không đọc được dữ liệu MySQL. Hãy kiểm tra cấu hình và các file SQL.")
    return page("Cần kiểm tra MySQL", guidance, """
    <section class="card"><h2>Cách khắc phục</h2>
    <p>Trong thư mục ứng dụng, sao chép <code>.env.example</code> thành <code>.env</code>, điền mật khẩu MySQL thật vào dòng <code>MYSQL_PASSWORD=</code>, rồi khởi động lại ứng dụng.</p>
    <p>Nếu đã nhập đúng mật khẩu, mở MySQL Workbench và chạy lần lượt <code>schema.sql</code>, <code>seed.sql</code>.</p>
    <p class="hint">Mã lỗi MySQL: {{ code if code is not none else 'không xác định' }}. Không gửi mật khẩu cho người khác.</p></section>
    """, code=code), 503


@app.get("/")
def home():
    counts = fetch("SELECT (SELECT COUNT(*) FROM patients) patients, (SELECT COUNT(*) FROM doctors) doctors, (SELECT COUNT(*) FROM nurses) nurses, (SELECT COUNT(*) FROM episodes WHERE status='dang_dieu_tri') active") [0]
    recent = fetch("""SELECT v.id,p.full_name patient,d.name disease,doc.full_name doctor,v.visit_no,v.admitted_on
        FROM visits v JOIN episodes e ON e.id=v.episode_id JOIN patients p ON p.id=e.patient_id
        JOIN diseases d ON d.id=e.disease_id JOIN doctors doc ON doc.id=e.doctor_id
        ORDER BY v.admitted_on DESC,v.id DESC LIMIT 8""")
    return page("Tổng quan phòng khám", "Theo dõi hoạt động khám chữa bệnh trên một màn hình.", """
    <section class="stats"><div class="stat"><span>Bệnh nhân</span><strong>{{c.patients}}</strong></div><div class="stat"><span>Bác sĩ</span><strong>{{c.doctors}}</strong></div><div class="stat"><span>Y tá</span><strong>{{c.nurses}}</strong></div><div class="stat"><span>Đợt đang điều trị</span><strong>{{c.active}}</strong></div></section>
    <section class="card"><div class="section-head"><h2>Lần khám gần đây</h2><a class="button secondary" href="/manage">Thêm dữ liệu</a></div>
    <div class="table-wrap"><table><thead><tr><th>Ngày</th><th>Bệnh nhân</th><th>Bệnh</th><th>Bác sĩ</th><th>Lần</th></tr></thead><tbody>
    {% for r in rows %}<tr><td>{{r.admitted_on}}</td><td>{{r.patient}}</td><td>{{r.disease}}</td><td>{{r.doctor}}</td><td>{{r.visit_no}}</td></tr>{% else %}<tr><td colspan="5">Chưa có lần khám.</td></tr>{% endfor %}</tbody></table></div></section>
    """, c=counts, rows=recent)


@app.get("/patients")
def patients():
    code = request.args.get("code", "").strip()
    people = fetch("SELECT id,patient_code,full_name,identity_no,birth_date,address,phone FROM patients WHERE patient_code LIKE %s OR full_name LIKE %s ORDER BY full_name", (f"%{code}%", f"%{code}%"))
    selected = request.args.get("id", type=int)
    history, active = [], []
    if selected:
        history = fetch("""SELECT e.id episode_id,d.name disease,e.status,e.started_on,e.cured_on,
            v.visit_no,v.admitted_on,v.discharged_on,v.consultation_fee,v.notes,doc.full_name doctor,
            COALESCE((SELECT SUM(p.quantity*p.unit_price) FROM prescriptions p WHERE p.visit_id=v.id),0) drug_total
            FROM episodes e JOIN diseases d ON d.id=e.disease_id JOIN doctors doc ON doc.id=e.doctor_id
            LEFT JOIN visits v ON v.episode_id=e.id WHERE e.patient_id=%s
            ORDER BY e.started_on DESC,e.id DESC,v.visit_no DESC""", (selected,))
        active = fetch("""SELECT d.name disease,e.id episode_id,COUNT(v.id) visit_count,MAX(v.admitted_on) last_visit
            FROM episodes e JOIN diseases d ON d.id=e.disease_id LEFT JOIN visits v ON v.episode_id=e.id
            WHERE e.patient_id=%s AND e.status='dang_dieu_tri' GROUP BY e.id,d.name""", (selected,))
    return page("Hồ sơ bệnh nhân", "Tìm bệnh nhân và xem toàn bộ lịch sử, đợt bệnh hiện tại.", """
    <section class="card"><form class="inline" method="get"><label for="code">Tìm theo mã hoặc tên</label><input id="code" name="code" value="{{code}}"><button>Tìm</button></form>
    <div class="table-wrap"><table><thead><tr><th>Mã</th><th>Họ tên</th><th>CCCD</th><th>Ngày sinh</th><th>Điện thoại</th><th></th></tr></thead><tbody>
    {% for p in people %}<tr><td>{{p.patient_code}}</td><td>{{p.full_name}}</td><td>{{p.identity_no}}</td><td>{{p.birth_date}}</td><td>{{p.phone}}</td><td><a href="/patients?id={{p.id}}">Xem hồ sơ</a> · <a href="/edit/patient/{{p.id}}">Sửa</a></td></tr>{% else %}<tr><td colspan="6">Không tìm thấy bệnh nhân.</td></tr>{% endfor %}</tbody></table></div></section>
    {% if selected %}<section class="card"><h2>Đang điều trị</h2>{% for a in active %}<p><strong>{{a.disease}}</strong> · Đợt #{{a.episode_id}} · Đã khám lần thứ {{a.visit_count}} · Gần nhất {{a.last_visit}}</p>{% else %}<p>Không có bệnh đang điều trị.</p>{% endfor %}</section>
    <section class="card"><h2>Lịch sử khám chữa bệnh</h2><div class="table-wrap"><table><thead><tr><th>Đợt</th><th>Bệnh</th><th>Ngày khám</th><th>Lần</th><th>Bác sĩ</th><th>Tiền khám</th><th>Tiền thuốc</th><th>Trạng thái</th></tr></thead><tbody>
    {% for h in history %}<tr><td>#{{h.episode_id}}</td><td>{{h.disease}}</td><td>{{h.admitted_on or '—'}}</td><td>{{h.visit_no or '—'}}</td><td>{{h.doctor}}</td><td>{{h.consultation_fee|money}}</td><td>{{h.drug_total|money}}</td><td>{{'Đã khỏi' if h.status=='da_khoi' else 'Đang điều trị'}}</td></tr>{% else %}<tr><td colspan="8">Chưa có lịch sử.</td></tr>{% endfor %}</tbody></table></div></section>{% endif %}
    """, code=code, people=people, selected=selected, history=history, active=active)


@app.get("/reports")
def reports():
    month = request.args.get("month") or date.today().strftime("%Y-%m")
    start = month + "-01"
    from_date = request.args.get("from") or start
    to_date = request.args.get("to") or date.today().isoformat()
    salary_config = salary_policy()
    disease = fetch("""SELECT d.name,COUNT(DISTINCT e.id) episode_count,COUNT(DISTINCT e.patient_id) patient_count
      FROM visits v JOIN episodes e ON e.id=v.episode_id JOIN diseases d ON d.id=e.disease_id
      WHERE v.admitted_on >= %s AND v.admitted_on < DATE_ADD(%s,INTERVAL 1 MONTH)
      GROUP BY d.id,d.name ORDER BY episode_count DESC,d.name""", (start,start))
    doctors = fetch("""SELECT d.code,d.full_name,COUNT(e.id) cured_count,
      s.doctor_base+COUNT(e.id)*s.doctor_bonus salary
      FROM doctors d CROSS JOIN salary_config s LEFT JOIN episodes e ON e.doctor_id=d.id AND e.status='da_khoi'
      AND e.cured_on >= %s AND e.cured_on < DATE_ADD(%s,INTERVAL 1 MONTH)
      WHERE s.id=1 GROUP BY d.id,d.code,d.full_name,s.doctor_base,s.doctor_bonus ORDER BY d.code""", (start,start))
    nurses = fetch("""SELECT n.employee_code,n.full_name,
      COUNT(CASE WHEN v.admitted_on >= %s AND v.admitted_on < DATE_ADD(%s,INTERVAL 1 MONTH) THEN 1 END) support_count,
      s.nurse_base+COUNT(CASE WHEN v.admitted_on >= %s AND v.admitted_on < DATE_ADD(%s,INTERVAL 1 MONTH) THEN 1 END)*s.nurse_bonus salary
      FROM nurses n CROSS JOIN salary_config s LEFT JOIN visit_nurses vn ON vn.nurse_id=n.id LEFT JOIN visits v ON v.id=vn.visit_id
      WHERE s.id=1 GROUP BY n.id,n.employee_code,n.full_name,s.nurse_base,s.nurse_bonus ORDER BY n.employee_code""", (start,start,start,start))
    revenue = fetch("""SELECT
      COALESCE((SELECT SUM(consultation_fee) FROM visits WHERE admitted_on BETWEEN %s AND %s),0) visit_total,
      COALESCE((SELECT SUM(p.quantity*p.unit_price) FROM prescriptions p JOIN visits v ON v.id=p.visit_id WHERE v.admitted_on BETWEEN %s AND %s),0) drug_total""", (from_date,to_date,from_date,to_date))[0]
    return page("Báo cáo", "Các truy vấn theo đúng yêu cầu của đề bài.", """
    <section class="card"><form class="inline" method="get"><label for="month">Tháng</label><input id="month" type="month" name="month" value="{{month}}" required><label for="from">Doanh thu từ</label><input id="from" type="date" name="from" value="{{from_date}}"><label for="to">đến</label><input id="to" type="date" name="to" value="{{to_date}}"><button>Xem báo cáo</button></form></section>
    <div class="grid"><section class="card"><h2>Bệnh trong tháng</h2><p class="hint">Một đợt tái mắc được tính riêng; nhiều lần khám trong cùng đợt chỉ tính một lần.</p><div class="table-wrap"><table><thead><tr><th>Bệnh</th><th>Đợt mắc</th><th>Bệnh nhân</th></tr></thead><tbody>{% for r in disease %}<tr><td>{{r.name}}</td><td>{{r.episode_count}}</td><td>{{r.patient_count}}</td></tr>{% else %}<tr><td colspan="3">Không có dữ liệu.</td></tr>{% endfor %}</tbody></table></div></section>
    <section class="card"><h2>Doanh thu</h2><p class="metric">{{(revenue.visit_total+revenue.drug_total)|money}}</p><p>Tiền khám: {{revenue.visit_total|money}}</p><p>Tiền thuốc: {{revenue.drug_total|money}}</p></section></div>
    <div class="section-head"><h2>Lương nhân viên</h2><a class="button secondary" href="/salary">Chỉnh mức lương</a></div>
    <div class="grid"><section class="card"><h2>Lương bác sĩ</h2><p class="hint">{{salary_config.doctor_base|money}} cơ bản + {{salary_config.doctor_bonus|money}} mỗi đợt khỏi trong tháng.</p><div class="table-wrap"><table><thead><tr><th>Bác sĩ</th><th>Đợt khỏi</th><th>Lương</th></tr></thead><tbody>{% for r in doctors %}<tr><td>{{r.full_name}}</td><td>{{r.cured_count}}</td><td>{{r.salary|money}}</td></tr>{% endfor %}</tbody></table></div></section>
    <section class="card"><h2>Lương y tá</h2><p class="hint">{{salary_config.nurse_base|money}} cơ bản + {{salary_config.nurse_bonus|money}} mỗi lần hỗ trợ một lần khám.</p><div class="table-wrap"><table><thead><tr><th>Y tá</th><th>Lần hỗ trợ</th><th>Lương</th></tr></thead><tbody>{% for r in nurses %}<tr><td>{{r.full_name}}</td><td>{{r.support_count}}</td><td>{{r.salary|money}}</td></tr>{% endfor %}</tbody></table></div></section></div>
    """, month=month, from_date=from_date, to_date=to_date, disease=disease, doctors=doctors, nurses=nurses, revenue=revenue, salary_config=salary_config)


FORMS = {
    "patient": ("Thêm bệnh nhân", "INSERT INTO patients(patient_code,identity_no,full_name,birth_date,address,phone) VALUES (%s,%s,%s,%s,%s,%s)", ["patient_code","identity_no","full_name","birth_date","address","phone"]),
    "doctor": ("Thêm bác sĩ", "INSERT INTO doctors(code,identity_no,full_name,birth_date,address,grade,years_experience,education,specialty) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", ["code","identity_no","full_name","birth_date","address","grade","years_experience","education","specialty"]),
    "nurse": ("Thêm y tá", "INSERT INTO nurses(employee_code,identity_no,full_name,qualification,years_experience,birth_date,address,phone) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", ["employee_code","identity_no","full_name","qualification","years_experience","birth_date","address","phone"]),
    "disease": ("Thêm bệnh", "INSERT INTO diseases(name) VALUES (%s)", ["name"]),
    "drug": ("Thêm thuốc", "INSERT INTO drugs(name,unit,current_price) VALUES (%s,%s,%s)", ["name","unit","current_price"]),
    "episode": ("Mở đợt điều trị", "INSERT INTO episodes(patient_id,disease_id,doctor_id,started_on) VALUES (%s,%s,%s,%s)", ["patient_id","disease_id","doctor_id","started_on"]),
    "visit": ("Thêm lần khám", "INSERT INTO visits(episode_id,visit_no,admitted_on,discharged_on,consultation_fee,notes) VALUES (%s,%s,%s,%s,%s,%s)", ["episode_id","visit_no","admitted_on","discharged_on","consultation_fee","notes"]),
    "support": ("Ghi nhận y tá hỗ trợ", "INSERT INTO visit_nurses(visit_id,nurse_id,action_type) VALUES (%s,%s,%s)", ["visit_id","nurse_id","action_type"]),
    "prescription": ("Kê thuốc", "INSERT INTO prescriptions(visit_id,drug_id,quantity,unit_price) VALUES (%s,%s,%s,%s)", ["visit_id","drug_id","quantity","unit_price"]),
    "cure": ("Đánh dấu đã khỏi", "UPDATE episodes SET status='da_khoi',cured_on=%s WHERE id=%s AND status='dang_dieu_tri'", ["cured_on","episode_id"]),
}
LABELS = dict(patient_code="Mã bệnh nhân",identity_no="CCCD",full_name="Họ tên",birth_date="Ngày sinh",address="Địa chỉ",phone="Điện thoại",code="Mã bác sĩ",grade="Bậc nghề",years_experience="Thâm niên (năm)",education="Trình độ đào tạo",specialty="Chuyên môn",employee_code="Mã y tá",qualification="Trình độ",name="Tên",unit="Đơn vị",current_price="Giá hiện tại",patient_id="Bệnh nhân",disease_id="Bệnh",doctor_id="Bác sĩ",started_on="Ngày bắt đầu",episode_id="Đợt điều trị",visit_no="Lần khám thứ",admitted_on="Ngày vào",discharged_on="Ngày ra (có thể trống)",consultation_fee="Tiền khám",notes="Ghi chú",visit_id="Lần khám",nurse_id="Y tá",action_type="Việc hỗ trợ",drug_id="Thuốc",quantity="Số lượng",unit_price="Giá bán mỗi đơn vị",cured_on="Ngày khỏi")
SELECTS = dict(patient_id="patients",disease_id="diseases",doctor_id="doctors",episode_id="episodes",visit_id="visits",nurse_id="nurses",drug_id="drugs")
EDITABLE = {
    "doctor": ("Bác sĩ", "doctors", ["code","identity_no","full_name","birth_date","address","grade","years_experience","education","specialty"]),
    "nurse": ("Y tá", "nurses", ["employee_code","identity_no","full_name","qualification","years_experience","birth_date","address","phone"]),
    "patient": ("Bệnh nhân", "patients", ["patient_code","identity_no","full_name","birth_date","address","phone"]),
    "drug": ("Thuốc", "drugs", ["name","unit","current_price"]),
    "disease": ("Bệnh", "diseases", ["name"]),
}
DIRECTORY_FIELDS = {
    "doctor": ["code","full_name","specialty","grade","years_experience"],
    "nurse": ["employee_code","full_name","qualification","years_experience","phone"],
    "patient": ["patient_code","full_name","birth_date","phone"],
    "drug": ["name","unit","current_price"],
    "disease": ["name"],
}


@app.get("/directory")
def directory():
    groups = []
    for kind, (title, table, _) in EDITABLE.items():
        columns = DIRECTORY_FIELDS[kind]
        rows = fetch(f"SELECT id,{','.join(columns)} FROM {table} ORDER BY id DESC")
        groups.append(dict(kind=kind, title=title, columns=columns, rows=rows))
    return page("Danh sách và chỉnh sửa", "Xem nhân viên, bệnh nhân, thuốc và bệnh; sửa hoặc xóa từng hồ sơ.", """
    <div class="jump-links"><a href="#doctor">Bác sĩ</a><a href="#nurse">Y tá</a><a href="#patient">Bệnh nhân</a><a href="#drug">Thuốc</a><a href="#disease">Bệnh</a></div>
    {% for group in groups %}<section class="card" id="{{group.kind}}"><div class="section-head"><h2>{{group.title}} <span class="count">{{group.rows|length}}</span></h2><a class="button secondary" href="/manage">Thêm mới</a></div>
    <div class="table-wrap"><table><thead><tr>{% for column in group.columns %}<th>{{labels[column]}}</th>{% endfor %}<th>Thao tác</th></tr></thead><tbody>
    {% for row in group.rows %}<tr>{% for column in group.columns %}<td>{{row[column]|money if column=='current_price' else row[column]}}</td>{% endfor %}
    <td><div class="row-actions"><a href="/edit/{{group.kind}}/{{row.id}}">Sửa</a>
    <form method="post" action="/delete/{{group.kind}}/{{row.id}}" onsubmit="return confirm('{{'Xóa toàn bộ hồ sơ và lịch sử khám của bệnh nhân này?' if group.kind=='patient' else 'Xóa mục này? Nếu đã được dùng trong lịch sử khám, hệ thống sẽ từ chối.'}}')"><button class="danger" type="submit">Xóa</button></form></div></td></tr>
    {% else %}<tr><td colspan="{{group.columns|length+1}}">Chưa có dữ liệu.</td></tr>{% endfor %}
    </tbody></table></div></section>{% endfor %}
    """, groups=groups, labels=LABELS)


@app.route("/edit/<kind>/<int:item_id>", methods=["GET", "POST"])
def edit_item(kind, item_id):
    if kind not in EDITABLE:
        return "Không tìm thấy loại hồ sơ", 404
    title, table, fields = EDITABLE[kind]
    existing = fetch(f"SELECT id,{','.join(fields)} FROM {table} WHERE id=%s", (item_id,))
    if not existing:
        return "Không tìm thấy hồ sơ", 404
    row = existing[0]
    if request.method == "POST":
        values = [request.form.get(field, "").strip() for field in fields]
        if any(not value for value in values):
            flash("Vui lòng nhập đầy đủ thông tin.", "error")
        else:
            try:
                for field, value in zip(fields, values):
                    if field in ("current_price", "years_experience") and Decimal(value) < 0:
                        raise ValueError("Giá và thâm niên không được âm")
                assignments = ",".join(f"{field}=%s" for field in fields)
                execute(f"UPDATE {table} SET {assignments} WHERE id=%s", (*values, item_id))
                flash(f"Đã cập nhật {title.lower()}.", "success")
                return redirect(url_for("directory") + "#" + kind)
            except (pymysql.MySQLError, ValueError) as exc:
                flash(f"Không thể cập nhật: {exc}", "error")
    return page("Sửa " + title.lower(), "Chỉnh thông tin rồi bấm Lưu thay đổi.", """
    <section class="card edit-card"><form method="post" class="fields">
    {% for field in fields %}<label>{{labels[field]}}<input name="{{field}}" value="{{row[field] if row[field] is not none else ''}}" type="{{'date' if field=='birth_date' else 'number' if field in ['years_experience','current_price'] else 'text'}}" {{'min=0 step=0.01' if field=='current_price' else 'min=0 step=1' if field=='years_experience' else ''}} required></label>{% endfor %}
    <div class="form-actions"><button type="submit">Lưu thay đổi</button><a class="button secondary" href="/directory#{{kind}}">Quay lại</a></div></form></section>
    """, fields=fields, labels=LABELS, row=row, kind=kind)


@app.post("/delete/<kind>/<int:item_id>")
def delete_item(kind, item_id):
    if kind not in EDITABLE:
        return "Không tìm thấy loại hồ sơ", 404
    title, table, _ = EDITABLE[kind]
    try:
        if kind == "patient":
            with connection() as db:
                try:
                    with db.cursor() as cur:
                        cur.execute("DELETE p FROM prescriptions p JOIN visits v ON v.id=p.visit_id JOIN episodes e ON e.id=v.episode_id WHERE e.patient_id=%s", (item_id,))
                        cur.execute("DELETE vn FROM visit_nurses vn JOIN visits v ON v.id=vn.visit_id JOIN episodes e ON e.id=v.episode_id WHERE e.patient_id=%s", (item_id,))
                        cur.execute("DELETE v FROM visits v JOIN episodes e ON e.id=v.episode_id WHERE e.patient_id=%s", (item_id,))
                        cur.execute("DELETE FROM episodes WHERE patient_id=%s", (item_id,))
                        cur.execute("DELETE FROM patients WHERE id=%s", (item_id,))
                        affected = cur.rowcount
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
        else:
            affected = execute(f"DELETE FROM {table} WHERE id=%s", (item_id,))
        flash(f"Đã xóa {title.lower()}." if affected else "Hồ sơ không còn tồn tại.", "success" if affected else "error")
    except pymysql.IntegrityError:
        flash(f"Không thể xóa {title.lower()} vì đang được dùng trong lịch sử khám. Bạn vẫn có thể sửa thông tin.", "error")
    return redirect(url_for("directory") + "#" + kind)


@app.route("/salary", methods=["GET", "POST"])
def salary_settings():
    fields = ["doctor_base", "nurse_base", "doctor_bonus", "nurse_bonus"]
    labels = dict(doctor_base="Lương cơ bản bác sĩ", nurse_base="Lương cơ bản y tá", doctor_bonus="Thưởng mỗi đợt khỏi", nurse_bonus="Thưởng mỗi lần y tá hỗ trợ")
    current = salary_policy()
    if request.method == "POST":
        try:
            values = [Decimal(request.form.get(field, "")) for field in fields]
            if any(value < 0 for value in values):
                raise ValueError("Mức lương không được âm")
            execute("UPDATE salary_config SET doctor_base=%s,nurse_base=%s,doctor_bonus=%s,nurse_bonus=%s WHERE id=1", values)
            flash("Đã cập nhật mức lương. Báo cáo sẽ dùng mức mới.", "success")
            return redirect(url_for("reports"))
        except (pymysql.MySQLError, ValueError, ArithmeticError) as exc:
            flash(f"Không thể lưu mức lương: {exc}", "error")
    return page("Chỉnh mức lương", "Các mức mặc định đúng đề bài; thay đổi ở đây sẽ áp dụng cho báo cáo.", """
    <section class="card edit-card"><form method="post" class="fields">
    {% for field in fields %}<label>{{labels[field]}}<input type="number" name="{{field}}" value="{{current[field]}}" min="0" step="1000" required></label>{% endfor %}
    <div class="form-actions"><button type="submit">Lưu mức lương</button><a class="button secondary" href="/reports">Quay lại báo cáo</a></div></form></section>
    """, fields=fields, labels=labels, current=current)


@app.get("/manage")
def manage():
    options = {
        "patient_id": fetch("SELECT id,CONCAT(patient_code,' · ',full_name) label FROM patients ORDER BY id DESC"),
        "disease_id": fetch("SELECT id,name label FROM diseases ORDER BY name"),
        "doctor_id": fetch("SELECT id,CONCAT(code,' · ',full_name) label FROM doctors ORDER BY id"),
        "episode_id": fetch("""SELECT e.id,CONCAT('#',e.id,' · ',p.full_name,' · ',d.name,' (',e.status,')') label
            FROM episodes e JOIN patients p ON p.id=e.patient_id JOIN diseases d ON d.id=e.disease_id ORDER BY e.id DESC"""),
        "visit_id": fetch("""SELECT v.id,CONCAT('#',v.id,' · đợt ',v.episode_id,' · lần ',v.visit_no) label FROM visits v ORDER BY v.id DESC"""),
        "nurse_id": fetch("SELECT id,CONCAT(employee_code,' · ',full_name) label FROM nurses ORDER BY id"),
        "drug_id": fetch("SELECT id,CONCAT(name,' · ',current_price,' ₫') label FROM drugs ORDER BY name"),
    }
    return page("Nhập dữ liệu", "Các thao tác cơ bản để dùng và kiểm tra mô hình phòng khám.", """
    <p class="hint">Thứ tự thuận tiện: thêm danh mục và nhân sự → bệnh nhân → mở đợt → lần khám → hỗ trợ/kê thuốc → đánh dấu khỏi.</p>
    <div class="form-grid">{% for key,form in forms.items() %}<section class="card"><h2>{{form[0]}}</h2><form action="/add/{{key}}" method="post" class="fields">
    {% for field in form[2] %}<label>{{labels[field]}}{% if field in options %}<select name="{{field}}" required><option value="">Chọn...</option>{% for option in options[field] %}<option value="{{option.id}}">{{option.label}}</option>{% endfor %}</select>
    {% elif field=='action_type' %}<select name="{{field}}" required><option value="tiep_don">Tiếp đón</option><option value="cap_thuoc">Cấp thuốc</option><option value="tiem_thuoc">Tiêm thuốc</option><option value="cham_soc">Chăm sóc</option></select>
    {% else %}<input name="{{field}}" type="{{'date' if field.endswith('_on') or field=='birth_date' or field=='admitted_on' or field=='discharged_on' else 'number' if field in ['years_experience','current_price','visit_no','consultation_fee','quantity','unit_price'] else 'text'}}" {{'min=0 step=0.01' if field in ['current_price','consultation_fee','unit_price'] else 'min=1' if field in ['visit_no','quantity'] else ''}} {{'' if field in ['discharged_on','notes'] else 'required'}}>{% endif %}</label>{% endfor %}
    <button type="submit">Lưu</button></form></section>{% endfor %}</div>
    """, forms=FORMS, labels=LABELS, options=options)


@app.post("/add/<kind>")
def add(kind):
    if kind not in FORMS:
        return "Không tìm thấy thao tác", 404
    title, sql, fields = FORMS[kind]
    values = [request.form.get(field) or None for field in fields]
    if any(value is None for field,value in zip(fields,values) if field not in ("discharged_on","notes")):
        flash("Vui lòng nhập đủ các trường bắt buộc.", "error")
        return redirect(url_for("manage"))
    try:
        affected = execute(sql, values)
        if kind == "cure" and affected == 0:
            flash("Đợt điều trị đã khỏi hoặc không tồn tại.", "error")
        else:
            flash(f"Đã lưu: {title.lower()}.", "success")
    except (pymysql.MySQLError, ValueError) as exc:
        flash(f"Không thể lưu. Kiểm tra dữ liệu và ràng buộc: {exc}", "error")
    return redirect(url_for("manage"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
