from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort, make_response
import json
from functools import wraps
from datetime import datetime
import csv
import io

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_here'
app.config['SESSION_TYPE'] = 'filesystem'

# Mock данные
WITCHERS = {
    "Geralt": {"school": "Wolf", "toxicity": 35, "vitality": 90, "signs": ["Igni", "Aard", "Quen"]},
    "Lambert": {"school": "Wolf", "toxicity": 45, "vitality": 80, "signs": ["Aard", "Yrden"]},
    "Letho": {"school": "Viper", "toxicity": 50, "vitality": 85, "signs": ["Quen", "Axii"]}
}

SCHOOLS = {
    "Wolf": {"access": ["kaermorhen", "wolf_gear"], "color": "#8b9dc3"},
    "Viper": {"access": ["viper_gear"], "color": "#4CAF50"},
    "Griffin": {"access": ["griffin_gear"], "color": "#FFC107"}
}

ALCHEMY_ITEMS = [
    {"name": "Black Blood", "type": "potion", "toxicity": 40},
    {"name": "Golden Oriole", "type": "potion", "toxicity": 20},
    {"name": "Swallow", "type": "potion", "toxicity": 30},
    {"name": "Dancing Star", "type": "bomb", "toxicity": 15},
    {"name": "Dragon's Dream", "type": "bomb", "toxicity": 25}
]

CONTRACTS = [
    {"monster": "Kikimora", "reward": 500, "date": "2023-05-15", "completed": True},
    {"monster": "Leshen", "reward": 1200, "date": "2023-06-20", "completed": True},
    {"monster": "Bruxa", "reward": 800, "date": "2023-07-10", "completed": False}
]


# Декоратор для проверки доступа к маршрутам
def school_required(route):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'school' not in session:
                return redirect(url_for('login'))
            if route not in SCHOOLS[session['school']]['access']:
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Декоратор для проверки ранга
def master_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rank') != 'Master':
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('profile'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        school = request.form['school']
        rank = request.form.get('rank', 'Novice')

        if username in WITCHERS and school == WITCHERS[username]['school']:
            session['username'] = username
            session['school'] = school
            session['rank'] = rank
            return redirect(url_for('profile'))
        return "Invalid credentials", 401

    return render_template('login.html', schools=SCHOOLS.keys())


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    witcher = {
        "name": session['username'],
        **WITCHERS[session['username']]
    }

    return render_template('profile.html',
                           witcher=witcher,
                           school_color=SCHOOLS[session['school']]['color'])


@app.route('/kaermorhen')
@school_required('kaermorhen')
def kaermorhen():
    return render_template('kaermorhen.html')


@app.route('/alchemy')
def alchemy():
    item_type = request.args.get('type')
    toxicity = request.args.get('toxicity', type=int)

    filtered_items = ALCHEMY_ITEMS

    if item_type:
        filtered_items = [item for item in filtered_items if item['type'] == item_type]

    if toxicity is not None:
        filtered_items = [item for item in filtered_items if item['toxicity'] >= toxicity]

    if request.headers.get('Accept') == 'application/json':
        return jsonify([item['name'] for item in filtered_items])

    return render_template('alchemy.html', items=filtered_items)


@app.route('/bestiary', methods=['GET', 'POST'])
def bestiary():
    try:
        with open('monsters.json', 'r') as f:
            monsters = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        monsters = []

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            monsters.append({
                "name": request.form['name'],
                "type": request.form['type'],
                "weakness": request.form['weakness']
            })
        elif action == 'delete':
            monsters = [m for m in monsters if m['name'] != request.form['name']]

        with open('monsters.json', 'w') as f:
            json.dump(monsters, f)

        return redirect(url_for('bestiary'))

    search = request.args.get('search')
    if search:
        monsters = [m for m in monsters if search.lower() in m['weakness'].lower()]

    return render_template('bestiary.html', monsters=monsters)


@app.route('/contracts')
@master_required
def contracts():
    return render_template('contracts.html', contracts=CONTRACTS)


@app.route('/contracts/report')
@master_required
def contracts_report():
    completed = [c for c in CONTRACTS if c['completed']]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Monster', 'Reward', 'Date Completed'])

    for contract in completed:
        writer.writerow([contract['monster'], contract['reward'], contract['date']])

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=contracts_report.csv'
    response.headers['Content-type'] = 'text/csv'
    return response


@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    try:
        with open('reviews.json', 'r') as f:
            reviews = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        reviews = []

    if request.method == 'POST':
        reviews.append({
            "contract": request.form['contract'],
            "rating": int(request.form['rating']),
            "comment": request.form['comment'],
            "author": session.get('username', 'Anonymous'),
            "date": datetime.now().strftime("%Y-%m-%d")
        })

        with open('reviews.json', 'w') as f:
            json.dump(reviews, f)

        return redirect(url_for('reviews'))

    return render_template('reviews.html', reviews=reviews)


@app.route('/witcher/stats')
def witcher_stats():
    if 'username' not in session:
        abort(401)

    witcher = WITCHERS.get(session['username'], {})

    return jsonify({
        "name": session['username'],
        "school": session['school'],
        "toxicity": witcher.get('toxicity', 0),
        "active_quests": [c['monster'] for c in CONTRACTS if not c['completed']],
        "gear": ["Silver Sword", "Witcher Armor"]
    })


def calculate_total_gold():
    return sum(c['reward'] for c in CONTRACTS if c['completed'])


if __name__ == '__main__':
    app.run(debug=True)