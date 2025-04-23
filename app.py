from flask import Flask, render_template, request, redirect, url_for, flash, make_response
from flask_mysqldb import MySQL
import config
import csv
import io
from io import StringIO

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Thay bằng key mạnh hơn

# Cấu hình MySQL
app.config.update(
    MYSQL_HOST=config.DB_HOST,
    MYSQL_USER=config.DB_USER,
    MYSQL_PASSWORD=config.DB_PASSWORD,
    MYSQL_DB=config.DB_NAME,
    MYSQL_CURSORCLASS='DictCursor'
)

mysql = MySQL(app)

# Tạo bảng students nếu chưa tồn tại
with app.app_context():
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL UNIQUE,
                phone VARCHAR(20),
                major VARCHAR(50)
            )
        """)
        mysql.connection.commit()
    except Exception as e:
        print(f"Lỗi khi tạo bảng: {str(e)}")
    finally:
        if 'cur' in locals():
            cur.close()

@app.route('/')
def index():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM students")
        students = cur.fetchall()
           # Ngay trước return render_template
        print("Dữ liệu sinh viên:", students)
        print("Kiểu dữ liệu:", type(students))
        print("Số lượng:", len(students))
        return render_template('index.html', students=students)
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        return render_template('index.html', students=[])
    finally:
        if 'cur' in locals():
            cur.close()

@app.route('/add', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            major = request.form.get('major', '').strip()

            if not name or not email:
                flash('Tên và email là bắt buộc', 'danger')
                return redirect(url_for('add_student'))

            cur = mysql.connection.cursor()
            cur.execute(
                "INSERT INTO students (name, email, phone, major) VALUES (%s, %s, %s, %s)",
                (name, email, phone, major)
            )
            mysql.connection.commit()
            flash('Thêm sinh viên thành công!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Lỗi khi thêm sinh viên: {str(e)}', 'danger')
        finally:
            if 'cur' in locals():
                cur.close()
    
    return render_template('add_student.html')

@app.route('/import-csv', methods=['GET', 'POST'])
def import_csv():
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('Vui lòng chọn file CSV', 'danger')
            return redirect(request.url)
            
        file = request.files['csv_file']
        
        if file.filename == '':
            flash('Không có file được chọn', 'danger')
            return redirect(request.url)
            
        if not file.filename.lower().endswith('.csv'):
            flash('File phải có định dạng .csv', 'danger')
            return redirect(request.url)

        try:
            stream = file.stream.read().decode("utf-8-sig")
            csv_data = csv.DictReader(io.StringIO(stream))
            cur = mysql.connection.cursor()
            imported_count = 0
            
            for row in csv_data:
                if not row.get('name') or not row.get('email'):
                    continue
                    
                cur.execute(
                    """INSERT INTO students (name, email, phone, major)
                    VALUES (%s, %s, %s, %s)""",
                    (
                        row['name'].strip(),
                        row['email'].strip(),
                        row.get('phone', '').strip(),
                        row.get('major', '').strip()
                    )
                )
                imported_count += 1
                
            mysql.connection.commit()
            flash(f'Đã import thành công {imported_count} sinh viên', 'success')
            
            cur.execute("SELECT * FROM students")
            students = cur.fetchall()
            return render_template('index.html', students=students) 
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Lỗi khi import: {str(e)}', 'danger')
            print(f"Lỗi chi tiết: {str(e)}")
            
        finally:
            if 'cur' in locals():
                cur.close()
                
        return redirect(url_for('index'))
    
 
    return render_template('import_csv.html')

@app.route('/edit/<int:student_id>', methods=['GET'])  # Đổi tên tham số thành student_id để tránh nhầm lẫn
def edit_student(student_id):  # Đổi tên tham số hàm
    try:
        cur = mysql.connection.cursor()
        
        # Lấy dữ liệu sinh viên
        cur.execute("SELECT * FROM students WHERE id = %s", (student_id,))  # Sử dụng student_id thay vì id
        columns = [col[0] for col in cur.description]  # Lấy tên các cột
        student_data = cur.fetchone()
        
        if not student_data:
            flash('Không tìm thấy sinh viên', 'danger')
            return redirect(url_for('index'))
        
        # Chuyển đổi tuple thành dictionary
        student = dict(zip(columns, student_data))
        
        return render_template('edit_student.html', student=student)
        
    except Exception as e:
        flash(f'Lỗi khi lấy dữ liệu: {str(e)}', 'danger')
        return redirect(url_for('index'))
    finally:
        if 'cur' in locals():
            cur.close()

@app.route('/update/<int:student_id>', methods=['POST'])  # Đổi tên tham số
def update_student(student_id):  # Đổi tên tham số hàm
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            phone = request.form.get('phone', '')
            major = request.form.get('major', '')
            
            cur = mysql.connection.cursor()
            cur.execute(
                "UPDATE students SET name = %s, email = %s, phone = %s, major = %s WHERE id = %s",
                (name, email, phone, major, student_id)  # Sử dụng student_id
            )
            mysql.connection.commit()
            flash('Cập nhật thông tin thành công', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Lỗi khi cập nhật: {str(e)}', 'danger')
        finally:
            if 'cur' in locals():
                cur.close()
    
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete_student(id):
    try:
        cur = mysql.connection.cursor()
        
        # 1. Xóa sinh viên
        cur.execute("DELETE FROM students WHERE id = %s", (id,))
        
        # 2. Lấy toàn bộ dữ liệu còn lại
        cur.execute("SELECT * FROM students ORDER BY id")
        remaining_students = cur.fetchall()
        
        # 3. Tắt kiểm tra khóa ngoại tạm thời
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # 4. Xóa và tạo lại bảng (cách reset ID triệt để nhất)
        cur.execute("TRUNCATE TABLE students")
        
        # 5. Insert lại dữ liệu với ID mới
        for new_id, student in enumerate(remaining_students, start=1):
            # Giả sử cấu trúc: id, name, email, phone
            cur.execute(
                "INSERT INTO students (id, name, email, phone) VALUES (%s, %s, %s, %s)",
                (new_id, student[1], student[2], student[3])
            )
        
        # 6. Bật lại kiểm tra khóa ngoại
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        # 7. Reset AUTO_INCREMENT
        cur.execute(f"ALTER TABLE students AUTO_INCREMENT = {len(remaining_students) + 1}")
        
        mysql.connection.commit()
        flash('Đã xóa và reset ID thành công', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Lỗi khi xử lý: {str(e)}', 'danger')
        app.logger.error(f"Error: {str(e)}")
        
    finally:
        if 'cur' in locals():
            cur.close()
            
    return redirect(url_for('index'))
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/export-csv')
def export_csv():
    try:
        # Lấy dữ liệu từ database
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM students")
        students = cur.fetchall()
        
        # Tạo file CSV trong bộ nhớ
        output = StringIO()
        writer = csv.writer(output)
        
        # Viết header
        writer.writerow(['ID', 'Họ tên', 'Email', 'Điện thoại', 'Chuyên ngành'])
        
        # Viết dữ liệu
        for student in students:
            writer.writerow([
                student['id'],
                student['name'],
                student['email'],
                student['phone'] or '',
                student['major'] or ''
            ])
        
        # Tạo response
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=danh_sach_sinh_vien.csv'
        response.headers['Content-type'] = 'text/csv'
        
        return response
        
    except Exception as e:
        flash(f'Lỗi khi export: {str(e)}', 'danger')
        return redirect(url_for('index'))
    finally:
        if 'cur' in locals():
            cur.close()

if __name__ == '__main__':
    app.run(debug=True)