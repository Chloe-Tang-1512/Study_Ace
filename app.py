from flask import Flask, render_template, request, redirect, url_for, session, flash, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from random import shuffle
from difflib import SequenceMatcher
from sqlalchemy.exc import IntegrityError
import random
import datetime
from flask import send_file
import io
import csv
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///flashcards.db')
app.config['APPLICATION_NAME'] = 'Study Ace'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    flashcard_sets = db.relationship('FlashcardSet', backref='user', lazy=True)
    streak = db.Column(db.Integer, default=0)
    last_active = db.Column(db.String(20), default=None)
    points = db.Column(db.Integer, default=0)
    badges = db.Column(db.String(255), default="")
    daily_challenge_date = db.Column(db.String(20), default=None)
    daily_challenge_progress = db.Column(db.Integer, default=0)
    daily_challenge_completed = db.Column(db.Boolean, default=False)

class FlashcardSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cards = db.relationship('Flashcard', backref='flashcard_set', lazy=True)

class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(200), nullable=False)
    definition = db.Column(db.String(500), nullable=False)
    set_id = db.Column(db.Integer, db.ForeignKey('flashcard_set.id'), nullable=False)
    tags = db.Column(db.String(200), default="")  # comma-separated tags

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('signup'))
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        session['theme'] = 'blue'
        default_set = FlashcardSet.query.filter_by(title="Python (default)", user_id=new_user.id).first()
        if not default_set:
            python_set = FlashcardSet(title="Python (default)", user_id=new_user.id)
            db.session.add(python_set)
            db.session.commit()
            default_cards = [
                ("Python", "A high-level programming language."),
                ("Variable", "A storage location paired with an associated symbolic name."),
                ("Function", "A block of reusable code that performs a specific task."),
                ("Loop", "A programming construct that repeats a block of code."),
            ]
            for term, definition in default_cards:
                db.session.add(Flashcard(term=term, definition=definition, set_id=python_set.id))
            db.session.commit()
        flash('Account created successfully')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Logged in successfully')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        challenge = session.get('daily_challenge')
        if challenge and challenge.get('date') == str(datetime.date.today()):
            user.daily_challenge_date = challenge['date']
            user.daily_challenge_progress = challenge['progress']
            user.daily_challenge_completed = challenge['completed']
            db.session.commit()
    session.pop('user_id', None)
    session.pop('daily_challenge', None)
    return redirect(url_for('index'))

def calculate_user_level(user):
    points = getattr(user, 'points', 0)
    levels = [
        (100, "Beginner"),
        (500, "Intermediate"),
        (1000, "Advanced"),
        (2500, "Expert"),
        (5000, "Master"),
        (7500, "Legend"),
        (10000, "Mythic"),
        (25000, "Supreme"),
        (50000, "Ultimate"),
        (750000, "Godlike"),
        (1000000, "Master of Knowledge"),
    ]
    for threshold, name in levels:
        if points < threshold:
            return name
    return "The Ultimate Student"

