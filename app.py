from flask import Flask, render_template, request, redirect, session
import pymysql
import uuid
from datetime import datetime, timedelta
import qrcode
import os
from twilio.rest import Client
import config

app = Flask(__name__)
app.secret_key = "attendance_secret"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
QR_FOLDER = os.path.join(BASE_DIR, 'static', 'qr')
os.makedirs(QR_FOLDER, exist_ok=True)


# ---------------- DATABASE ----------------
def db():
    return pymysql.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )


# ---------------- LOGIN ----------------
@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']

        con = db()
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s",(u,p))
        user = cur.fetchone()

        if user:
            session['uid'] = user['id']
            session['role'] = user['role']
            return redirect('/teacher' if user['role']=='teacher' else '/student')

    return render_template('login.html')


# ---------------- TEACHER DASHBOARD ----------------
@app.route('/teacher')
def teacher():
    if session.get('role') != 'teacher':
        return redirect('/')

    con = db()
    cur = con.cursor()
    cur.execute("SELECT * FROM subjects")
    subjects = cur.fetchall()

    return render_template("teacher_dashboard.html", subjects=subjects)


# ---------------- CREATE QR ----------------
@app.route('/create_qr', methods=['POST'])
def create_qr():
    subject_id = request.form['subject']
    code = str(uuid.uuid4())[:8]
    expires = datetime.now() + timedelta(minutes=5)

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO qr_sessions(subject_id, session_code, expires_at)
        VALUES(%s,%s,%s)
    """,(subject_id, code, expires))
    con.commit()

    qr_path = os.path.join(QR_FOLDER, f"{code}.png")
    qrcode.make(code).save(qr_path)

    return render_template("generate_qr.html",
                           code=code,
                           qr_image=f"qr/{code}.png")


# ---------------- STUDENT DASHBOARD ----------------
@app.route('/student')
def student():
    if session.get('role') != 'student':
        return redirect('/')
    return render_template("student_dashboard.html")


# ---------------- MARK ATTENDANCE ----------------
@app.route('/mark', methods=['POST'])
def mark():
    qr = request.form['code']
    uid = session['uid']

    con = db()
    cur = con.cursor()

    cur.execute("SELECT id FROM students WHERE user_id=%s",(uid,))
    student = cur.fetchone()

    cur.execute("SELECT * FROM qr_sessions WHERE session_code=%s",(qr,))
    qrdata = cur.fetchone()

    if qrdata and datetime.now() < qrdata['expires_at']:
        cur.execute("""
        INSERT INTO attendance(student_id,subject_id,session_id,status)
        VALUES(%s,%s,%s,'PRESENT')
        """,(student['id'], qrdata['subject_id'], qrdata['id']))
        con.commit()
        return render_template("attendance_success.html")


    return "❌ Invalid QR"


# ---------------- ADD STUDENT ----------------
@app.route('/add_student', methods=['GET','POST'])
def add_student():
    if session.get('role') != 'teacher':
        return redirect('/')

    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        roll = request.form['roll']
        parent_phone = request.form['parent_phone']

        con = db()
        cur = con.cursor()

        cur.execute("""
            INSERT INTO users(name,username,password,role)
            VALUES(%s,%s,%s,'student')
        """,(name,username,password))
        uid = cur.lastrowid

        cur.execute("""
            INSERT INTO students(user_id,roll_no,parent_phone)
            VALUES(%s,%s,%s)
        """,(uid,roll,parent_phone))

        con.commit()
        return redirect('/teacher')

    return render_template("add_student.html")


# ---------------- ATTENDANCE REPORT ----------------
@app.route('/attendance_report', methods=['GET','POST'])
def attendance_report():
    if session.get('role') != 'teacher':
        return redirect('/')

    con = db()
    cur = con.cursor()
    cur.execute("SELECT * FROM subjects")
    subjects = cur.fetchall()

    report = None

    if request.method == 'POST':
        subject_id = request.form['subject']
        date = request.form['date']

        cur.execute("""
        SELECT users.name, subjects.subject_name,
        CASE WHEN attendance.student_id IS NULL THEN 'ABSENT'
        ELSE 'PRESENT' END AS status
        FROM students
        JOIN users ON students.user_id = users.id
        JOIN subjects ON subjects.id = %s
        LEFT JOIN attendance
        ON attendance.student_id = students.id
        AND attendance.subject_id = %s
        AND DATE(attendance.marked_at) = %s
        """,(subject_id,subject_id,date))

        report = cur.fetchall()

    return render_template("attendance_records.html",
                           subjects=subjects,
                           report=report)


# ---------------- SEND ABSENT SMS (WORKING) ----------------
@app.route('/send_absent_sms')
def send_absent_sms():
    con = db()
    cur = con.cursor()
    today = datetime.now().date()

    cur.execute("""
        SELECT users.name, students.parent_phone
        FROM students
        JOIN users ON students.user_id = users.id
        WHERE students.id NOT IN (
            SELECT student_id FROM attendance
            WHERE DATE(marked_at)=%s
        )
    """, (today,))

    absentees = cur.fetchall()
    client = Client(config.TWILIO_SID, config.TWILIO_AUTH)

    for s in absentees:
        try:
            message = f"Alert: {s['name']} is ABSENT today."
            client.messages.create(
                body=message,
                from_=config.TWILIO_NUMBER,
                to=s['parent_phone']
            )
        except Exception as e:
            print("SMS Failed for:", s['parent_phone'], e)

    return redirect('/teacher')



# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
