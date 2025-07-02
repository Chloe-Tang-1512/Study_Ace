import random
import difflib
import json
import os
import gzip
import hashlib
import csv
import datetime
import sys
import platform

if platform.system() == "Windows":
    import msvcrt
else:
    import tty
    import termios

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(stored_password, provided_password):
    return stored_password == hash_password(provided_password)

def load_user_data():
    if os.path.exists("user_data.json.gz"):
        with gzip.open("user_data.json.gz", "rt", encoding="utf-8") as file:
            return json.load(file)
    return {}

def save_user_data(user_data):
    with gzip.open("user_data.json.gz", "wt", encoding="utf-8") as file:
        json.dump(user_data, file, indent=4)

def input_password(prompt="Enter your password: ", mask="*"):
    print(prompt, end="", flush=True)
    password = ""
    if platform.system() == "Windows":
        while True:
            char = msvcrt.getch()
            if char in {b"\r", b"\n"}:
                print()
                break
            elif char == b"\x08":
                if len(password) > 0:
                    password = password[:-1]
                    print("\b \b", end="", flush=True)
            else:
                password += char.decode("utf-8")
                print(mask, end="", flush=True)
    else:
        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setraw(fd)
            while True:
                char = sys.stdin.read(1)
                if char == "\n" or char == "\r":
                    print()
                    break
                elif char == "\x7f":
                    if len(password) > 0:
                        password = password[:-1]
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                else:
                    password += char
                    sys.stdout.write(mask)
                    sys.stdout.flush()
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return password

def display_separator():
    print("=" * 50)

def display_header(title):
    display_separator()
    print(f"{title:^50}")
    display_separator()

def login():
    user_data = load_user_data()
    display_header("Welcome to the Flashcard Program!")
    print("Learn, revise, and master your studies!")
    while True:
        username = input("Enter your username (or type 'new' to create an account): ").strip()
        if username.lower() == "new":
            new_username = input("Enter a new username: ").strip()
            if new_username in user_data:
                print("❌ This username already exists. Please try again.")
            else:
                password = input_password("Enter a password: ").strip()
                hashed_password = hash_password(password)
                user_data[new_username] = {
                    "password": hashed_password,
                    "flashcard_sets": {}
                }
                save_user_data(user_data)
                print(f"✅ Account created successfully! Welcome, {new_username}!")
                return new_username, user_data
        elif username in user_data:
            password = input_password("Enter your password: ").strip()
            stored_hashed_password = user_data[username]["password"]
            if verify_password(stored_hashed_password, password):
                print(f"✅ Welcome back, {username}!")
                return username, user_data
            else:
                print("❌ Incorrect password. Please try again.")
        else:
            print("❌ Username not found. Please try again or type 'new' to create an account.")

def flash_card_game(flash_cards, daily_challenge):
    print("Welcome to the Flash Card Game!")
    print("You will be shown a term, and you need to guess its definition.")
    print("Type 'exit' to quit the game.\n")
    terms = sorted(
        flash_cards["terms"].keys(),
        key=lambda term: (
            flash_cards["terms"][term]["total"] - flash_cards["terms"][term]["correct"]
        ),
        reverse=True,
    )
    score = 0
    total_questions = len(terms)
    for term in terms:
        print(f"Term: {term}")
        user_answer = input("Your definition: ").strip()
        if user_answer.lower() == "exit":
            print("Thanks for playing! Returning to the main menu...\n")
            break
        correct_answer = flash_cards["terms"][term]["definition"]
        similarity = difflib.SequenceMatcher(None, user_answer.lower(), correct_answer.lower()).ratio()
        flash_cards["terms"][term]["total"] += 1
        flash_cards["stats"]["total"] += 1
        if similarity > 0.7:
            print("✅ Correct!\n")
            score += 1
            flash_cards["terms"][term]["correct"] += 1
            flash_cards["stats"]["correct"] += 1
        elif similarity > 0.4:
            print(f"Almost correct! Here's a hint: {correct_answer[:len(correct_answer)//2]}...\n")
        else:
            print(f"❌ Incorrect. The correct definition is: {correct_answer}\n")
    if flash_cards["stats"]["total"] > 0:
        flash_cards["stats"]["percentage"] = (flash_cards["stats"]["correct"] / flash_cards["stats"]["total"]) * 100
    else:
        flash_cards["stats"]["percentage"] = 0.0
    print(f"You answered {score} out of {total_questions} questions correctly!")
    print("You've gone through all the flash cards. Great job!")
    daily_challenge = update_daily_challenge(daily_challenge, score)
    return score