@app.route('/leaderboard')
def leaderboard():
    users = User.query.all()
    leaderboard_data = []
    for user in users:
        level = calculate_user_level(user)
        leaderboard_data.append({
            "id": user.id,
            "username": user.username,
            "points": user.points,
            "level": level
        })
    leaderboard_data.sort(key=lambda x: x["points"], reverse=True)
    top_users = leaderboard_data[:10]
    user_ranks = {user["id"]: idx + 1 for idx, user in enumerate(leaderboard_data)}
    my_rank = None
    my_user = None
    if 'user_id' in session:
        my_rank = user_ranks.get(session["user_id"])
        my_user = next((u for u in leaderboard_data if u["id"] == session["user_id"]), None)
    else:
        my_rank = None
        my_user = None
    return render_template(
        'leaderboard.html',
        top_users=top_users,
        my_rank=my_rank,
        my_user=my_user,
        all_users=leaderboard_data,
        user_ranks=user_ranks
    )

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        flash('You must be logged in to access the dashboard.', 'info')
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        flash('User not found. Please log in again.', 'info')
        return redirect(url_for('login'))
    search_query = ""
    flashcard_sets = list(user.flashcard_sets)
    if request.method == 'POST':
        search_query = request.form.get('search_query', '').strip().lower()
        if search_query:
            matching = [s for s in flashcard_sets if search_query in s.title.lower()]
            non_matching = [s for s in flashcard_sets if search_query not in s.title.lower()]
            flashcard_sets = matching + non_matching
            flash(f"Showing results for '{search_query}'", 'info')
    streak = getattr(user, 'streak', 0)
    points = getattr(user, 'points', 0)
    update_achievements(user)
    achievements = [b for b in (user.badges or "").split(",") if b]
    user_rank = calculate_user_level(user)
    daily_challenge = get_daily_challenge()
    latest_achievement = None
    achievements_sorted = sorted(
        achievements,
        key=lambda a: (
            1 if a == "Created your first set" and len(achievements) > 1 else 0,
            achievements.index(a)
        )
    )
    if achievements_sorted:
        latest_achievement = achievements_sorted[-1]
        if latest_achievement == "Created your first set" and len(achievements_sorted) > 1:
            latest_achievement = achievements_sorted[-2]
    return render_template(
        'dashboard.html',
        flashcard_sets=flashcard_sets,
        manage_account_url=url_for('account'),
        search_query=search_query,
        streak=streak,
        points=points,
        achievements=achievements,
        latest_achievement=latest_achievement,
        user_rank=user_rank,
        daily_challenge=daily_challenge
    )

@app.route('/create_set', methods=['GET', 'POST'])
def create_set():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        terms = request.form.getlist('term')
        definitions = request.form.getlist('definition')
        valid_cards = []
        for term, definition in zip(terms, definitions):
            if term and definition:
                valid_cards.append((term, definition))
        if len(valid_cards) < 2:
            flash('You must add at least two flashcards to create a set.')
            return render_template(
                'create_set.html',
                prev_title=title,
                prev_terms=terms,
                prev_definitions=definitions
            )
        new_set = FlashcardSet(title=title, user_id=session['user_id'])
        db.session.add(new_set)
        db.session.commit()
        for term, definition in valid_cards:
            card = Flashcard(term=term, definition=definition, set_id=new_set.id)
            db.session.add(card)
        db.session.commit()
        flash('Flashcard set created successfully')
        return redirect(url_for('dashboard'))
    return render_template('create_set.html')

