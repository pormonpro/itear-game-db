import os
import psycopg2
from psycopg2.extras import RealDictCursor
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session

# Resolve paths relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static'),
    static_url_path='/static')

app.secret_key = os.environ.get('SECRET_KEY', 'evory-eshop-secret-2024')

ADMIN_ID = os.environ.get('ADMIN_ID', 'Admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'zidan001')


def get_db():
    # Use pooled URL from Supabase integration, strip incompatible query params
    url = (os.environ.get('evorydb_POSTGRES_URL') or 
           os.environ.get('evorydb_POSTGRES_PRISMA_URL') or '')
    # Remove query parameters that psycopg2 doesn't understand
    if '?' in url:
        url = url.split('?')[0]
    # Fix protocol if needed (postgres:// -> postgresql://)
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    
    conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
    return conn


def init_db():
    try:
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
    except Exception as e:
        print(f"DB init error: {e}")


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
    try:
        init_db()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM games ORDER BY name ASC')
        games = cursor.fetchall()
        conn.close()
        return render_template('index.html', games=games)
    except Exception as e:
        raw_url = os.environ.get('evorydb_POSTGRES_URL', 'NOT SET')
        return f"Database connection error: {e}<br><br>Raw URL prefix: {raw_url[:60]}...", 500


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
    try:
        init_db()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM games ORDER BY name ASC')
        games = cursor.fetchall()
        conn.close()
        return render_template('admin.html', games=games)
    except Exception as e:
        return f"Database connection error: {e}", 500


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

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_game(id):
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form.get('name')
        size = request.form.get('size')
        genre = request.form.get('genres', '')
        cover_url = request.form.get('cover_url', '')

        if name and size:
            cursor.execute('UPDATE games SET name=%s, size=%s, cover_url=%s, genre=%s WHERE id=%s', 
                           (name, size, cover_url, genre, id))
            conn.commit()
            conn.close()
            return redirect(url_for('admin'))
            
    cursor.execute('SELECT * FROM games WHERE id = %s', (id,))
    game = cursor.fetchone()
    if not game:
        conn.close()
        return redirect(url_for('admin'))
        
    conn.close()
    return render_template('edit.html', game=game)
