# Bài tập lớn CSDL: Phòng khám tư nhân

Bộ nộp gồm mô hình EER, lệnh MySQL và ứng dụng web đơn giản. Dữ liệu trong `seed.sql` là dữ liệu minh họa, không phải hồ sơ thật.

## Chạy ứng dụng

1. Cài MySQL 8 và Python 3.10 trở lên.
2. Trong MySQL, chạy `schema.sql`, rồi `seed.sql`. Có thể chạy `queries.sql` để xem các truy vấn riêng lẻ.
   Chỉ chạy `seed.sql` một lần trên cơ sở dữ liệu mới; chạy lại sẽ bị trùng mã và khóa chính.
3. Trong thư mục này, chạy `python -m venv .venv` và kích hoạt môi trường ảo; sau đó chạy `pip install -r requirements.txt`.
4. Sao chép `.env.example` thành `.env`, sửa thông tin MySQL, đặc biệt là `MYSQL_PASSWORD`. Ứng dụng tự đọc `.env` khi khởi động và ưu tiên giá trị trong file này nếu terminal còn giữ mật khẩu cũ. Không đưa `.env` lên GitHub.
5. Chạy `python app.py`, mở `http://127.0.0.1:5000`.

### Từng bước trên Windows với VS Code và MySQL Workbench

1. Trong VS Code, chọn **File → Open Folder** và mở chính thư mục `phong-kham` (thư mục chứa `app.py`).
2. Nhấn **Ctrl+Shift+P**, chạy **Python: Select Interpreter**, chọn `.venv\Scripts\python.exe` trong thư mục này. Nếu không thấy, chọn **Enter interpreter path** và trỏ tới file đó.
3. Mở **Terminal → New Terminal**. Trong terminal PowerShell, chạy ` .\.venv\Scripts\python.exe -m pip install -r requirements.txt `. Máy cần kết nối tới kho gói Python ở bước này. Kiểm tra bằng ` .\.venv\Scripts\python.exe -c "import flask, pymysql; print('OK')" `.
4. Mở MySQL Workbench và đăng nhập kết nối MySQL đang chạy. Mở `schema.sql`, bấm nút tia sét để chạy toàn bộ. Sau đó mở `seed.sql` và chạy toàn bộ. `queries.sql` chỉ dùng để xem và thử các câu truy vấn, không cần chạy trước ứng dụng.
5. Mở `.env` và thay `your_password` bằng mật khẩu MySQL của bạn. File `.env` nằm cùng thư mục với `app.py`.
6. Chạy ` .\.venv\Scripts\python.exe app.py `, sau đó mở `http://127.0.0.1:5000` trên trình duyệt. Để dừng ứng dụng, nhấn **Ctrl+C** trong terminal.

Nếu thấy `No module named flask` hoặc `No module named pymysql`, quay lại bước 3 và chắc chắn lệnh cài đặt dùng chính `.venv\Scripts\python.exe`. Nếu thấy `Access denied for user 'root'`, kiểm tra lại mật khẩu ở bước 5. Nếu thấy `Unknown database 'phong_kham'`, chạy lại `schema.sql` ở bước 4.

Nếu chưa tạo `.env`, bạn có thể dùng biến môi trường PowerShell:

```powershell
$env:MYSQL_HOST='127.0.0.1'
$env:MYSQL_USER='root'
$env:MYSQL_PASSWORD='mat-khau-cua-ban'
$env:MYSQL_DATABASE='phong_kham'
$env:FLASK_SECRET_KEY='khoa-bat-ky-cho-demo'
python app.py
```

## Quy ước nghiệp vụ

- Một **đợt điều trị** là một lần mắc một bệnh. Các lần khám liên tiếp thuộc cùng đợt. Sau khi khỏi, nếu mắc lại thì mở một đợt mới.
- Mỗi đợt điều trị có đúng một bệnh và một bác sĩ phụ trách. Mỗi lần khám thuộc đúng một đợt. Một lần khám có thể có nhiều y tá, nhưng một y tá chỉ được tính một lần hỗ trợ cho lần khám đó.
- Giá thuốc tại thời điểm kê được chép vào `prescriptions.unit_price` để doanh thu lịch sử không đổi khi giá danh mục thay đổi.
- Tổng tiền mỗi lần khám là tiền khám cộng tổng tiền thuốc trong lần khám, được tính khi truy vấn thay vì lưu lặp.
- Lương bác sĩ tính theo ngày đánh dấu khỏi (`cured_on`); lương y tá theo ngày vào khám (`admitted_on`).
- Doanh thu tính theo ngày vào khám. Các khoảng ngày doanh thu bao gồm cả ngày bắt đầu và kết thúc.

## Màn hình và tính năng

Tổng quan; tìm và xem toàn bộ lịch sử bệnh nhân; báo cáo bệnh trong tháng, lương bác sĩ, lương y tá, doanh thu; 10 thao tác thêm dữ liệu: thêm bệnh nhân, bác sĩ, y tá, bệnh, thuốc, mở đợt, thêm lần khám, ghi nhận hỗ trợ, kê thuốc, đánh dấu khỏi.

Trang **Danh sách** hiển thị bác sĩ, y tá, bệnh nhân, thuốc và bệnh, với nút **Sửa** và **Xóa**. Xóa bệnh nhân sẽ xóa cả các đợt điều trị, lần khám, hỗ trợ của y tá và đơn thuốc thuộc hồ sơ đó sau khi người dùng xác nhận. Bác sĩ, y tá, thuốc hoặc bệnh đã được dùng trong lịch sử khám sẽ không thể xóa; có thể sửa thông tin của họ.

Trang **Báo cáo → Chỉnh mức lương** cho phép sửa lương cơ bản và mức thưởng. Mặc định là 7 triệu/5 triệu lương cơ bản và 1 triệu/200 nghìn tiền thưởng đúng theo đề. Khi thay đổi, báo cáo dùng mức mới cho mọi tháng được xem.

Nếu cơ sở dữ liệu đã tạo bằng bản cũ, khi mở Báo cáo ứng dụng tự thêm bảng `salary_config` mà không xóa dữ liệu. Có thể chạy `migration_salary.sql` một lần trong MySQL Workbench nếu muốn thêm bảng trước khi mở ứng dụng.

Các ràng buộc chính được đặt tại CSDL: mã/CCCD duy nhất, khóa ngoại, tiền và số lượng hợp lệ, số lần khám tăng liên tiếp, một bệnh nhân không mở đồng thời hai đợt cho cùng bệnh, mỗi y tá tối đa một bản ghi hỗ trợ cho một lần khám. Những trường hợp sai được ứng dụng báo lại khi lưu.

## Giới hạn của bản minh họa

Ứng dụng phục vụ bài tập trên máy cá nhân hoặc mạng tin cậy. Chưa có đăng nhập, phân quyền, kiểm toán hay bảo vệ dữ liệu y tế để dùng trong thực tế. Cần có máy MySQL đang chạy để kiểm thử tích hợp.

## Đưa lên GitHub

Tạo một repository mới trên GitHub, chọn tải các file trong thư mục này lên, rồi nộp đường dẫn repository. Không tải file `.env` chứa mật khẩu MySQL. File `mo_hinh_eer_phong_kham.pdf` cũng nên có trong repository để người chấm xem đủ bộ.
