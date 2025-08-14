from flask import Flask, render_template, request, redirect, session
import random
import psycopg2
from psycopg2.extras import RealDictConnection
from collections import defaultdict
from flask import send_file
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'


DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", 5432)
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )



# Initialize SQLite DB

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            cash NUMERIC,
            shares INTEGER,
            portfolio_value NUMERIC
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value NUMERIC
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()


def get_price():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key='current_price'")
    result = c.fetchone()
    if result:
        price = result[0]
    else:
        price = 100
        c.execute("INSERT INTO settings (key, value) VALUES (%s, %s)", ('current_price', price))
        conn.commit()
    c.close()
    conn.close()
    return price


def set_price(price):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE settings SET value=%s WHERE key='current_price'", (price,))
    conn.commit()
    c.close()
    conn.close()


def get_user(username):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = c.fetchone()
    c.close()
    conn.close()
    return user


def create_user(username):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO users (username, cash, shares, portfolio_value) VALUES (%s, %s, %s, %s)",
              (username, 10000, 0, 10000))
    conn.commit()
    c.close()
    conn.close()


def update_user(username, cash, shares):
    portfolio_value = cash + shares * get_price()
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET cash=%s, shares=%s, portfolio_value=%s WHERE username=%s",
              (cash, shares, portfolio_value, username))
    conn.commit()
    c.close()
    conn.close()


def get_leaderboard():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT username, portfolio_value FROM users ORDER BY portfolio_value DESC;")
    rows=c.fetchall()
    c.close()
    conn.close()
    return [{"NAME": row[0],"PORTFOLIO VALUE": row[1]} for row in rows]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    if not get_user(username):
        create_user(username)
    session['username'] = username
    return redirect('/dashboard')


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user = get_user(username)
    price = get_price()
    data = {'cash': user[1], 'shares': user[2], 'portfolio_value': user[3]}
    return render_template('dashboard.html', user=username, price=price, data=data)


@app.route('/trade', methods=['POST'])
def trade():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    action = request.form['action']
    quantity = int(request.form['quantity'])
    user = get_user(username)
    cash, shares = user[1], user[2]
    price = get_price()

    if action == 'buy':
        cost = quantity * price
        if cash >= cost:
            cash -= cost
            shares += quantity
    elif action == 'sell':
        if shares >= quantity:
            cash += quantity * price
            shares -= quantity

    update_user(username, cash, shares)
    return redirect('/dashboard')


@app.route('/leaderboard')
def leaderboard():
    ranked = get_leaderboard()
    return render_template('leaderboard.html', leaderboard=ranked)


@app.route('/admin')
def admin():
    price = get_price()
    return render_template('admin.html', price=price)


@app.route('/admin/roll')
def roll():
    price = get_price()
    roll = random.randint(1, 6)
    change_map = {1: -10, 2: -5, 3: 0, 4: 5, 5: 10, 6: random.choice([-20, 20])}
    new_price = max(1, price + change_map[roll])
    set_price(new_price)
    return redirect('/admin')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/')





init_db()
if __name__ == '__main__':
    app.run(debug=True)
