import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_session'  # In production, use a secure random key
app.config['UPLOAD_FOLDER'] = 'static/uploads'

DATABASE = 'games.db'

# Dummy Admin Credentials
ADMIN_ID = 'Admin'
ADMIN_PASSWORD = 'zidan001'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                size TEXT NOT NULL,
                cover_url TEXT,
                genre TEXT
            )
        ''')
        db.commit()

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
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM games ORDER BY name COLLATE NOCASE ASC')
    games = cursor.fetchall()
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
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM games ORDER BY name COLLATE NOCASE ASC')
    games = cursor.fetchall()
    return render_template('admin.html', games=games)

@app.route('/admin/add', methods=['POST'])
@login_required
def add_game():
    name = request.form.get('name')
    size = request.form.get('size')
    genre = request.form.get('genres', '')  # Expecting comma-separated genres from custom JS
    
    cover_url = ''
    if 'cover_image' in request.files:
        file = request.files['cover_image']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            cover_url = url_for('static', filename='uploads/' + filename)

    if name and size:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO games (name, size, cover_url, genre) VALUES (?, ?, ?, ?)', (name, size, cover_url, genre))
        db.commit()
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:id>')
@login_required
def delete_game(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM games WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('admin'))

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_game(id):
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        name = request.form.get('name')
        size = request.form.get('size')
        genre = request.form.get('genres', '')
        cover_url = request.form.get('cover_url', '')
        
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                cover_url = url_for('static', filename='uploads/' + filename)

        if name and size:
            cursor.execute('UPDATE games SET name=?, size=?, cover_url=?, genre=? WHERE id=?', (name, size, cover_url, genre, id))
            db.commit()
            return redirect(url_for('admin'))
            
    cursor.execute('SELECT * FROM games WHERE id = ?', (id,))
    game = cursor.fetchone()
    if not game:
        return redirect(url_for('admin'))
        
    return render_template('edit.html', game=game)

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True, port=5000)