def calculate_user_level(flashcard_sets):
    total_correct = sum(fc["stats"]["correct"] for fc in flashcard_sets.values())
    total_attempts = sum(fc["stats"]["total"] for fc in flashcard_sets.values())
    if total_attempts == 0:
        return "Unranked"
    pct = (total_correct / total_attempts) * 100
    levels = [
        (40, "Beginner"),
        (70, "Intermediate"),
        (90, "Advanced"),
    ]
    for threshold, name in levels:
        if pct <= threshold:
            return name
    return "Expert"

def track_progress(flashcard_set):
    display_header("Progress Report")
    total_terms = len(flashcard_set["terms"])
    learned_terms = sum(1 for t in flashcard_set["terms"].values() if t["correct"] > 0)
    total_attempts = flashcard_set["stats"]["total"]
    correct_answers = flashcard_set["stats"]["correct"]
    accuracy = (correct_answers / total_attempts * 100) if total_attempts else 0
    print(f"Total terms: {total_terms}")
    print(f"Learned terms: {learned_terms}/{total_terms}")
    print(f"Total attempts: {total_attempts}")
    print(f"Correct answers: {correct_answers}")
    print(f"Accuracy: {accuracy:.2f}%")
    print("\nTerms that need more practice:")
    for term, data in flashcard_set["terms"].items():
        if data["total"] > 0 and (data["correct"] / data["total"]) < 0.5:
            print(f"- {term}: {data['correct']}/{data['total']} correct")
    display_separator()

def edit_flashcard_set(flashcard_set):
    while True:
        print("\n Edit Flashcard Set:")
        print("1. Add a new term")
        print("2. Edit an existing term")
        print("3. Return to the main menu")
        choice = input("Enter your choice (1/2/3): ").strip()
        if choice == "1":
            term = input("Enter the new term: ").strip()
            if term in flashcard_set["terms"]:
                print(f"❌ The term '{term}' already exists. Please choose a different term.")
            else:
                definition = input(f"Enter the definition for '{term}': ").strip()
                flashcard_set["terms"][term] = {"definition": definition, "correct": 0, "total": 0}
                print(f"✅ Added: {term} -> {definition}")
        elif choice == "2":
            term = input("Enter the term you want to edit: ").strip()
            if term in flashcard_set["terms"]:
                new_definition = input(f"Enter the new definition for '{term}': ").strip()
                flashcard_set["terms"][term]["definition"] = new_definition
                print(f"✅ Updated: {term} -> {new_definition}")
            else:
                print(f"❌ The term '{term}' does not exist in this flashcard set.")
        elif choice == "3":
            print("Returning to the main menu...\n")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.\n")

def edit_flashcard_set_menu(flashcard_sets, user_data):
    while True:
        print("\nEdit Flashcard Sets Menu:")
        print("1. Edit terms in a flashcard set")
        print("2. Delete a flashcard set")
        print("3. Return to Main Menu")
        choice = input("Enter your choice (1/2/3): ").strip()
        if choice == "1":
            set_name = input("Enter the name of the flashcard set you want to edit: ").strip()
            if set_name in flashcard_sets:
                edit_flashcard_set(flashcard_sets[set_name])
                save_user_data(user_data)
            else:
                print(f"No flashcard set named '{set_name}' found. Please try again.")
        elif choice == "2":
            set_name = input("Enter the name of the flashcard set you want to delete: ").strip()
            if set_name in flashcard_sets:
                if set_name == "Python (default)":
                    print("The default flashcard set cannot be deleted.")
                else:
                    del flashcard_sets[set_name]
                    save_user_data(user_data)
                    print(f"Flashcard set '{set_name}' deleted successfully!")
            else:
                print(f"No flashcard set named '{set_name}' found. Please try again.")
        elif choice == "3":
            print("Returning to the Main Menu...\n")
            break
        else:
            print("Invalid choice. Please enter a valid option.\n")

