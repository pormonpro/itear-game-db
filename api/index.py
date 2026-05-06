import os
import psycopg2
from psycopg2.extras import RealDictCursor
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__,
    template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'))

app.secret_key = os.environ.get('SECRET_KEY', 'itear-eshop-secret-2024')

DATABASE_URL = os.environ.get('DATABASE_URL', '')
ADMIN_ID = os.environ.get('ADMIN_ID', 'Admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'zidan001')


def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            size TEXT NOT NULL,
            cover_url TEXT,
            genre TEXT
        )
    ''')
    conn.commit()
    conn.close()


# Require login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM games ORDER BY name ASC')
    games = cursor.fetchall()
    conn.close()
    return render_template('index.html', games=games)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['admin_id'] == ADMIN_ID and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            error = 'Invalid Admin ID or password. Please try again.'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))


@app.route('/admin')
@login_required
def admin():
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM games ORDER BY name ASC')
    games = cursor.fetchall()
    conn.close()
    return render_template('admin.html', games=games)


@app.route('/admin/add', methods=['POST'])
@login_required
def add_game():
    name = request.form.get('name')
    size = request.form.get('size')
    genre = request.form.get('genres', '')
    cover_url = request.form.get('cover_url', '')

    if name and size:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO games (name, size, cover_url, genre) VALUES (%s, %s, %s, %s)',
                       (name, size, cover_url, genre))
        conn.commit()
        conn.close()
    return redirect(url_for('admin'))


@app.route('/admin/delete/<int:id>')
@login_required
def delete_game(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM games WHERE id = %s', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))
