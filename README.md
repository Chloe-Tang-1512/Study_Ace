# Study Ace

Study Ace is a comprehensive flashcard-based learning platform with both a web (Flask) and terminal (Python) version. It helps users create, manage, and study flashcards, track progress, earn achievements, and compete on a leaderboard.

---

## Features

### Web Version (`web_flashcards/app.py`)
- **User Authentication:** Sign up, log in, change password, and manage account.
- **Flashcard Management:** Create, edit, delete, import, and export flashcard sets.
- **Study Modes:** Classic, multiple choice, and fill-in-the-blank games.
- **Progress Tracking:** View stats, streaks, and achievements.
- **Daily Challenges:** Complete daily goals for bonus points and badges.
- **Leaderboard:** See your rank and compare with other users.
- **Themes:** Choose between blue, red, green, or dark themes for a personalized look.
- **Gamification:** Earn badges and level up based on your points.
- **Tagging & Filtering:** Add tags to flashcards and review by tag.
- **PWA Support:** Installable as a Progressive Web App for offline use.

### Terminal Version (`flashcards.py`)
- **User Authentication:** Secure login and account creation with password hashing.
- **Flashcard Management:** Create, edit, delete, import, and export sets (JSON/CSV).
- **Game Modes:** Flashcard game, revision, multiple choice quiz, fill-in-the-blank.
- **Progress Tracking:** Detailed stats and accuracy for each set.
- **Achievements & Badges:** Earned for streaks, accuracy, and milestones.
- **Daily Challenge:** Encourages daily study habits.
- **Leaderboard:** Ranks users by accuracy and level.
- **Cross-platform:** Works on Windows, macOS, and Linux.

---

## Getting Started

### Web Version

1. **Install dependencies:**
    ```bash
    pip install flask flask_sqlalchemy werkzeug
    ```

2. **Run the app:**
    ```bash
    python web_flashcards/app.py
    ```

3. **Open your browser:**  
   Go to `http://127.0.0.1:5000/`

### Terminal Version

1. **Run the program:**
    ```bash
    python flashcards.py
    ```

2. **Follow the prompts:**  
   Create an account or log in, then use the menu to manage flashcards and play games.

---

## File Structure

```
web_flashcards/
    app.py
    templates/
    static/
flashcards.py
README.md
requirements.txt
```

---

## Data Storage

- **Web version:** Uses SQLite database (`flashcards.db`) by default. For online/cloud use, switch to PostgreSQL or MySQL.
- **Terminal version:** Stores user data in a compressed JSON file (`user_data.json.gz`).

---

## Deployment

- For local use, follow the steps above.
- For online deployment, use a platform like [Render](https://render.com) or [Railway](https://railway.app) and a managed database (PostgreSQL/MySQL).
- Update `SQLALCHEMY_DATABASE_URI` in `app.py` for cloud database usage.

---

## Contributing

Contributions are welcome!  
If you have suggestions, bug fixes, or want to add features, feel free to open an issue or submit a pull request.

---

## License

This project is for educational use.  
Feel free to modify and extend for your own learning!

---

## Credits

Created by Chloe Tang.

---