def update_streak(user_data, username):
    today = datetime.date.today().isoformat()
    streak_data = user_data[username].get("streak", {"last_active": None, "current_streak": 0, "max_streak": 0})
    if streak_data["last_active"] == today:
        return streak_data
    if streak_data["last_active"]:
        last_active_date = datetime.date.fromisoformat(streak_data["last_active"])
        if (datetime.date.today() - last_active_date).days == 1:
            streak_data["current_streak"] += 1
        else:
            streak_data["current_streak"] = 1
    else:
        streak_data["current_streak"] = 1
    streak_data["last_active"] = today
    streak_data["max_streak"] = max(streak_data["max_streak"], streak_data["current_streak"])
    user_data[username]["streak"] = streak_data
    save_user_data(user_data)
    return streak_data

def calculate_badges(user_data, username):
    badges = []
    streak = user_data[username].get("streak", {"current_streak": 0, "max_streak": 0})["current_streak"]
    flashcard_sets = user_data[username]["flashcard_sets"]
    total_correct = sum(fc["stats"]["correct"] for fc in flashcard_sets.values())
    total_attempts = sum(fc["stats"]["total"] for fc in flashcard_sets.values())
    if streak >= 7: badges.append("🔥 7-day streak!")
    if streak >= 30: badges.append("🌟 30-day streak!")
    if total_attempts >= 500: badges.append("🏅 Answered 500 questions!")
    if total_attempts > 0 and (total_correct / total_attempts) >= 0.9: badges.append("🎖️ 90% accuracy!")
    if len(flashcard_sets) >= 10: badges.append("📚 Created 10 flashcard sets!")
    mastered_sets = sum(all(t["correct"] > 0 for t in fc["terms"].values()) for fc in flashcard_sets.values())
    if mastered_sets >= 5: badges.append("🏆 Mastered 5 flashcard sets!")
    return badges

def calculate_achievements(flashcard_sets):
    achievements = []
    total_sets = len(flashcard_sets)
    total_correct = sum(fc["stats"]["correct"] for fc in flashcard_sets.values())
    total_attempts = sum(fc["stats"]["total"] for fc in flashcard_sets.values())
    if total_sets >= 5: achievements.append("🏆 Completed 5 flashcard sets!")
    if total_attempts >= 100: achievements.append("🎯 Answered 100 questions!")
    if total_attempts > 0 and (total_correct / total_attempts) >= 0.8: achievements.append("📈 Achieved 80% or higher accuracy!")
    for set_name, fc in flashcard_sets.items():
        if all(t["correct"] > 0 for t in fc["terms"].values()):
            achievements.append(f"🎓 Mastered all terms in '{set_name}'!")
    total_games_played = sum(fc["stats"]["total"] for fc in flashcard_sets.values())
    if total_games_played >= 50: achievements.append("🎮 Played 50 flashcard games!")
    if total_attempts >= 1000: achievements.append("🏅 Answered 1000 questions!")
    return achievements

def manage_account(username, user_data):
    while True:
        print("\nAccount Management:")
        print("1. View account details")
        print("2. Edit account details")
        print("3. Delete account")
        print("4. Return to the main menu")
        choice = input("Enter your choice (1/2/3/4): ").strip()
        if choice == "1":
            flashcard_sets = user_data[username]["flashcard_sets"]
            user_level = calculate_user_level(flashcard_sets)
            achievements = calculate_achievements(flashcard_sets)
            streak_data = update_streak(user_data, username)
            badges = calculate_badges(user_data, username)
            print(f"\nAccount Details for '{username}':")
            print(f"- Level: {user_level}")
            print(f"- Number of flashcard sets: {len(flashcard_sets)}")
            print("- Flashcard sets:")
            for set_name in flashcard_sets:
                print(f"  - {set_name}")
            print(f"- Current streak: {streak_data['current_streak']} days")
            print(f"- Max streak: {streak_data['max_streak']} days")
            print("\nAchievements:")
            for achievement in achievements:
                print(f"- {achievement}")
            print("\nBadges:")
            for badge in badges:
                print(f"- {badge}")
            print()
        elif choice == "2":
            print("\nEdit Account Details:")
            print("1. Change username")
            print("2. Change password")
            edit_choice = input("Enter your choice (1/2): ").strip()
            if edit_choice == "1":
                new_username = input("Enter your new username: ").strip()
                if new_username in user_data:
                    print("❌ This username is already taken. Please try again.")
                else:
                    user_data[new_username] = user_data.pop(username)
                    username = new_username
                    save_user_data(user_data)
                    print(f"✅ Your username has been updated to '{new_username}'.")
            elif edit_choice == "2":
                new_password = input_password("Enter your new password: ").strip()
                user_data[username]["password"] = hash_password(new_password)
                save_user_data(user_data)
                print("✅ Your password has been updated successfully.")
            else:
                print("❌ Invalid choice. Please enter 1 or 2.\n")
        elif choice == "3":
            confirm = input("Are you sure you want to delete your account? This action cannot be undone (yes/no): ").strip().lower()
            if confirm == "yes":
                password = input_password("Enter your password to confirm account deletion: ").strip()
                if verify_password(user_data[username]["password"], password):
                    del user_data[username]
                    save_user_data(user_data)
                    print("✅ Your account has been deleted. Goodbye!")
                    exit()
                else:
                    print("❌ Account deletion canceled. Incorrect password.")
            else:
                print("❌ Account deletion canceled.")
        elif choice == "4":
            print("Returning to the main menu...\n")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, 3, or 4.\n")