@app.route('/review/<int:set_id>')
def review_set(set_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    flashcard_set = FlashcardSet.query.get_or_404(set_id)
    if flashcard_set.user_id != session['user_id']:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    return render_template('review.html', flashcard_set=flashcard_set)

@app.route('/delete_set/<int:set_id>', methods=['POST'])
def delete_set(set_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    flashcard_set = FlashcardSet.query.get_or_404(set_id)
    if flashcard_set.user_id != session['user_id']:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    for card in flashcard_set.cards:
        db.session.delete(card)
    db.session.delete(flashcard_set)
    db.session.commit()
    flash('Flashcard set deleted successfully')
    return redirect(url_for('dashboard'))

@app.route('/edit_set/<int:set_id>', methods=['GET', 'POST'])
def edit_set(set_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    flashcard_set = FlashcardSet.query.get_or_404(set_id)
    if flashcard_set.user_id != session['user_id']:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        flashcard_set.title = request.form['title']
        for card in flashcard_set.cards:
            db.session.delete(card)
        db.session.commit()
        terms = request.form.getlist('term')
        definitions = request.form.getlist('definition')
        tags_list = request.form.getlist('tags')
        for term, definition, tags in zip(terms, definitions, tags_list):
            if term and definition:
                card = Flashcard(term=term, definition=definition, set_id=flashcard_set.id, tags=tags)
                db.session.add(card)
        db.session.commit()
        flash('Flashcard set updated successfully')
        return redirect(url_for('dashboard'))
    return render_template('edit_set.html', flashcard_set=flashcard_set)

@app.route('/game/<int:set_id>', methods=['GET', 'POST'])
def flashcard_game(set_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    flashcard_set = FlashcardSet.query.get_or_404(set_id)
    if flashcard_set.user_id != session['user_id']:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    cards = flashcard_set.cards[:]
    if not cards:
        flash('No cards in this set.')
        return redirect(url_for('dashboard'))
    if 'game_order' not in session or session.get('game_set_id') != set_id:
        card_order = list(range(len(cards)))
        shuffle(card_order)
        session['game_order'] = card_order
        session['game_index'] = 0
        session['game_score'] = 0
        session['game_set_id'] = set_id
    else:
        card_order = session['game_order']
    idx = session['game_index']
    score = session['game_score']
    if idx >= len(card_order):
        final_score = score
        session.pop('game_index', None)
        session.pop('game_score', None)
        session.pop('game_set_id', None)
        session.pop('game_order', None)
        return render_template('game_result.html', score=final_score, total=len(card_order), flashcard_set=flashcard_set)
    current_card = cards[card_order[idx]]
    if request.method == 'POST':
        user_answer = request.form.get('user_answer', '').strip()
        correct_answer = current_card.definition
        similarity = SequenceMatcher(None, user_answer.lower(), correct_answer.lower()).ratio()
        if similarity > 0.7:
            score += 1
            flash('Correct!')
            update_daily_challenge(1)
        elif similarity > 0.4:
            flash(f'Almost correct! The correct answer was: {correct_answer}')
        else:
            flash(f'Incorrect. The correct answer was: {correct_answer}')
        idx += 1
        session['game_index'] = idx
        session['game_score'] = score
        return redirect(url_for('flashcard_game', set_id=set_id))
    return render_template(
        'game.html',
        term=current_card.term,
        idx=idx + 1,
        total=len(card_order),
        score=score,
        set_id=set_id,
        flashcard_set=flashcard_set
    )

@app.route('/practise/<int:set_id>', methods=['GET', 'POST'])
def flashcard_practise(set_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    flashcard_set = FlashcardSet.query.get_or_404(set_id)
    if flashcard_set.user_id != session['user_id']:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    mode = request.args.get('mode')
    if not mode:
        return render_template(
            'practise_menu.html',
            set_id=set_id,
            flashcard_set=flashcard_set
        )
    cards = flashcard_set.cards[:]
    if not cards:
        flash('No cards in this set.')
        return redirect(url_for('dashboard'))
    if mode == 'classic':
        if 'practise_order' not in session or session.get('practise_set_id') != set_id or len(session.get('practise_order', [])) != len(cards):
            card_order = list(range(len(cards)))
            shuffle(card_order)
            session['practise_order'] = card_order
            session['practise_index'] = 0
            session['practise_score'] = 0
            session['practise_set_id'] = set_id
        else:
            card_order = session['practise_order']
        idx = session['practise_index']
        score = session['practise_score']
        if idx >= len(card_order):
            final_score = score
            session.pop('practise_index', None)
            session.pop('practise_score', None)
            session.pop('practise_set_id', None)
            session.pop('practise_order', None)
            flash(f'Practise complete! You scored {final_score} out of {len(card_order)}.', 'info')
            return render_template('practise_result.html', score=final_score, total=len(card_order), flashcard_set=flashcard_set)
        current_card = cards[card_order[idx]]
        if request.method == 'POST':
            user_answer = request.form.get('user_answer', '').strip()
            correct_answer = current_card.definition
            similarity = SequenceMatcher(None, user_answer.lower(), correct_answer.lower()).ratio()
            if similarity > 0.7:
                score += 1
                flash('Correct!', 'info')
                add_points_and_badges(User.query.get(session['user_id']), 10)
                update_daily_challenge(1)
            elif similarity > 0.4:
                flash(f'Almost correct! The correct answer was: {correct_answer}', 'info')
                add_points_and_badges(User.query.get(session['user_id']), 2)
            else:
                flash(f'Incorrect. The correct answer was: {correct_answer}', 'info')
            idx += 1
            session['practise_index'] = idx
            session['practise_score'] = score
            return redirect(url_for('flashcard_practise', set_id=set_id, mode='classic'))
        return render_template(
            'practise.html',
            term=current_card.term,
            idx=idx + 1,
            total=len(card_order),
            score=score,
            set_id=set_id,
            flashcard_set=flashcard_set
        )
    elif mode == 'multiple_choice':
        if len(cards) < 4:
            flash('Need at least 4 cards for multiple choice mode.', 'info')
            return redirect(url_for('dashboard'))
        if 'mc_order' not in session or session.get('mc_set_id') != set_id or len(session.get('mc_order', [])) != len(cards):
            card_order = list(range(len(cards)))
            shuffle(card_order)
            session['mc_order'] = card_order
            session['mc_index'] = 0
            session['mc_score'] = 0
            session['mc_set_id'] = set_id
        else:
            card_order = session['mc_order']
        idx = session['mc_index']
        score = session['mc_score']
        if idx >= len(card_order):
            final_score = score
            session.pop('mc_index', None)
            session.pop('mc_score', None)
            session.pop('mc_set_id', None)
            session.pop('mc_order', None)
            flash(f'Practise complete! You scored {final_score} out of {len(card_order)}.', 'info')
            return render_template('game_result.html', score=final_score, total=len(card_order), flashcard_set=flashcard_set)
        current_card = cards[card_order[idx]]
        correct_answer = current_card.definition
        options = [correct_answer]
        other_defs = [c.definition for i, c in enumerate(cards) if i != card_order[idx]]
        shuffle(other_defs)
        while len(options) < 4 and other_defs:
            option = other_defs.pop()
            if option not in options:
                options.append(option)
        shuffle(options)
        if request.method == 'POST':
            user_choice = request.form.get('choice')
            if user_choice == correct_answer:
                score += 1
                flash('Correct!', 'info')
                add_points_and_badges(User.query.get(session['user_id']), 10)
                update_daily_challenge(1)
            else:
                flash(f'Incorrect. The correct answer was: {correct_answer}', 'info')
            idx += 1
            session['mc_index'] = idx
            session['mc_score'] = score
            return redirect(url_for('flashcard_practise', set_id=set_id, mode='multiple_choice'))
        return render_template(
            'multiple_choice.html',
            term=current_card.term,
            options=options,
            idx=idx + 1,
            total=len(card_order),
            score=score,
            set_id=set_id,
            flashcard_set=flashcard_set
        )
    elif mode == 'fill_blank':
        fill_cards = [c for c in cards if len(c.definition.split()) >= 3]
        skip_words = {
            "a", "an", "the", "some", "and", "or", "but", "if", "then", "with", "of", "to", "for", "on", "in", "by", "at", "from", "as", "is", "are", "was", "were", "be", "been", "being", "that", "this", "these", "those", "it", "its", "their", "his", "her", "our", "your", "my", "i", "you", "he", "she", "they", "we", "not", "so", "do", "does", "did"
        }
        if 'fb_order' not in session or session.get('fb_set_id') != set_id or len(session.get('fb_order', [])) != len(fill_cards):
            card_order = list(range(len(fill_cards)))
            shuffle(card_order)
            session['fb_order'] = card_order
            session['fb_index'] = 0
            session['fb_score'] = 0
            session['fb_set_id'] = set_id
            session['fb_blank_index'] = {}
        else:
            card_order = session['fb_order']

        idx = session['fb_index']
        score = session['fb_score']

        if idx >= len(card_order):
            final_score = score
            session.pop('fb_index', None)
            session.pop('fb_score', None)
            session.pop('fb_set_id', None)
            session.pop('fb_order', None)
            session.pop('fb_blank_index', None)
            flash(f'Practise complete! You scored {final_score} out of {len(card_order)}.', 'info')
            return render_template('game_result.html', score=final_score, total=len(card_order), flashcard_set=flashcard_set)

        current_card = fill_cards[card_order[idx]]
        words = current_card.definition.split()

        fb_blank_index = session.get('fb_blank_index', {})
        if request.method == 'POST':
            blank_index = fb_blank_index.get(str(idx))
            if blank_index is None or blank_index >= len(words):
                important_indices = [i for i, w in enumerate(words) if w.lower().strip(".,;:!?") not in skip_words and len(w) > 2]
                blank_index = random.choice(important_indices) if important_indices else 0
            correct_word = words[blank_index]
            user_input = request.form.get('user_answer', '').strip()
            if user_input.lower() == correct_word.lower():
                score += 1
                flash('Correct!', 'info')
                add_points_and_badges(User.query.get(session['user_id']), 10)
                update_daily_challenge(1)
            else:
                flash(f'Incorrect. The correct word was: {correct_word}', 'info')
            idx += 1
            session['fb_index'] = idx
            session['fb_score'] = score
            session['fb_blank_index'] = fb_blank_index
            return redirect(url_for('flashcard_practise', set_id=set_id, mode='fill_blank'))
        else:
            if str(idx) not in fb_blank_index:
                important_indices = [i for i, w in enumerate(words) if w.lower().strip(".,;:!?") not in skip_words and len(w) > 2]
                blank_index = random.choice(important_indices) if important_indices else 0
                fb_blank_index[str(idx)] = blank_index
                session['fb_blank_index'] = fb_blank_index
            else:
                blank_index = fb_blank_index[str(idx)]
            blanked = words[:]
            blanked[blank_index] = "____"
            blanked_definition = " ".join(blanked)

        return render_template(
            'fill_blank.html',
            term=current_card.term,
            blanked_definition=blanked_definition,
            idx=idx + 1,
            total=len(card_order),
            score=score,
            set_id=set_id,
            flashcard_set=flashcard_set
        )
    else:
        flash('Invalid practise mode.', 'info')
        return redirect(url_for('dashboard'))

@app.route('/account', methods=['GET', 'POST'])
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'edit_username':
            new_username = request.form.get('new_username', '').strip()
            if not new_username:
                flash('Username cannot be empty.')
            elif User.query.filter_by(username=new_username).first():
                flash('Username already exists.')
            else:
                user.username = new_username
                try:
                    db.session.commit()
                    flash('Username updated successfully.')
                except IntegrityError:
                    db.session.rollback()
                    flash('Username already exists.')
        elif action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            if not check_password_hash(user.password, current_password):
                flash('Current password is incorrect.')
            elif not new_password:
                flash('New password cannot be empty.')
            else:
                user.password = generate_password_hash(new_password)
                db.session.commit()
                flash('Password updated successfully.')
        elif action == 'delete_account':
            password = request.form.get('delete_password', '')
            if not check_password_hash(user.password, password):
                flash('Password incorrect. Account not deleted.')
            else:
                for flashcard_set in user.flashcard_sets:
                    for card in flashcard_set.cards:
                        db.session.delete(card)
                    db.session.delete(flashcard_set)
                db.session.delete(user)
                db.session.commit()
                session.pop('user_id', None)
                flash('Account deleted successfully.')
                return redirect(url_for('index'))
        elif action == 'change_theme':
            theme = request.form.get('theme')
            # FIX: allow 'dark' as a valid theme
            if theme in ['blue', 'red', 'green', 'dark']:
                session['theme'] = theme
                session.modified = True
                flash(f"Theme changed to {theme.capitalize()}!", "info")
            else:
                flash('Invalid theme selected.', 'danger')
    user_theme = session.get('theme', 'blue')
    return render_template('account.html', user=user, user_theme=user_theme)

@app.route('/search_sets', methods=['GET', 'POST'])
def search_sets():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    results = []
    query = ""
    if request.method == 'POST':
        query = request.form.get('query', '').strip().lower()
        if query:
            results = [s for s in user.flashcard_sets if query in s.title.lower()]
    return render_template('search_sets.html', results=results, query=query)

@app.route('/search_within_set/<int:set_id>', methods=['GET', 'POST'])
def search_within_set(set_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    flashcard_set = FlashcardSet.query.get_or_404(set_id)
    if flashcard_set.user_id != session['user_id']:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    results = []
    query = ""
    if request.method == 'POST':
        query = request.form.get('query', '').strip().lower()
        if query:
            results = [
                card for card in flashcard_set.cards
                if query in card.term.lower() or query in card.definition.lower()
            ]
    return render_template('search_within_set.html', flashcard_set=flashcard_set, results=results, query=query)

@app.route('/export_set/<int:set_id>/<string:format>')
def export_set(set_id, format):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    flashcard_set = FlashcardSet.query.get_or_404(set_id)
    if flashcard_set.user_id != session['user_id']:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    if format == 'json':
        data = {
            'title': flashcard_set.title,
            'cards': [
                {'term': card.term, 'definition': card.definition}
                for card in flashcard_set.cards
            ]
        }
        buf = io.BytesIO()
        buf.write(json.dumps(data, indent=2).encode('utf-8'))
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name=f"{flashcard_set.title}.json", mimetype='application/json')
    elif format == 'csv':
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['Term', 'Definition'])
        for card in flashcard_set.cards:
            writer.writerow([card.term, card.definition])
        mem = io.BytesIO()
        mem.write(buf.getvalue().encode('utf-8'))
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name=f"{flashcard_set.title}.csv", mimetype='text/csv')
    else:
        flash('Unsupported export format.')
        return redirect(url_for('dashboard'))

@app.route('/import_set', methods=['GET', 'POST'])
def import_set():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files.get('file')
        format = request.form.get('format')
        title = request.form.get('title', '').strip()
        if not file or not title:
            flash('Please provide a file and a title for the set.')
            return redirect(url_for('import_set'))
        if format == 'json' and file.filename.endswith('.json'):
            data = json.load(file)
            new_set = FlashcardSet(title=title, user_id=session['user_id'])
            db.session.add(new_set)
            db.session.commit()
            for card in data.get('cards', []):
                db.session.add(Flashcard(term=card['term'], definition=card['definition'], set_id=new_set.id))
            db.session.commit()
            flash('Flashcard set imported successfully (JSON).')
            return redirect(url_for('dashboard'))
        elif format == 'csv' and file.filename.endswith('.csv'):
            new_set = FlashcardSet(title=title, user_id=session['user_id'])
            db.session.add(new_set)
            db.session.commit()
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            reader = csv.DictReader(stream)
            for row in reader:
                db.session.add(Flashcard(term=row['Term'], definition=row['Definition'], set_id=new_set.id))
            db.session.commit()
            flash('Flashcard set imported successfully (CSV).')
            return redirect(url_for('dashboard'))
        else:
            flash('Unsupported file format or mismatch.')
            return redirect(url_for('import_set'))
    return render_template('import_set.html')

def update_user_gamification(user):
    today = str(datetime.date.today())
    if not hasattr(user, 'streak'):
        user.streak = 0
        user.last_active = None
    if not hasattr(user, 'points'):
        user.points = 0
    if not hasattr(user, 'badges'):
        user.badges = ""
    if getattr(user, 'last_active', None) != today:
        if user.last_active:
            last = datetime.datetime.strptime(user.last_active, "%Y-%m-%d").date()
            if (datetime.date.today() - last).days == 1:
                user.streak += 1
            else:
                user.streak = 1
        else:
            user.streak = 1
        user.last_active = today
        
@app.before_request
def gamification_before_request():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            update_user_gamification(user)
            db.session.commit()

def add_points_and_badges(user, points_earned):
    user.points = getattr(user, 'points', 0) + points_earned
    badges = set(user.badges.split(',')) if user.badges else set()
    if user.streak >= 7:
        badges.add("7-day streak")
    if user.points >= 100:
        badges.add("100 points")
    if user.points >= 500:
        badges.add("500 points")
    if user.streak >= 30:
        badges.add("30-day streak")
    user.badges = ",".join(badges)
    db.session.commit()

def calculate_achievements(user):
    achievements = set()
    user_sets = [s for s in user.flashcard_sets if s.title != "Python (default)"]
    total_sets = len(user_sets)
    total_cards = sum(len(s.cards) for s in user_sets)
    total_points = getattr(user, 'points', 0)
    streak = getattr(user, 'streak', 0)

    if total_sets >= 1:
        achievements.add("Created your first set")
    if total_sets >= 5:
        achievements.add("Created 5 sets")
    if total_cards >= 20:
        achievements.add("Added 20 cards")
    if total_points >= 100:
        achievements.add("Scored 100 points")
    if total_points >= 500:
        achievements.add("Scored 500 points")
    if streak >= 7:
        achievements.add("7-day streak")
    if streak >= 30:
        achievements.add("30-day streak")
    if getattr(user, 'daily_challenge_completed', False):
        achievements.add("Completed today's daily challenge")
    return list(achievements)

def update_achievements(user):
    achievements = set(calculate_achievements(user))
    user.badges = ",".join(achievements)
    db.session.commit()

def get_user_rank(user_id):
    users = User.query.order_by(User.points.desc()).all()
    for idx, user in enumerate(users, 1):
        if user.id == user_id:
            return idx
    return None

def get_daily_challenge():
    today = str(datetime.date.today())
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.daily_challenge_date != today:
            user.daily_challenge_date = today
            user.daily_challenge_progress = 0
            user.daily_challenge_completed = False
            db.session.commit()
        return {
            'date': user.daily_challenge_date,
            'goal': 10,
            'progress': user.daily_challenge_progress,
            'completed': user.daily_challenge_completed
        }
    else:
        challenge = session.get('daily_challenge')
        if not challenge or challenge.get('date') != today:
            challenge = {
                'date': today,
                'goal': 10,
                'progress': 0,
                'completed': False
            }
            session['daily_challenge'] = challenge
        return challenge

def update_daily_challenge(correct_increment=0):
    today = str(datetime.date.today())
    reward_points = 50  # Points to award for completing daily challenge
    reward_badge = "Daily Challenge Winner"
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.daily_challenge_date != today:
            user.daily_challenge_date = today
            user.daily_challenge_progress = 0
            user.daily_challenge_completed = False
        if not user.daily_challenge_completed:
            user.daily_challenge_progress += correct_increment
            if user.daily_challenge_progress >= 10:
                user.daily_challenge_completed = True
                user.points = getattr(user, 'points', 0) + reward_points
                badges = set(user.badges.split(',')) if user.badges else set()
                badges.add(reward_badge)
                user.badges = ",".join(badges)
                flash(f'🎉 Daily Challenge completed! You earned {reward_points} bonus points and a badge!')
        db.session.commit()
    else:
        challenge = get_daily_challenge()
        if not challenge['completed']:
            challenge['progress'] += correct_increment
            if challenge['progress'] >= challenge['goal']:
                challenge['completed'] = True
                flash('🎉 Daily Challenge completed!')
            session['daily_challenge'] = challenge

@app.route('/set_theme/<theme>')
def set_theme(theme):
    if theme not in ['blue', 'red', 'green', 'dark']:
        flash('Invalid theme.')
        return redirect(request.referrer or url_for('dashboard'))
    session['theme'] = theme
    session.permanent = True  # Ensure session persists
    session.modified = True
    flash(f"Theme changed to {theme.capitalize()}!", "info")
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/review_by_tag/<int:set_id>', methods=['GET', 'POST'])
def review_by_tag(set_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    flashcard_set = FlashcardSet.query.get_or_404(set_id)
    if flashcard_set.user_id != session['user_id']:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    all_tags = set()
    for card in flashcard_set.cards:
        if card.tags:
            all_tags.update([t.strip() for t in card.tags.split(',') if t.strip()])
    selected_tag = request.args.get('tag', '')
    if selected_tag:
        filtered_cards = [card for card in flashcard_set.cards if selected_tag in [t.strip() for t in (card.tags or '').split(',')]]
    else:
        filtered_cards = flashcard_set.cards
    return render_template('review_by_tag.html', flashcard_set=flashcard_set, cards=filtered_cards, all_tags=sorted(all_tags), selected_tag=selected_tag)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

# This program is a Flask web application for flashcard-based 
# learning. It supports user authentication, flashcard set creation, 
# editing, deletion, and review, as well as multiple study/game modes 
# (classic, multiple choice, fill in the blank). The app tracks user 
# progress, streaks, points, badges, and daily challenges, and provides
# a leaderboard. Users can import/export flashcard sets in JSON or 
# CSV format. All user data and gamification stats are stored in a 
# SQLite database. The code is organized into routes for user actions 
# and helper functions for gamification, challenge logic, and data 
# management.
