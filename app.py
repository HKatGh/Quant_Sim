from flask import Flask, render_template, request, redirect, session
import random
import sqlite3
from collections import defaultdict
from flask import send_file
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Initialize SQLite DB
def init_db():
    conn = sqlite3.connect('quant_sim.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    cash REAL,
                    shares INTEGER,
                    portfolio_value REAL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value REAL
                )''')
    conn.commit()
    conn.close()


def get_price():
    conn = sqlite3.connect('quant_sim.db')
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key='current_price'")
    result = c.fetchone()
    if result:
        price = result[0]
    else:
        price = 100
        c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ('current_price', price))
        conn.commit()
    conn.close()
    return price


def set_price(price):
    conn = sqlite3.connect('quant_sim.db')
    c = conn.cursor()
    c.execute("UPDATE settings SET value=? WHERE key='current_price'", (price,))
    conn.commit()
    conn.close()


def get_user(username):
    conn = sqlite3.connect('quant_sim.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    return user


def create_user(username):
    conn = sqlite3.connect('quant_sim.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (username, cash, shares, portfolio_value) VALUES (?, ?, ?, ?)",
              (username, 10000, 0, 10000))
    conn.commit()
    conn.close()


def update_user(username, cash, shares):
    portfolio_value = cash + shares * get_price()
    conn = sqlite3.connect('quant_sim.db')
    c = conn.cursor()
    c.execute("UPDATE users SET cash=?, shares=?, portfolio_value=? WHERE username=?",
              (cash, shares, portfolio_value, username))
    conn.commit()
    conn.close()


def get_leaderboard():
    conn = sqlite3.connect('quant_sim.db')
    c = conn.cursor()
    c.execute("SELECT username, portfolio_value FROM users ORDER BY portfolio_value DESC")
    rows = c.fetchall()
    conn.close()
    return [{"username": row[0], "portfolio_value": row[1]} for row in rows]


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


@app.route('/download-db')
def download_db():
    if os.path.exists('quant_sim.db'):
        return send_file('quant_sim.db', as_attachment=True)
    return "Database not found", 404


init_db()
if __name__ == '__main__':
    app.run(debug=True)