def export_flashcard_set(flashcard_set, file_format="json"):
    set_name = flashcard_set.get("name", "flashcard_set")
    if file_format.lower() == "json":
        file_name = f"{set_name}.json"
        with open(file_name, "w", encoding="utf-8") as file:
            json.dump(flashcard_set, file, indent=4)
        print(f"Flashcard set exported as {file_name}")
    elif file_format.lower() == "csv":
        file_name = f"{set_name}.csv"
        with open(file_name, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Term", "Definition", "Correct", "Total"])
            for term, data in flashcard_set["terms"].items():
                writer.writerow([term, data["definition"], data["correct"], data["total"]])
        print(f"Flashcard set exported as {file_name}")
    else:
        print("Unsupported file format. Please choose 'json' or 'csv'.")

def import_flashcard_set(file_name):
    if file_name.endswith(".json"):
        with open(file_name, "r", encoding="utf-8") as file:
            flashcard_set = json.load(file)
        print(f"Flashcard set imported from {file_name}")
        return flashcard_set
    elif file_name.endswith(".csv"):
        flashcard_set = {"terms": {}, "stats": {"correct": 0, "total": 0, "percentage": 0.0}}
        with open(file_name, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                term = row["Term"]
                definition = row["Definition"]
                correct = int(row["Correct"])
                total = int(row["Total"])
                flashcard_set["terms"][term] = {"definition": definition, "correct": correct, "total": total}
        print(f"Flashcard set imported from {file_name}")
        return flashcard_set
    else:
        print("Unsupported file format. Please provide a '.json' or '.csv' file.")
        return None

def manage_flashcard_import_export(flashcard_sets):
    while True:
        print("\nImport/Export Flashcard Sets:")
        print("1. Export a flashcard set")
        print("2. Import a flashcard set")
        print("3. Return to the main menu")
        choice = input("Enter your choice (1/2/3): ").strip()
        if choice == "1":
            set_name = input("Enter the name of the flashcard set to export: ").strip()
            if set_name in flashcard_sets:
                file_format = input("Enter the file format (json/csv): ").strip().lower()
                export_flashcard_set(flashcard_sets[set_name], file_format)
            else:
                print(f"No flashcard set named '{set_name}' found. Please try again.")
        elif choice == "2":
            file_name = input("Enter the file name to import (with extension): ").strip()
            imported_set = import_flashcard_set(file_name)
            if imported_set:
                set_name = input("Enter a name for the imported flashcard set: ").strip()
                if set_name in flashcard_sets:
                    print(f"A flashcard set named '{set_name}' already exists. Please choose a different name.")
                else:
                    flashcard_sets[set_name] = imported_set
                    print(f"Flashcard set '{set_name}' imported successfully!")
        elif choice == "3":
            print("Returning to the main menu...\n")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.\n")

def generate_daily_challenge():
    today = datetime.date.today()
    challenge = {
        "date": today.isoformat(),
        "goal": 10,
        "progress": 0,
        "completed": False
    }
    return challenge

def update_daily_challenge(challenge, correct_answers):
    if correct_answers is None:
        correct_answers = 0
    if challenge["completed"]:
        print("Today's challenge is already completed!")
        return challenge
    challenge["progress"] += correct_answers
    if challenge["progress"] >= challenge["goal"]:
        challenge["completed"] = True
        print(f"Congratulations! You completed today's challenge: Answer {challenge['goal']} questions correctly!")
    else:
        print(f"Daily Challenge Progress: {challenge['progress']}/{challenge['goal']} correct answers.")
    return challenge

def display_daily_challenge(challenge):
    print("\nDaily Challenge:")
    print(f"- Goal: Answer {challenge['goal']} questions correctly")
    print(f"- Progress: {challenge['progress']}/{challenge['goal']}")
    print(f"- Completed: {'Yes' if challenge['completed'] else 'No'}\n")

def calculate_leaderboard(user_data):
    leaderboard = []
    for username, data in user_data.items():
        flashcard_sets = data.get("flashcard_sets", {})
        total_correct = sum(flashcard_sets[set_name]["stats"]["correct"] for set_name in flashcard_sets)
        total_attempts = sum(flashcard_sets[set_name]["stats"]["total"] for set_name in flashcard_sets)
        accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
        level = calculate_user_level(flashcard_sets)
        leaderboard.append({
            "username": username,
            "accuracy": accuracy,
            "level": level,
            "total_correct": total_correct,
            "total_attempts": total_attempts
        })
    leaderboard.sort(key=lambda x: x["accuracy"], reverse=True)
    print("\nLeaderboard:")
    print(f"{'Rank':<5} {'Username':<15} {'Level':<12} {'Accuracy (%)':<12} {'Correct':<10} {'Attempts':<10}")
    for rank, entry in enumerate(leaderboard, start=1):
        print(f"{rank:<5} {entry['username']:<15} {entry['level']:<12} {entry['accuracy']:<12.2f} {entry['total_correct']:<10} {entry['total_attempts']:<10}")
    print()
    
def search_flashcard_set(flashcard_set):
    query = input("Enter a term or definition to search for: ").strip().lower()
    results = []
    for term, data in flashcard_set["terms"].items():
        if query in term.lower() or query in data["definition"].lower():
            results.append((term, data["definition"]))
    if results:
        print("\nSearch Results:")
        for term, definition in results:
            print(f"- {term}: {definition}")
    else:
        print("No matching terms or definitions found.")

def revision_mode(flash_cards, daily_challenge):
    print("Welcome to Revision Mode!")
    print("You will be shown a term, and you can review its definition.")
    print("Type 'exit' to quit revision mode.\n")
    terms = list(flash_cards["terms"].keys())
    random.shuffle(terms)
    score = 0
    for term in terms:
        print(f"Term: {term}")
        user_input = input("Press Enter to reveal the definition or type 'exit' to quit: ").strip()
        if user_input.lower() == "exit":
            break
        print(f"Definition: {flash_cards['terms'][term]['definition']}\n")
        # Count each term reviewed as a partial success (0.5)
        flash_cards["terms"][term]["total"] += 1
        flash_cards["stats"]["total"] += 1
        flash_cards["terms"][term]["correct"] += 0.5
        flash_cards["stats"]["correct"] += 0.5
        score += 1
    
    # Update overall statistics
    if flash_cards["stats"]["total"] > 0:
        flash_cards["stats"]["percentage"] = (flash_cards["stats"]["correct"] / flash_cards["stats"]["total"]) * 100
    
    print(f"Revision completed! You reviewed {score} terms.\n")
    return update_daily_challenge(daily_challenge, score // 2)  # Count half points for revision

def quiz_mode(flash_cards, daily_challenge):
    print("Welcome to Quiz Mode!")
    print("You will be shown a term and four possible definitions.")
    print("Type the number corresponding to your answer or 'exit' to quit the quiz.\n")
    terms = list(flash_cards["terms"].keys())
    random.shuffle(terms)
    score = 0
    total_questions = len(terms)
    for term in terms:
        print(f"Term: {term}")
        correct_answer = flash_cards["terms"][term]["definition"]
        options = [correct_answer]
        while len(options) < 4:
            random_term = random.choice(terms)
            random_definition = flash_cards["terms"][random_term]["definition"]
            if random_definition not in options:
                options.append(random_definition)
        random.shuffle(options)
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        user_input = input("Your choice (1/2/3/4 or 'exit'): ").strip()
        if user_input.lower() == "exit":
            print("Exiting Quiz Mode...\n")
            break
        if user_input.isdigit() and 1 <= int(user_input) <= 4:
            selected_option = options[int(user_input) - 1]
            flash_cards["terms"][term]["total"] += 1
            flash_cards["stats"]["total"] += 1
            if selected_option == correct_answer:
                print("Correct!\n")
                score += 1
                flash_cards["terms"][term]["correct"] += 1
                flash_cards["stats"]["correct"] += 1
            else:
                print(f"Incorrect. The correct answer was: {correct_answer}\n")
        else:
            print("Invalid input. Please enter a number between 1 and 4 or 'exit'.\n")
    # Update overall statistics
    if flash_cards["stats"]["total"] > 0:
        flash_cards["stats"]["percentage"] = (flash_cards["stats"]["correct"] / flash_cards["stats"]["total"]) * 100
    
    print(f"Quiz completed! You answered {score} out of {total_questions} questions correctly.\n")
    return update_daily_challenge(daily_challenge, score)

def fill_in_the_blank_mode(flash_cards, daily_challenge):
    print("Welcome to Fill in the Blank Mode!")
    print("You will be shown a term and a definition with missing words, and you need to fill in the blanks.")
    print("Type 'exit' to quit this mode.\n")
    terms = list(flash_cards["terms"].keys())
    random.shuffle(terms)
    score = 0
    total_questions = len(terms)
    for term in terms:
        definition = flash_cards["terms"][term]["definition"]
        words = definition.split()
        if len(words) < 3:
            continue
        blank_index = random.randint(0, len(words) - 1)
        blanked_definition = words[:]
        blanked_definition[blank_index] = "____"
        print(f"Term: {term}")
        print(f"Definition: {' '.join(blanked_definition)}")
        user_input = input("Fill in the blank: ").strip()
        if user_input.lower() == "exit":
            print("Exiting Fill in the Blank Mode...\n")
            break
        correct_word = words[blank_index]
        if user_input.lower() == correct_word.lower():
            print("Correct!\n")
            score += 1
            flash_cards["terms"][term]["total"] += 1
            flash_cards["stats"]["total"] += 1
            flash_cards["terms"][term]["correct"] += 1
            flash_cards["stats"]["correct"] += 1
        else:
            print(f"Incorrect. The correct word was: {correct_word}\n")
            flash_cards["terms"][term]["total"] += 1
            flash_cards["stats"]["total"] += 1
    
    # Update overall statistics
    if flash_cards["stats"]["total"] > 0:
        flash_cards["stats"]["percentage"] = (flash_cards["stats"]["correct"] / flash_cards["stats"]["total"]) * 100
    
    print(f"Fill in the Blank Mode completed! You answered {score} out of {total_questions} questions correctly.\n")
    return update_daily_challenge(daily_challenge, score)

def flashcard_games_menu(flashcard_sets, daily_challenge):
    while True:
        print("\nFlashcard Games Menu:")
        print("1. Play Flashcard Game")
        print("2. Revision Mode")
        print("3. Quiz Mode")
        print("4. Fill in the Blank Mode")
        print("5. Return to Main Menu")
        choice = input("Enter your choice (1-5): ").strip()
        if choice == "1":
            set_name = input("Enter the name of the flashcard set you want to play with: ").strip()
            if set_name in flashcard_sets:
                flash_card_game(flashcard_sets[set_name], daily_challenge)
            else:
                print(f"No flashcard set named '{set_name}' found. Please try again.")
        elif choice == "2":
            set_name = input("Enter the name of the flashcard set you want to review: ").strip()
            if set_name in flashcard_sets:
                revision_mode(flashcard_sets[set_name], daily_challenge)
            else:
                print(f"No flashcard set named '{set_name}' found. Please try again.")
        elif choice == "3":
            set_name = input("Enter the name of the flashcard set you want to quiz with: ").strip()
            if set_name in flashcard_sets:
                quiz_mode(flashcard_sets[set_name], daily_challenge)
            else:
                print(f"No flashcard set named '{set_name}' found. Please try again.")
        elif choice == "4":
            set_name = input("Enter the name of the flashcard set you want to use for Fill in the Blank Mode: ").strip()
            if set_name in flashcard_sets:
                fill_in_the_blank_mode(flashcard_sets[set_name], daily_challenge)
            else:
                print(f"No flashcard set named '{set_name}' found. Please try again.")
        elif choice == "5":
            print("Returning to the Main Menu...\n")
            break
        else:
            print("Invalid choice. Please enter a valid option.\n")

def main_menu():
    username, user_data = login()
    flashcard_sets = user_data[username]["flashcard_sets"]
    daily_challenge = generate_daily_challenge()
    if "Python (default)" not in flashcard_sets:
        flashcard_sets["Python (default)"] = {
            "category": "Programming",
            "terms": {
                "Python": {"definition": "A high-level programming language.", "correct": 0, "total": 0},
                "Variable": {"definition": "A storage location paired with an associated symbolic name.", "correct": 0, "total": 0},
                "Function": {"definition": "A block of reusable code that performs a specific task.", "correct": 0, "total": 0},
                "Loop": {"definition": "A programming construct that repeats a block of code.", "correct": 0, "total": 0},
            },
            "stats": {"correct": 0, "total": 0, "percentage": 0.0}
        }
        save_user_data(user_data)
    while True:
        user_level = calculate_user_level(flashcard_sets)
        display_header(f"Main Menu (Logged in as: {username} - Level: {user_level})")
        print("1. Create a new flashcard set")
        print("2. View available flashcard sets")
        print("3. Edit or Delete a flashcard set")
        print("4. Flashcard Games")
        print("5. View progress")
        print("6. View Daily Challenge")
        print("7. View Leaderboard")
        print("8. Search within a flashcard set")
        print("9. Import/Export flashcard sets")
        print("10. Manage account")
        print("11. Save and Exit")
        display_separator()
        choice = input("Enter your choice (1-11): ").strip()
        os.system('cls' if os.name == 'nt' else 'clear')
        if choice == "1":
            set_name = input("Enter a name for your new flashcard set: ").strip()
            if set_name in flashcard_sets:
                print(f"A flashcard set named '{set_name}' already exists. Please choose a different name.")
            else:
                category = input("Enter a category for this flashcard set (e.g., Math, Science, History): ").strip()
                flashcard_sets[set_name] = {
                    "category": category,
                    "terms": {},
                    "stats": {"correct": 0, "total": 0, "percentage": 0.0}
                }
                save_user_data(user_data)
                print(f"Flashcard set '{set_name}' created successfully under the category '{category}'!")
                display_separator()
                while True:
                    term = input("Enter a term (or type 'done' to finish adding terms): ").strip()
                    if term.lower() == "done":
                        print(f"Finished adding terms to '{set_name}'.")
                        break
                    if term in flashcard_sets[set_name]["terms"]:
                        print(f"The term '{term}' already exists. Please enter a different term.")
                    else:
                        definition = input(f"Enter the definition for '{term}': ").strip()
                        flashcard_sets[set_name]["terms"][term] = {"definition": definition, "correct": 0, "total": 0}
                        save_user_data(user_data)
                        print(f"Added: {term} -> {definition}")
                        display_separator()
        elif choice == "2":
            print("\nView Flashcard Sets:")
            print("1. View all flashcard sets")
            print("2. View flashcard sets by category")
            view_choice = input("Enter your choice (1/2): ").strip()
            if view_choice == "1":
                print("\nAvailable Flashcard Sets:")
                for set_name, flash_cards in flashcard_sets.items():
                    correct = flash_cards["stats"]["correct"]
                    total = flash_cards["stats"]["total"]
                    percentage = flash_cards["stats"]["percentage"]
                    category = flash_cards.get("category", "Uncategorized")
                    print(f"- {set_name} (Category: {category}): {correct}/{total} correct ({percentage:.2f}%)")
                print()
            elif view_choice == "2":
                categories = set(flash_cards.get("category", "Uncategorized") for flash_cards in flashcard_sets.values())
                print("\nAvailable Categories:")
                for category in categories:
                    print(f"- {category}")
                selected_category = input("Enter the category you want to view: ").strip()
                print(f"\nFlashcard Sets in Category '{selected_category}':")
                for set_name, flash_cards in flashcard_sets.items():
                    if flash_cards.get("category", "Uncategorized") == selected_category:
                        correct = flash_cards["stats"]["correct"]
                        total = flash_cards["stats"]["total"]
                        percentage = flash_cards["stats"]["percentage"]
                        print(f"- {set_name}: {correct}/{total} correct ({percentage:.2f}%)")
                print()
            else:
                print("Invalid choice. Returning to the main menu.\n")
        elif choice == "3":
            edit_flashcard_set_menu(flashcard_sets, user_data)
        elif choice == "4":
            flashcard_games_menu(flashcard_sets, daily_challenge)
        elif choice == "5":
            print("\nView Progress:")
            print("1. View progress for all flashcard sets")
            print("2. View progress for a specific flashcard set")
            progress_choice = input("Enter your choice (1/2): ").strip()
            if progress_choice == "1":
                print("\nProgress for All Flashcard Sets:")
                for set_name, flashcard_set in flashcard_sets.items():
                    print(f"\nFlashcard Set: {set_name}")
                    track_progress(flashcard_set)
            elif progress_choice == "2":
                set_name = input("Enter the name of the flashcard set: ").strip()
                if set_name in flashcard_sets:
                    print(f"\nProgress for Flashcard Set: {set_name}")
                    track_progress(flashcard_sets[set_name])
                else:
                    print(f"No flashcard set named '{set_name}' found. Please try again.")
            else:
                print("Invalid choice. Returning to the main menu.\n")
        elif choice == "6":
            display_daily_challenge(daily_challenge)
        elif choice == "7":
            calculate_leaderboard(load_user_data())
        elif choice == "8":
            set_name = input("Enter the name of the flashcard set you want to search in: ").strip()
            if set_name in flashcard_sets:
                search_flashcard_set(flashcard_sets[set_name])
            else:
                print(f"No flashcard set named '{set_name}' found. Please try again.")
        elif choice == "9":
            manage_flashcard_import_export(flashcard_sets)
        elif choice == "10":
            manage_account(username, user_data)
        elif choice == "11":
            user_data[username]["flashcard_sets"] = flashcard_sets
            save_user_data(user_data)
            print("Your progress has been saved. Goodbye!")
            break
        else:
            print("Invalid choice. Please enter a valid option.\n")
    os.system('cls' if os.name == 'nt' else 'clear')
    exit()

if __name__ == "__main__":
    main_menu()

# This program is a comprehensive flashcard management and learning system designed to help users create, manage, and study flashcards effectively. 
# It includes features for user authentication, flashcard set creation, editing, and deletion, as well as various game modes for studying. 
# Below is a detailed breakdown of the program's functionality:

# 1. **User Authentication**:
#    - Users can log in with a username and password or create a new account.
#    - Passwords are securely hashed using SHA-256 before being stored.
#    - User data, including flashcard sets and progress, is saved in a compressed JSON file (`user_data.json.gz`).

# 2. **Flashcard Management**:
#    - Users can create flashcard sets, add terms and definitions, and edit or delete existing sets.
#    - Flashcard sets are categorized, and users can view sets by category or as a complete list.
#    - Each flashcard set tracks statistics such as the number of correct answers, total attempts, and accuracy percentage.

# 3. **Game Modes**:
#    - The program offers four game modes to help users study:
#      - **Flashcard Game**: Users guess definitions for terms, with priority given to terms they struggle with.
#      - **Revision Mode**: Users review terms and definitions without affecting their stats.
#      - **Quiz Mode**: A multiple-choice quiz where users select the correct definition for a term.
#      - **Fill in the Blank Mode**: Users fill in missing words in definitions.
#    - Each game mode updates the user's progress and contributes to daily challenges.

# 4. **Daily Challenges**:
#    - A daily challenge is generated each day, encouraging users to answer a specific number of questions correctly.
#    - Progress toward the challenge is tracked across all game modes.

# 5. **Progress Tracking**:
#    - Users can view detailed progress reports for individual flashcard sets or all sets combined.
#    - Reports include statistics such as total terms, learned terms, total attempts, correct answers, and accuracy.

# 6. **Achievements and Badges**:
#    - The program calculates achievements and badges based on user activity, such as completing flashcard sets, maintaining streaks, and achieving high accuracy.
#    - Examples include "7-day streak," "Answered 500 questions," and "Mastered 5 flashcard sets."

# 7. **Leaderboard**:
#    - A leaderboard ranks users based on their accuracy percentage and displays their level, total correct answers, and total attempts.

# 8. **Import/Export**:
#    - Users can export flashcard sets to JSON or CSV files and import sets from these formats.

# 9. **Account Management**:
#    - Users can view account details, including their level, streaks, achievements, and badges.
#    - They can also change their username or password or delete their account.

# 10. **Technical Details**:
#     - The program uses cross-platform password masking for secure input.
#     - Data is saved and loaded efficiently using gzip compression.
#     - The terminal is cleared between actions for a clean user interface.

# Overall, this program provides a robust and engaging platform for learning and mastering any subject through flashcards. It combines effective study techniques with gamification elements to keep users motivated and track their progress over time.