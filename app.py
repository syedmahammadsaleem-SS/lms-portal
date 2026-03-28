import os
import sqlite3
from flask import Flask, render_template, request, redirect, session, send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from transformers import pipeline

# ✅ FREE AI MODEL
chatbot_model = pipeline("text-generation", model="distilgpt2")

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ================= DATABASE =================
def get_db():
    return sqlite3.connect("database.db")


def create_tables():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        password TEXT,
        role TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS courses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        file TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS quiz(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        option1 TEXT,
        option2 TEXT,
        option3 TEXT,
        option4 TEXT,
        answer TEXT
    )
    """)

    conn.commit()
    conn.close()


# Create DB tables
create_tables()


# ================= ROUTES =================

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
            (name, email, password, 'student')
        )

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db()
        cur = conn.cursor()

        user = cur.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()

        conn.close()

        if user:
            session['user_id'] = user[0]
            session['role'] = user[4]
            return redirect('/dashboard')

        return "Invalid login"

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    conn = get_db()
    cur = conn.cursor()

    courses = cur.execute("SELECT * FROM courses").fetchall()

    # Ensure uploads folder exists
    if not os.path.exists('static/uploads'):
        os.makedirs('static/uploads')

    files = os.listdir('static/uploads')

    conn.close()

    return render_template('dashboard.html', courses=courses, files=files)


@app.route('/add-course', methods=['POST'])
def add_course():
    title = request.form.get('title')
    description = request.form.get('description')
    file = request.form.get('file')

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO courses (title, description, file) VALUES (?, ?, ?)",
        (title, description, file)
    )

    conn.commit()
    conn.close()

    return redirect('/dashboard')


@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']

    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

    return redirect('/dashboard')


@app.route('/view/<filename>')
def view_file(filename):
    ext = filename.split('.')[-1].lower()
    return render_template('view.html', file=filename, ext=ext)


@app.route('/quiz')
def quiz():
    conn = get_db()
    cur = conn.cursor()

    questions = cur.execute("SELECT * FROM quiz").fetchall()
    conn.close()

    return render_template('quiz.html', questions=questions)


@app.route('/submit-quiz', methods=['POST'])
def submit_quiz():
    conn = get_db()
    cur = conn.cursor()

    questions = cur.execute("SELECT * FROM quiz").fetchall()
    conn.close()

    score = 0

    for q in questions:
        qid = str(q[0])
        selected = request.form.get(qid)

        if selected == q[6]:
            score += 1

    return render_template('result.html', score=score, total=len(questions))


@app.route('/add-question', methods=['GET', 'POST'])
def add_question():
    if session.get('role') != 'admin':
        return "Access Denied ❌"

    if request.method == 'POST':
        question = request.form.get('question')
        o1 = request.form.get('option1')
        o2 = request.form.get('option2')
        o3 = request.form.get('option3')
        o4 = request.form.get('option4')
        answer = request.form.get('answer')

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO quiz (question, option1, option2, option3, option4, answer) VALUES (?,?,?,?,?,?)",
            (question, o1, o2, o3, o4, answer)
        )

        conn.commit()
        conn.close()

        return redirect('/quiz')

    return render_template('add_question.html')


@app.route('/certificate/<int:score>/<int:total>')
def certificate(score, total):
    file_name = "certificate.pdf"

    doc = SimpleDocTemplate(file_name)
    styles = getSampleStyleSheet()

    content = []
    content.append(Paragraph("LMS Certificate", styles['Title']))
    content.append(Spacer(1, 20))
    content.append(Paragraph("Congratulations!", styles['Normal']))
    content.append(Spacer(1, 10))
    content.append(Paragraph("You successfully completed the quiz.", styles['Normal']))
    content.append(Spacer(1, 10))
    content.append(Paragraph(f"Score: {score} / {total}", styles['Normal']))

    doc.build(content)

    return send_file(file_name, as_attachment=True)


# 🤖 AI CHATBOT
@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    response = ""

    if request.method == 'POST':
        user_input = request.form.get('message')

        try:
            result = chatbot_model(user_input, max_length=100, num_return_sequences=1)
            response = result[0]['generated_text']
        except Exception as e:
            response = "Error: " + str(e)

    return render_template('chatbot.html', response=response)


# ================= RUN FOR RENDER =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)