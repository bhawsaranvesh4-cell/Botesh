import json
import os
import logging
import random
import string
from telegram import (
    Update, Poll, KeyboardButton,
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, CallbackQueryHandler, filters
)

from telegram.ext import PollAnswerHandler

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7226957526:AAFlnED39YoA-cxQEKfLT69CI8mhvfBLu7M")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUIZ_NAME, WAIT_FOR_POLL, WAIT_FOR_IMAGE, WAIT_FOR_SHOUT_MESSAGE = range(4)

QUIZ_FILE = "quiz.json"
TEAM_FILE = "teams.json"
ASSIGN_FILE = "team_assignments.json"
BATTLE_FILE = "battles.json"

def load_quizzes():
    if not os.path.exists(QUIZ_FILE):
        return {}
    with open(QUIZ_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_quizzes(data):
    with open(QUIZ_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_teams():
    if not os.path.exists(TEAM_FILE):
        return {}
    with open(TEAM_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_teams(data):
    with open(TEAM_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_team_assignments():
    if not os.path.exists(ASSIGN_FILE):
        return {}
    with open(ASSIGN_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_team_assignments(data):
    with open(ASSIGN_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_stars():
    if not os.path.exists("stars.json"):
        return {}
    with open("stars.json", "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_stars(data):
    with open("stars.json", "w") as f:
        json.dump(data, f, indent=2)

def load_battles():
    if not os.path.exists(BATTLE_FILE):
        return {}
    with open(BATTLE_FILE, "r") as f:
        try:
            data = json.load(f)
            # Convert lists back to sets
            for battle_id, battle_data in data.items():
                if 'used_codes' in battle_data and isinstance(battle_data['used_codes'], list):
                    battle_data['used_codes'] = set(battle_data['used_codes'])
                if 'announced_questions' in battle_data and isinstance(battle_data['announced_questions'], list):
                    battle_data['announced_questions'] = set(battle_data['announced_questions'])
                # Handle question_messages attempted_users
                if 'question_messages' in battle_data:
                    for chat_id, msg_data in battle_data['question_messages'].items():
                        if 'attempted_users' in msg_data and isinstance(msg_data['attempted_users'], list):
                            msg_data['attempted_users'] = set(msg_data['attempted_users'])
                # Handle initiator_next_presses conversion back to sets
                if 'initiator_next_presses' in battle_data:
                    for question_idx, user_list in battle_data['initiator_next_presses'].items():
                        if isinstance(user_list, list):
                            battle_data['initiator_next_presses'][question_idx] = set(user_list)
                        elif not isinstance(user_list, set):
                            battle_data['initiator_next_presses'][question_idx] = set()
            return data
        except json.JSONDecodeError:
            return {}

def save_battles(data):
    # Convert sets to lists for JSON serialization
    serializable_data = {}
    for battle_id, battle_data in data.items():
        serializable_battle = battle_data.copy()
        if 'used_codes' in serializable_battle and isinstance(serializable_battle['used_codes'], set):
            serializable_battle['used_codes'] = list(serializable_battle['used_codes'])
        if 'announced_questions' in serializable_battle and isinstance(serializable_battle['announced_questions'], set):
            serializable_battle['announced_questions'] = list(serializable_battle['announced_questions'])
        # Handle question_messages attempted_users
        if 'question_messages' in serializable_battle:
            for chat_id, msg_data in serializable_battle['question_messages'].items():
                if 'attempted_users' in msg_data and isinstance(msg_data['attempted_users'], set):
                    msg_data['attempted_users'] = list(msg_data['attempted_users'])
        # Handle initiator_next_presses sets
        if 'initiator_next_presses' in serializable_battle:
            for question_idx, user_set in serializable_battle['initiator_next_presses'].items():
                if isinstance(user_set, set):
                    serializable_battle['initiator_next_presses'][question_idx] = list(user_set)
        serializable_data[battle_id] = serializable_battle

    with open(BATTLE_FILE, "w") as f:
        json.dump(serializable_data, f, indent=2)

user_quizzes = load_quizzes()
teams = load_teams()
team_assignments = load_team_assignments()
stars_data = load_stars()
battles_data = load_battles() # Load battles from file
authorized_users = set()

def get_main_menu():
    return ReplyKeyboardRemove()

def track_active_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Helper function to track active chats"""
    if not hasattr(context, 'bot_data'):
        context.bot_data = {}
    if 'active_chats' not in context.bot_data:
        context.bot_data['active_chats'] = set()
    context.bot_data['active_chats'].add(update.effective_chat.id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Track active chats
    if not hasattr(context, 'bot_data'):
        context.bot_data = {}
    if 'active_chats' not in context.bot_data:
        context.bot_data['active_chats'] = set()

    # Initialize bot_data if needed
    if not hasattr(context, 'bot_data'):
        context.bot_data = {}
    if 'battles' not in context.bot_data:
        context.bot_data['battles'] = battles_data.copy()

    context.bot_data['active_chats'].add(update.effective_chat.id)

    await update.message.reply_text("👋 Welcome! Use official code to unlock bot .", reply_markup=get_main_menu())

async def unlock_quiz_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    authorized_users.add(user_id)
    
    # Track active chats
    if not hasattr(context, 'bot_data'):
        context.bot_data = {}
    if 'active_chats' not in context.bot_data:
        context.bot_data['active_chats'] = set()
    context.bot_data['active_chats'].add(update.effective_chat.id)
    
    await update.message.reply_text("🔓 Access granted!\n You are now authorised as an admin ✅", reply_markup=get_main_menu())

async def create_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in authorized_users:
        await update.message.reply_text("🔒 You need authorization to create quizzes. Use code first.")
        return ConversationHandler.END
    await update.message.reply_text("📝 What will be the name of your new quiz?")
    return QUIZ_NAME

async def receive_quiz_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    quiz_name = update.message.text.strip()
    if not quiz_name:
        await update.message.reply_text("⚠ Quiz name can't be empty.")
        return QUIZ_NAME
    context.user_data["quiz_name"] = quiz_name
    user_quizzes.setdefault(user_id, {})
    user_quizzes[user_id].setdefault(quiz_name, [])
    save_quizzes(user_quizzes)
    await update.message.reply_text("📩 Now send a *quiz-type poll* (anonymous off).")
    return WAIT_FOR_POLL

async def receive_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll = update.message.poll if update.message else None
    if not poll:
        await update.message.reply_text("⚠ Invalid poll.")
        return WAIT_FOR_POLL
    if poll.type != Poll.QUIZ or poll.is_anonymous:
        await update.message.reply_text("⚠ Only *non-anonymous* quiz-type polls are accepted.")
        return WAIT_FOR_POLL

    user_id = str(update.effective_user.id)
    quiz_name = context.user_data.get("quiz_name")
    if not quiz_name:
        await update.message.reply_text("⚠ Quiz name missing.")
        return ConversationHandler.END

    question_data = {
        "question": poll.question,
        "options": [opt.text for opt in poll.options],
        "correct_option_id": poll.correct_option_id,
        "image": None,
    }

    user_quizzes[user_id][quiz_name].append(question_data)
    context.user_data["last_question"] = question_data
    save_quizzes(user_quizzes)

    await update.message.reply_text(
        "📸 Send an image for this question or use /skip to continue without image.\n"
        "You can also use /undo to remove last question.",
        reply_markup=get_main_menu()
    )
    return WAIT_FOR_IMAGE

async def receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "last_question" not in context.user_data:
        await update.message.reply_text("⚠️ No question to attach image.")
        return WAIT_FOR_POLL

    photo = update.message.photo[-1]
    file_id = photo.file_id
    context.user_data["last_question"]["image"] = file_id

    user_id = str(update.effective_user.id)
    quiz_name = context.user_data["quiz_name"]
    user_quizzes[user_id][quiz_name][-1] = context.user_data["last_question"]
    save_quizzes(user_quizzes)

    await update.message.reply_text("✅ Image attached. Send next poll or use /end to finish.")
    return WAIT_FOR_POLL

async def skip_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⭐ Skipped image. Send next poll or use /end to finish.")
    return WAIT_FOR_POLL

async def undo_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    quiz_name = context.user_data.get("quiz_name")
    if quiz_name and user_quizzes.get(user_id, {}).get(quiz_name):
        user_quizzes[user_id][quiz_name].pop()
        save_quizzes(user_quizzes)
        await update.message.reply_text("⚠ Last question removed.")
    else:
        await update.message.reply_text("⚠️ Nothing to undo.")
    return WAIT_FOR_POLL

async def end_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 Quiz saved!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠ Quiz creation cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def poll_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 To send a quiz:\n"
        "1. Tap 📎 or ➕ icon.\n"
        "2. Select *Poll*.\n"
        "3. Set *Poll Type* to 'Quiz'.\n"
        "4. Turn OFF 'Anonymous'.\n"
        "5. Add options and select correct one.\n"
        "6. Send it here.",
        reply_markup=get_main_menu()
    )

async def show_my_quizzes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    quizzes = user_quizzes.get(user_id, {})

    if not quizzes:
        await update.message.reply_text("📭 You haven't created any quizzes yet.", reply_markup=get_main_menu())
        return

    keyboard = [
        [InlineKeyboardButton(text=name, callback_data=f"select_quiz:{name}")]
        for name in quizzes
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("📚 Your Quizzes:", reply_markup=reply_markup)

async def handle_quiz_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("select_quiz:"):
        quiz_name = data.split(":", 1)[1]
        context.user_data["selected_quiz"] = quiz_name

        buttons = [
            [
                InlineKeyboardButton("📤 Give Quiz", callback_data="give_quiz"),
                InlineKeyboardButton("🗑️ Delete Quiz", callback_data="delete_quiz")
            ],
            [
                InlineKeyboardButton("📄 See Quiz", callback_data="see_quiz")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        await query.edit_message_text(
            text=f"📌 What do you want to do with *{quiz_name}*?",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

async def handle_quiz_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    quiz_name = context.user_data.get("selected_quiz")

    if not quiz_name:
        await query.edit_message_text("⚠️ No quiz selected.")
        return

    questions = user_quizzes.get(user_id, {}).get(quiz_name, [])

    if query.data == "see_quiz":
        if not questions:
            await query.edit_message_text("📭 No questions in this quiz.")
            return
        lines = [f"📖 *{quiz_name}* contains {len(questions)} questions:\n"]
        for i, q in enumerate(questions, 1):
            lines.append(f"{i}. {q['question']}")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")

    elif query.data == "delete_quiz":
        del user_quizzes[user_id][quiz_name]
        save_quizzes(user_quizzes)
        await query.edit_message_text(f"🗑️ Quiz *{quiz_name}* deleted.", parse_mode="Markdown")

    elif query.data == "give_quiz":
        if not questions:
            await query.edit_message_text("📭 This quiz has no questions.")
            return

        context.user_data["give_quiz_index"] = 0
        context.user_data["give_quiz_questions"] = questions
        await send_next_quiz_question(query.message.chat_id, context)

async def send_next_quiz_question(chat_id, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data.get("give_quiz_index", 0)
    questions = context.user_data.get("give_quiz_questions", [])

    if index >= len(questions):
        await context.bot.send_message(chat_id, "✅ Quiz completed.")
        return

    question = questions[index]
    bot = context.bot

    if question.get("image"):
        await bot.send_photo(chat_id, photo=question["image"])

    keyboard = [
        [InlineKeyboardButton("➡️ Next", callback_data="next_quiz_question")],
        [InlineKeyboardButton("Skip Skip", callback_data="skip_quiz_question")]
    ]

    await bot.send_poll(
        chat_id=chat_id,
        question=f"Q{index + 1}: {question['question']}",
        options=question["options"],
        type=Poll.QUIZ,
        correct_option_id=question["correct_option_id"],
        is_anonymous=False,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def next_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["give_quiz_index"] += 1
    await send_next_quiz_question(query.message.chat_id, context)

async def skip_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["give_quiz_index"] += 1
    await send_next_quiz_question(query.message.chat_id, context)

# Team management functions
def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

async def create_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in authorized_users:
        await update.message.reply_text("🔒 You need authorization to create teams. Use /prepcentre first.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("⚠ Usage: /create_team <team_name>")
        return
    team_name = ' '.join(context.args).strip()
    if team_name in teams:
        await update.message.reply_text("⚠️ Team already exists.")
        return
    teams[team_name] = []
    save_teams(teams)
    await update.message.reply_text(f"✅ Team *{team_name}* created.", parse_mode="Markdown")

async def delete_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("⚠ Usage: /dlt <team_name>")
        return
    team_name = ' '.join(context.args).strip()
    if team_name not in teams:
        await update.message.reply_text("⚠️ Team not found.")
        return
    del teams[team_name]
    save_teams(teams)
    await update.message.reply_text(f"🗑️ Team *{team_name}* deleted.", parse_mode="Markdown")

async def list_teams(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not teams:
        await update.message.reply_text("📭 No teams found.")
        return
    text = "\n".join(f"• {team}" for team in teams)
    await update.message.reply_text(f"👥 Teams:\n{text}")

# NEW BATTLE SYSTEM
async def battle_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in authorized_users:
        await update.message.reply_text("🔒 You need authorization to create battles. Use /prepcentre first.")
        return

    if len(teams) < 2:
        await update.message.reply_text("⚠ Need at least 2 teams for battle. Create more teams first.")
        return

    # Step 1: Choose Team 1
    keyboard = [
        [InlineKeyboardButton(team, callback_data=f"battleteam1:{team}")]
        for team in teams
    ]
    await update.message.reply_text("Choose Team 1:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_battle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("battleteam1:"):
        team1 = query.data.split(":", 1)[1]
        context.user_data["battle_team1"] = team1

        # Step 2: Choose Team 2
        available_teams = [team for team in teams if team != team1]
        keyboard = [
            [InlineKeyboardButton(team, callback_data=f"battleteam2:{team}")]
            for team in available_teams
        ]
        await query.edit_message_text(
            "Choose Team 2:", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("battleteam2:"):
        team2 = query.data.split(":", 1)[1]
        team1 = context.user_data.get("battle_team1")

        if not team1:
            await query.edit_message_text("⚠ Battle setup incomplete.")
            return

        context.user_data["battle_team2"] = team2

        # Step 3: Choose Quiz
        user_id = str(query.from_user.id)
        quizzes = user_quizzes.get(user_id, {})

        if not quizzes:
            await query.edit_message_text("⚠ No quizzes found. Create a quiz first.")
            return

        keyboard = [
            [InlineKeyboardButton(quiz_name, callback_data=f"battlequiz:{quiz_name}")]
            for quiz_name in quizzes
        ]
        await query.edit_message_text(
            "Now choose a quiz for this battle:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("battlequiz:"):
        quiz_name = query.data.split(":", 1)[1]
        team1 = context.user_data.get("battle_team1")
        team2 = context.user_data.get("battle_team2")

        if not team1 or not team2:
            await query.edit_message_text("⚠ Battle setup incomplete.")
            return

        # Generate battle codes
        code1 = generate_code()
        code2 = generate_code()
        battle_id = generate_code(8)

        # Initialize bot_data if needed
        if not hasattr(context, 'bot_data'):
            context.bot_data = {}
        if 'battles' not in context.bot_data:
            context.bot_data['battles'] = battles_data.copy()

        # Store battle data
        context.bot_data['battles'][battle_id] = {
            "quiz_name": quiz_name,
            "team1": team1,
            "team2": team2,
            "questions": user_quizzes.get(str(query.from_user.id), {}).get(quiz_name, []),
            "creator_id": str(query.from_user.id),
            "used_codes": set(),
            "team1_scores": {},  # user_id: score
            "team2_scores": {},  # user_id: score
            "current_question": 0,
            "question_results": [],
            "team1_chat": None,
            "team2_chat": None,
            "team1_initiator": None,
            "team2_initiator": None,
            "team_question_indices": {"team1": 0, "team2": 0} # Track team-specific indices
        }
        save_battles(context.bot_data['battles']) # Save battle data

        # Store team assignments
        team_assignments[code1] = {
            "team": team1,
            "quiz": quiz_name,
            "battle_id": battle_id,
            "is_battle": True
        }

        team_assignments[code2] = {
            "team": team2,
            "quiz": quiz_name,
            "battle_id": battle_id,
            "is_battle": True
        }

        save_team_assignments(team_assignments)

        # Send setup confirmation
        await query.edit_message_text(
            f"✅ Perfect, your battle has been set up!\n"
            f"📘 Quiz: *{quiz_name}*\n"
            f"⚔ Team 1: *{team1}*  |  Team 2: *{team2}*\n\n"
            f"🔐 Team {team1} code: `{code1}`\n"
            f"🔐 Team {team2} code: `{code2}`\n\n"
            f"Share these codes in private with team groups.",
            parse_mode="Markdown"
        )

async def handle_team_code_detection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if update has a message and message has text
    if not update.message or not update.message.text:
        return
        
    user_id = str(update.effective_user.id)
    text = update.message.text.strip().upper()

    # Initialize bot_data if needed
    if not hasattr(context, 'bot_data'):
        context.bot_data = {}
    if 'active_chats' not in context.bot_data:
        context.bot_data['active_chats'] = set()
    # Initialize bot_data if needed
    if not hasattr(context, 'bot_data'):
        context.bot_data = {}
    if 'battles' not in context.bot_data:
        context.bot_data['battles'] = battles_data.copy()

    # Always track this chat as active
    context.bot_data['active_chats'].add(update.effective_chat.id)

    # Check if it's a battle code
    if text in team_assignments:
        data = team_assignments[text]
        battle_id = data.get("battle_id")

        if battle_id and battle_id in context.bot_data['battles']:
            battle_data = context.bot_data['battles'][battle_id]

            # Check if code was already used
            if text in battle_data['used_codes']:
                await update.message.reply_text("⚠ This code has already been used!")
                return

            quiz = data["quiz"]
            team = data["team"]
            opponent = battle_data['team1'] if team == battle_data['team2'] else battle_data['team2']

            keyboard = [
                [InlineKeyboardButton("Start Quiz", callback_data=f"start_battle:{text}")]
            ]

            await update.message.reply_text(
                f"🧩 Quiz Battle Identified!\n"
                f"🏷 Quiz: *{quiz}*\n"
                f"👥 Team: *{team}*\n"
                f"❓ Do you want to start this quiz?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            # Store who sent the code for permission control
            if not hasattr(context, 'chat_data'):
                context.chat_data = {}
            context.chat_data[f"code_sender_{text}"] = str(update.effective_user.id)

async def start_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    code = query.data.split(":", 1)[1]

    # Check if this user sent the original code
    if not hasattr(context, 'chat_data'):
        context.chat_data = {}

    original_sender_id = context.chat_data.get(f"code_sender_{code}")
    if original_sender_id and user_id != original_sender_id:
        await query.answer("🚫 Only the person who sent the code can start this battle!", show_alert=True)
        return

    await query.answer()

    if code not in team_assignments:
        await query.edit_message_text("⚠ Invalid or expired code.")
        return

    data = team_assignments[code]
    battle_id = data["battle_id"]
    battle_data = context.bot_data['battles'][battle_id]

    # Check if code was already used
    if code in battle_data['used_codes']:
        await query.edit_message_text("⚠ This code has already been used!")
        return

    # Mark code as used
    battle_data['used_codes'].add(code)

    team_name = data["team"]

    # Set team's chat and initiator
    if team_name == battle_data["team1"]:
        battle_data["team1_chat"] = query.message.chat_id
        battle_data["team1_initiator"] = user_id
    else:
        battle_data["team2_chat"] = query.message.chat_id
        battle_data["team2_initiator"] = user_id

    # Set up battle context
    context.user_data["battle_id"] = battle_id
    context.user_data["current_team"] = team_name
    context.user_data["quiz_initiator_id"] = user_id
    context.user_data["current_question_index"] = 0

    await query.edit_message_text("⚔️ Battle starting...")
    await send_next_battle_question(query.message.chat_id, context)

async def send_next_battle_question(chat_id, context: ContextTypes.DEFAULT_TYPE):
    battle_id = context.user_data.get("battle_id")
    battle_data = context.bot_data['battles'].get(battle_id)

    if not battle_data:
        await context.bot.send_message(chat_id, "⚠ Battle data not found.")
        return

    index = context.user_data.get("current_question_index", 0)
    questions = battle_data["questions"]

    if index >= len(questions):
        await context.bot.send_message(chat_id, "✅ You have completed all questions! Waiting for results...")
        return

    question = questions[index]
    bot = context.bot

    # Send image if available
    if question.get("image"):
        await bot.send_photo(chat_id, photo=question["image"])

    # Create option buttons (A, B, C, D) showing both label and option text
    option_buttons = []
    for i, option in enumerate(question["options"]):
        label = chr(65 + i)  # A, B, C, D
        option_buttons.append([InlineKeyboardButton(f"{label}. {option}", callback_data=f"answer:{battle_id}:{index}:{i}")])

    # Add Next/Skip buttons (only for initiator)
    control_buttons = [
        InlineKeyboardButton("Next", callback_data=f"next_battle:{battle_id}:{index}"),
        InlineKeyboardButton("Skip", callback_data=f"skip_battle:{battle_id}:{index}")
    ]

    # Arrange buttons: each option in its own row, then controls in another row
    keyboard_layout = option_buttons + [control_buttons]
    keyboard = InlineKeyboardMarkup(keyboard_layout)

    # Store the message ID for later updates
    message = await bot.send_message(
        chat_id=chat_id,
        text=f"⚔️ Question {index + 1}: {question['question']}",
        reply_markup=keyboard
    )

    # Store message info for updates
    if 'question_messages' not in battle_data:
        battle_data['question_messages'] = {}
    battle_data['question_messages'][chat_id] = {
        'message_id': message.message_id,
        'question_index': index,
        'attempted_users': set()
    }

async def handle_battle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)

    if query.data.startswith("answer:"):
        _, battle_id, question_index, selected_option = query.data.split(":")
        question_index = int(question_index)
        selected_option = int(selected_option)

        battle_data = context.bot_data['battles'].get(battle_id)
        if not battle_data:
            await query.answer("⚠ Battle not found!", show_alert=True)
            return

        # Check if user already answered this question
        team_name = None
        if battle_data["team1_chat"] == query.message.chat_id:
            team_name = "team1"
            scores_dict = battle_data["team1_scores"]
        elif battle_data["team2_chat"] == query.message.chat_id:
            team_name = "team2"
            scores_dict = battle_data["team2_scores"]
        else:
            await query.answer("⚠ Invalid team!", show_alert=True)
            return

        # Check if user already answered
        answer_key = f"{user_id}_q{question_index}"
        if answer_key in scores_dict:
            await query.answer("🔒 You already answered this question!", show_alert=True)
            return

        # Record answer and calculate score
        question = battle_data['questions'][question_index]
        correct_option = question["correct_option_id"]
        score = 4 if selected_option == correct_option else -1

        scores_dict[answer_key] = score

        # Don't update individual stars immediately - wait for announcement
        # Individual leaderboard will only update when question is announced

        # Add user to attempted users for this question
        if 'question_messages' in battle_data and query.message.chat_id in battle_data['question_messages']:
            # Ensure attempted_users is a set (convert from list if needed)
            attempted_users = battle_data['question_messages'][query.message.chat_id]['attempted_users']
            if isinstance(attempted_users, list):
                attempted_users = set(attempted_users)
                battle_data['question_messages'][query.message.chat_id]['attempted_users'] = attempted_users
            attempted_users.add(user_id)

            # Update question text to show tick
            await update_question_with_attempts(battle_id, query.message.chat_id, context)

        option_label = chr(65 + selected_option)  # A, B, C, D
        await query.answer(f"✅ Answer {option_label} recorded!", show_alert=False)

    elif query.data.startswith("next_battle:"):
        _, battle_id, question_index = query.data.split(":")
        question_index = int(question_index)

        battle_data = context.bot_data['battles'].get(battle_id)
        if not battle_data:
            await query.answer("⚠ Battle not found!", show_alert=True)
            return

        # Check if user is the initiator
        if battle_data["team1_chat"] == query.message.chat_id:
            if user_id != battle_data["team1_initiator"]:
                await query.answer("🚫 Only the quiz initiator can control this!", show_alert=True)
                return
        elif battle_data["team2_chat"] == query.message.chat_id:
            if user_id != battle_data["team2_initiator"]:
                await query.answer("🚫 Only the quiz initiator can control this!", show_alert=True)
                return
        else:
            await query.answer("⚠ Invalid team!", show_alert=True)
            return

        await query.answer()

        # Track that this initiator pressed Next for this question
        if 'initiator_next_presses' not in battle_data:
            battle_data['initiator_next_presses'] = {}
        if question_index not in battle_data['initiator_next_presses']:
            battle_data['initiator_next_presses'][question_index] = set()

        # Ensure it's a set (in case it was loaded as a list)
        if isinstance(battle_data['initiator_next_presses'][question_index], list):
            battle_data['initiator_next_presses'][question_index] = set(battle_data['initiator_next_presses'][question_index])

        battle_data['initiator_next_presses'][question_index].add(user_id)
        save_battles(context.bot_data['battles'])

        # Remove buttons from current team's chat
        current_chat_id = query.message.chat_id
        if 'question_messages' in battle_data and current_chat_id in battle_data['question_messages']:
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=current_chat_id,
                    message_id=battle_data['question_messages'][current_chat_id]['message_id'],
                    reply_markup=None
                )
            except:
                pass

        # Check if both initiators pressed Next and announce
        await check_and_announce_question_result(battle_id, question_index, context)

        # Move to next question for this team only (completely independent)
        current_team = None
        if battle_data["team1_chat"] == query.message.chat_id:
            current_team = "team1"
        elif battle_data["team2_chat"] == query.message.chat_id:
            current_team = "team2"

        if current_team:
            # Initialize team question indices if not present
            if 'team_question_indices' not in battle_data:
                battle_data['team_question_indices'] = {"team1": 0, "team2": 0}

            # Increment this team's question index
            battle_data['team_question_indices'][current_team] += 1
            next_index = battle_data['team_question_indices'][current_team]

            # Update context for this specific team
            context.user_data["current_question_index"] = next_index
        else:
            # Fallback to old method
            context.user_data["current_question_index"] = context.user_data.get("current_question_index", 0) + 1
            next_index = context.user_data["current_question_index"]

        save_battles(context.bot_data['battles'])

        if next_index >= len(battle_data["questions"]):
            await query.message.reply_text("✅ You have completed all questions! Waiting for results...")
        else:
            await send_next_battle_question(query.message.chat_id, context)

    elif query.data.startswith("skip_battle:"):
        _, battle_id, question_index = query.data.split(":")
        question_index = int(question_index)

        battle_data = context.bot_data['battles'].get(battle_id)
        if not battle_data:
            await query.answer("⚠ Battle not found!", show_alert=True)
            return

        # Check if user is the initiator
        if battle_data["team1_chat"] == query.message.chat_id:
            if user_id != battle_data["team1_initiator"]:
                await query.answer("🚫 Only the quiz initiator can control this!", show_alert=True)
                return
        elif battle_data["team2_chat"] == query.message.chat_id:
            if user_id != battle_data["team2_initiator"]:
                await query.answer("🚫 Only the quiz initiator can control this!", show_alert=True)
                return
        else:
            await query.answer("⚠ Invalid team!", show_alert=True)
            return

        await query.answer()

        # Track that this initiator pressed Skip (treat same as Next for announcement)
        if 'initiator_next_presses' not in battle_data:
            battle_data['initiator_next_presses'] = {}
        if question_index not in battle_data['initiator_next_presses']:
            battle_data['initiator_next_presses'][question_index] = set()

        # Ensure it's a set (in case it was loaded as a list)
        if isinstance(battle_data['initiator_next_presses'][question_index], list):
            battle_data['initiator_next_presses'][question_index] = set(battle_data['initiator_next_presses'][question_index])

        battle_data['initiator_next_presses'][question_index].add(user_id)
        save_battles(context.bot_data['battles'])

        # Remove buttons from current team's chat
        current_chat_id = query.message.chat_id
        if 'question_messages' in battle_data and current_chat_id in battle_data['question_messages']:
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=current_chat_id,
                    message_id=battle_data['question_messages'][current_chat_id]['message_id'],
                    reply_markup=None
                )
            except:
                pass

        # Check if both initiators pressed Next/Skip and announce
        await check_and_announce_question_result(battle_id, question_index, context)

        # Move to next question for this team only (completely independent)
        current_team = None
        if battle_data["team1_chat"] == query.message.chat_id:
            current_team = "team1"
        elif battle_data["team2_chat"] == query.message.chat_id:
            current_team = "team2"

        if current_team:
            # Initialize team question indices if not present
            if 'team_question_indices' not in battle_data:
                battle_data['team_question_indices'] = {"team1": 0, "team2": 0}

            # Increment this team's question index
            battle_data['team_question_indices'][current_team] += 1
            next_index = battle_data['team_question_indices'][current_team]

            # Update context for this specific team
            context.user_data["current_question_index"] = next_index
        else:
            # Fallback to old method
            context.user_data["current_question_index"] = context.user_data.get("current_question_index", 0) + 1
            next_index = context.user_data["current_question_index"]

        save_battles(context.bot_data['battles'])

        if next_index >= len(battle_data["questions"]):
            await query.message.reply_text("✅ You have completed all questions! Waiting for results...")
        else:
            await send_next_battle_question(query.message.chat_id, context)

async def check_and_announce_question_result(battle_id, question_index, context):
    """Check if both team initiators have pressed Next for this question and ask battle maker for announcement"""
    battle_data = context.bot_data['battles'].get(battle_id)
    if not battle_data:
        return

    # Initialize announced questions set if not exists
    if 'announced_questions' not in battle_data:
        battle_data['announced_questions'] = set()

    # Check if we already announced this question
    if question_index in battle_data['announced_questions']:
        return

    # Get initiator press tracking
    if 'initiator_next_presses' not in battle_data:
        battle_data['initiator_next_presses'] = {}

    next_presses = battle_data['initiator_next_presses'].get(question_index, set())

    # Ensure next_presses is a set (convert from list if needed)
    if isinstance(next_presses, list):
        next_presses = set(next_presses)
        battle_data['initiator_next_presses'][question_index] = next_presses

    team1_initiator = battle_data.get("team1_initiator")
    team2_initiator = battle_data.get("team2_initiator")

    # Check if both initiators exist and are different people
    if not team1_initiator or not team2_initiator:
        return

    # If both teams have the same initiator, only ask when that person presses Next
    if team1_initiator == team2_initiator:
        if team1_initiator not in next_presses:
            return
        # Same person is initiator for both teams, so ask immediately
    else:
        # Different initiators - need both to press Next
        team1_pressed_next = team1_initiator in next_presses
        team2_pressed_next = team2_initiator in next_presses

        # Debug logging
        print(f"Question {question_index}: Team1 initiator {team1_initiator} pressed: {team1_pressed_next}")
        print(f"Question {question_index}: Team2 initiator {team2_initiator} pressed: {team2_pressed_next}")
        print(f"Next presses for Q{question_index}: {next_presses}")

        # If both different initiators have pressed Next for this question
        if not (team1_pressed_next and team2_pressed_next):
            return

    # Send private message to battle creator asking for announcement decision
    creator_id = battle_data.get("creator_id")
    if creator_id:
        await ask_battle_maker_for_announcement(creator_id, battle_id, question_index, context)

async def ask_battle_maker_for_announcement(creator_id, battle_id, question_index, context):
    """Ask battle maker privately whether to announce question results"""
    battle_data = context.bot_data['battles'].get(battle_id)
    if not battle_data:
        return

    # Calculate gains for this question
    team1_gains = sum(score for key, score in battle_data["team1_scores"].items() if key.endswith(f"_q{question_index}"))
    team2_gains = sum(score for key, score in battle_data["team2_scores"].items() if key.endswith(f"_q{question_index}"))

    team1_name = battle_data["team1"]
    team2_name = battle_data["team2"]

    # Create message with question results
    result_message = (
        f"🎯 **Battle Question {question_index + 1} Complete**\n\n"
        f"**Results:**\n"
        f"Team {team1_name}: {team1_gains} prep tokens\n"
        f"Team {team2_name}: {team2_gains} prep tokens\n\n"
        f"Should I announce this result to all groups?"
    )

    # Create inline buttons
    keyboard = [
        [
            InlineKeyboardButton("📢 Announce", callback_data=f"announce_question:{battle_id}:{question_index}"),
            InlineKeyboardButton("👁️ Show me result", callback_data=f"show_result:{battle_id}:{question_index}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.send_message(
            chat_id=creator_id,
            text=result_message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Failed to send private message to creator {creator_id}: {e}")
        # Fallback: auto-announce if we can't reach creator
        await announce_question_result(battle_id, question_index, context)

async def check_final_completion(battle_id, context):
    """Check if both teams have completed all questions and announce final results"""
    battle_data = context.bot_data['battles'].get(battle_id)
    if not battle_data:
        return

    # Prevent multiple final announcements
    if battle_data.get('final_announced', False):
        return

    total_questions = len(battle_data["questions"])

    # Check if both teams have finished all questions (reached end independently)
    team1_finished = battle_data.get('team_question_indices', {}).get('team1', 0) >= total_questions
    team2_finished = battle_data.get('team_question_indices', {}).get('team2', 0) >= total_questions

    # Alternative check: if all questions have been announced
    all_questions_announced = len(battle_data.get('announced_questions', set())) >= total_questions

    if (team1_finished and team2_finished) or all_questions_announced:
        await announce_final_results(battle_id, context)

async def announce_question_result(battle_id, question_index, context, update_leaderboard=True):
    """Announce question result to all groups and optionally update leaderboard"""
    battle_data = context.bot_data['battles'].get(battle_id)
    if not battle_data:
        return

    # Mark this question as announced
    if 'announced_questions' not in battle_data:
        battle_data['announced_questions'] = set()
    battle_data['announced_questions'].add(question_index)
    save_battles(context.bot_data['battles'])

    # Calculate gains for this question
    team1_gains = sum(score for key, score in battle_data["team1_scores"].items() if key.endswith(f"_q{question_index}"))
    team2_gains = sum(score for key, score in battle_data["team2_scores"].items() if key.endswith(f"_q{question_index}"))

    team1_name = battle_data["team1"]
    team2_name = battle_data["team2"]

    # Question result announcement
    announcement = (
        f"🎯 Question {question_index + 1} Results:\n"
        f"Team {team1_name} gained: {team1_gains} prep tokens\n"
        f"Team {team2_name} gained: {team2_gains} prep tokens"
    )

    # Send to all active chats
    active_chats = context.bot_data.get('active_chats', set())
    for chat_id in active_chats:
        try:
            await context.bot.send_message(chat_id, announcement)
        except Exception:
            pass

    # Only update individual leaderboard if announcement is made
    if update_leaderboard:
        # Update individual stars for this question
        global stars_data
        for key, score in battle_data["team1_scores"].items():
            if key.endswith(f"_q{question_index}"):
                user_id = key.split('_q')[0]
                if user_id not in stars_data:
                    stars_data[user_id] = 0
                stars_data[user_id] += score
        
        for key, score in battle_data["team2_scores"].items():
            if key.endswith(f"_q{question_index}"):
                user_id = key.split('_q')[0]
                if user_id not in stars_data:
                    stars_data[user_id] = 0
                stars_data[user_id] += score
        
        save_stars(stars_data)

    # Check if this was the last question and both teams completed
    if question_index + 1 == len(battle_data["questions"]):
        # Check if both teams have completed all questions (pressed Next for last question)
        total_questions = len(battle_data["questions"])
        last_question_index = total_questions - 1

        if last_question_index in battle_data['announced_questions']:
            await ask_battle_maker_for_final_announcement(battle_data.get("creator_id"), battle_id, context)

async def ask_battle_maker_for_final_announcement(creator_id, battle_id, context):
    """Ask battle maker whether to announce final battle results"""
    battle_data = context.bot_data['battles'].get(battle_id)
    if not battle_data:
        return

    # Prevent multiple final announcement requests
    if battle_data.get('final_announcement_requested', False):
        return
    
    battle_data['final_announcement_requested'] = True
    save_battles(context.bot_data['battles'])

    team1_name = battle_data["team1"]
    team2_name = battle_data["team2"]

    # Calculate total gains
    team1_total_gains = sum(battle_data["team1_scores"].values())
    team2_total_gains = sum(battle_data["team2_scores"].values())

    # Find Man of the Match (highest individual scorer)
    all_individual_scores = {}

    # Collect individual scores from team1
    for key, score in battle_data["team1_scores"].items():
        user_id = key.split('_q')[0]  # Extract user_id from "user_id_q0" format
        if user_id not in all_individual_scores:
            all_individual_scores[user_id] = 0
        all_individual_scores[user_id] += score

    # Collect individual scores from team2
    for key, score in battle_data["team2_scores"].items():
        user_id = key.split('_q')[0]  # Extract user_id from "user_id_q0" format
        if user_id not in all_individual_scores:
            all_individual_scores[user_id] = 0
        all_individual_scores[user_id] += score

    # Find the highest scorer
    man_of_match_user_id = None
    max_score = float('-inf')
    for user_id, total_score in all_individual_scores.items():
        if total_score > max_score:
            max_score = total_score
            man_of_match_user_id = user_id

    # Determine the winner
    if team1_total_gains > team2_total_gains:
        winner = team1_name
        congratulations = f"🎉 Team {team1_name} wins!"
    elif team2_total_gains > team1_total_gains:
        winner = team2_name
        congratulations = f"🎉 Team {team2_name} wins!"
    else:
        winner = None
        congratulations = "🤝 It's a tie!"

    # Create final results message
    man_of_match_name = await get_user_name(context, man_of_match_user_id) if man_of_match_user_id else "Unknown"
    
    final_result_message = (
        f"🏆 **Battle Complete!**\n\n"
        f"**Final Results:**\n"
        f"{congratulations}\n\n"
        f"Team {team1_name}: {team1_total_gains} prep tokens\n"
        f"Team {team2_name}: {team2_total_gains} prep tokens\n\n"
        f"⭐ Man of the Match: **{man_of_match_name}** ({max_score} prep tokens)\n\n"
        f"Should I announce the final results to all groups?"
    )

    # Create inline buttons
    keyboard = [
        [
            InlineKeyboardButton("📢 Announce Final", callback_data=f"announce_final:{battle_id}"),
            InlineKeyboardButton("👁️ Show me result", callback_data=f"show_final:{battle_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.send_message(
            chat_id=creator_id,
            text=final_result_message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Failed to send final announcement request to creator {creator_id}: {e}")
        # Fallback: auto-announce if we can't reach creator
        await announce_final_results(battle_id, context)

async def announce_final_results(battle_id, context):
    """Announce final battle results with total gains and winner"""
    battle_data = context.bot_data['battles'].get(battle_id)
    if not battle_data:
        return

    # Prevent multiple final announcements
    if battle_data.get('final_announced', False):
        return

    battle_data['final_announced'] = True
    save_battles(context.bot_data['battles'])

    team1_name = battle_data["team1"]
    team2_name = battle_data["team2"]

    # Calculate total gains
    team1_total_gains = sum(battle_data["team1_scores"].values())
    team2_total_gains = sum(battle_data["team2_scores"].values())

    # Find Man of the Match (highest individual scorer)
    all_individual_scores = {}

    # Collect individual scores from team1
    for key, score in battle_data["team1_scores"].items():
        user_id = key.split('_q')[0]  # Extract user_id from "user_id_q0" format
        if user_id not in all_individual_scores:
            all_individual_scores[user_id] = 0
        all_individual_scores[user_id] += score

    # Collect individual scores from team2
    for key, score in battle_data["team2_scores"].items():
        user_id = key.split('_q')[0]  # Extract user_id from "user_id_q0" format
        if user_id not in all_individual_scores:
            all_individual_scores[user_id] = 0
        all_individual_scores[user_id] += score

    # Find the highest scorer
    man_of_match_user_id = None
    max_score = float('-inf')
    for user_id, total_score in all_individual_scores.items():
        if total_score > max_score:
            max_score = total_score
            man_of_match_user_id = user_id

    # Determine the winner
    if team1_total_gains > team2_total_gains:
        winner = team1_name
        congratulations = f"🎉 Congratulations to the winning team {team1_name}!"
    elif team2_total_gains > team1_total_gains:
        winner = team2_name
        congratulations = f"🎉 Congratulations to the winning team {team2_name}!"
    else:
        winner = None
        congratulations = "🤝 It's a tie! Both teams performed equally well!"

    # Create final announcement message
    final_announcement = (
        "🏆 Battle Results 🏆\n\n"
        f"{congratulations}\n\n"
        f"Team {team1_name} total gains: {team1_total_gains} prep tokens\n"
        f"Team {team2_name} total gains: {team2_total_gains} prep tokens\n\n"
    )

    # Add Man of the Match if found
    if man_of_match_user_id and max_score > float('-inf'):
        man_of_match_name = await get_user_name(context, man_of_match_user_id)
        final_announcement += f"⭐ Man of the Match: **{man_of_match_name}** ({max_score} prep tokens)"

    # Send to all active chats
    active_chats = context.bot_data.get('active_chats', set())
    for chat_id in active_chats:
        try:
            await context.bot.send_message(chat_id, final_announcement, parse_mode="Markdown")
        except Exception:
            pass

async def update_question_with_attempts(battle_id, chat_id, context):
    """Update question message to show attempt ticks"""
    battle_data = context.bot_data['battles'].get(battle_id)
    if not battle_data or 'question_messages' not in battle_data:
        return

    message_info = battle_data['question_messages'].get(chat_id)
    if not message_info:
        return

    question_index = message_info['question_index']
    attempted_count = len(message_info['attempted_users'])

    question = battle_data["questions"][question_index]

    # Add tick indicators
    tick_indicator = "✅" * attempted_count if attempted_count > 0 else ""
    updated_text = f"⚔️ Question {question_index + 1}: {question['question']} {tick_indicator}"

    try:
        # Get the current keyboard from battle data
        battle_data = context.bot_data['battles'].get(battle_id)
        if battle_data:
            question = battle_data["questions"][question_index]

            # Recreate the keyboard with options
            option_buttons = []
            for i, option in enumerate(question["options"]):
                label = chr(65 + i)  # A, B, C, D
                option_buttons.append([InlineKeyboardButton(f"{label}. {option}", callback_data=f"answer:{battle_id}:{question_index}:{i}")])

            control_buttons = [
                InlineKeyboardButton("Next", callback_data=f"next_battle:{battle_id}:{question_index}"),
                InlineKeyboardButton("Skip", callback_data=f"skip_battle:{battle_id}:{question_index}")
            ]

            keyboard_layout = option_buttons + [control_buttons]
            keyboard = InlineKeyboardMarkup(keyboard_layout)

            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_info['message_id'],
                text=updated_text,
                reply_markup=keyboard
            )
    except Exception:
        pass  # Message might be too old to edit

async def check_and_announce_question(battle_id, question_index, context):
    """Check if both teams have attempted the current question and announce if so"""
    battle_data = context.bot_data['battles'].get(battle_id)
    if not battle_data:
        return

    # Initialize announced questions set if not exists
    if 'announced_questions' not in battle_data:
        battle_data['announced_questions'] = set()

    # Check if we already announced this question
    if question_index in battle_data['announced_questions']:
        return

    # Count attempts from both teams for this question
    team1_attempts = sum(1 for key in battle_data["team1_scores"].keys() if key.endswith(f"_q{question_index}"))
    team2_attempts = sum(1 for key in battle_data["team2_scores"].keys() if key.endswith(f"_q{question_index}"))

    # Debug logging to see what's happening
    print(f"Question {question_index}: Team1 attempts: {team1_attempts}, Team2 attempts: {team2_attempts}")
    print(f"Team1 scores: {[k for k in battle_data['team1_scores'].keys() if k.endswith(f'_q{question_index}')]}")
    print(f"Team2 scores: {[k for k in battle_data['team2_scores'].keys() if k.endswith(f'_q{question_index}')]}")

    # If both teams have at least one attempt and we haven't announced yet
    if team1_attempts > 0 and team2_attempts > 0:
        # Mark this question as announced
        battle_data['announced_questions'].add(question_index)
        save_battles(context.bot_data['battles'])

        # Calculate scores for this question
        team1_question_score = sum(score for key, score in battle_data["team1_scores"].items() if key.endswith(f"_q{question_index}"))
        team2_question_score = sum(score for key, score in battle_data["team2_scores"].items() if key.endswith(f"_q{question_index}"))

        team1_name = battle_data["team1"]
        team2_name = battle_data["team2"]

        # Regular question announcement (for all questions including last)
        announcement = (
            f"🎯 Both teams have attempted Qn {question_index + 1}!\n"
            f"Team {team1_name} gained: +{team1_question_score} prep tokens\n"
            f"Team {team2_name} gained: +{team2_question_score} prep tokens"
        )

        # Send to all active chats
        active_chats = context.bot_data.get('active_chats', set())
        for chat_id in active_chats:
            try:
                await context.bot.send_message(chat_id, announcement)
            except Exception:
                pass  # Chat might be inactive

        # Check if this was the last question and if both teams have completed all questions
        if question_index + 1 == len(battle_data["questions"]):
            # Check if both teams have attempted all questions
            total_questions = len(battle_data["questions"])
            team1_attempted_all = True
            team2_attempted_all = True

            # Check each question to see if both teams have at least one attempt
            for q_idx in range(total_questions):
                team1_has_attempt = any(key.endswith(f"_q{q_idx}") for key in battle_data["team1_scores"])
                team2_has_attempt = any(key.endswith(f"_q{q_idx}") for key in battle_data["team2_scores"])

                if not team1_has_attempt:
                    team1_attempted_all = False
                if not team2_has_attempt:
                    team2_attempted_all = False

            # Announce final results if both teams have attempted all questions
            if team1_attempted_all and team2_attempted_all:
                await announce_final_battle_result(battle_id, context)

async def announce_final_battle_result(battle_id, context):
    battle_data = context.bot_data['battles'].get(battle_id)
    if not battle_data:
        return

    # Prevent multiple final announcements
    if battle_data.get('final_announced', False):
        return

    battle_data['final_announced'] = True

    team1_name = battle_data["team1"]
    team2_name = battle_data["team2"]

    # Calculate final scores
    team1_total = sum(score for score in battle_data["team1_scores"].values())
    team2_total = sum(score for score in battle_data["team2_scores"].values())

    # Find Man of the Match (highest individual scorer)
    all_individual_scores = {}

    # Collect individual scores from team1
    for key, score in battle_data["team1_scores"].items():
        user_id = key.split('_q')[0]  # Extract user_id from "user_id_q0" format
        if user_id not in all_individual_scores:
            all_individual_scores[user_id] = 0
        all_individual_scores[user_id] += score

    # Collect individual scores from team2
    for key, score in battle_data["team2_scores"].items():
        user_id = key.split('_q')[0]  # Extract user_id from "user_id_q0" format
        if user_id not in all_individual_scores:
            all_individual_scores[user_id] = 0
        all_individual_scores[user_id] += score

    # Find the highest scorer
    man_of_match_user_id = None
    max_score = float('-inf')
    for user_id, total_score in all_individual_scores.items():
        if total_score > max_score:
            max_score = total_score
            man_of_match_user_id = user_id

    # Determine winner
    if team1_total > team2_total:
        winner_text = f"🥇 Congratulations to the Winning Team {team1_name}!"
    elif team2_total > team1_total:
        winner_text = f"🥇 Congratulations to the Winning Team {team2_name}!"
    else:
        winner_text = "🤝 It's a TIE! Both teams performed equally well!"

    # Final announcement
    final_announcement = (
        f"🏁 Battle Completed!\n"
        f"{winner_text}\n\n"
        f"📊 Final Scores:\n"
        f"Team {team1_name} – {team1_total} pt\n"
        f"Team {team2_name} – {team2_total} pt\n\n"
    )

    # Add Man of the Match if found
    if man_of_match_user_id and max_score > float('-inf'):
        man_of_match_name = await get_user_name(context, man_of_match_user_id)
        final_announcement += f"⭐ Man of the Match: **{man_of_match_name}** ({max_score} pt)"

    # Send to all active chats
    active_chats = context.bot_data.get('active_chats', set())
    for chat_id in active_chats:
        try:
            await context.bot.send_message(chat_id, final_announcement, parse_mode="Markdown")
        except Exception:
            pass

    # Don't automatically clean up - let teams finish at their own pace
    # Mark battle as completed for tracking
    battle_data['completed'] = True
    save_battles(context.bot_data['battles']) # Save battle data

async def get_user_name(context: ContextTypes.DEFAULT_TYPE, user_id: str):
    """Try to get the user's display name from Telegram"""
    try:
        user = await context.bot.get_chat(user_id)
        if user.first_name:
            full_name = user.first_name
            if user.last_name:
                full_name += f" {user.last_name}"
            return full_name
        elif user.username:
            return f"@{user.username}"
        else:
            return f"User {user_id[-4:]}"
    except:
        return f"Player {user_id[-4:]}"

async def calculate_real_team_scores():
    """Calculate actual team scores by summing individual scores from battles"""
    team_scores = {}

    # Initialize all teams with 0 score
    for team_name in teams.keys():
        team_scores[team_name] = 0

    # Calculate scores from battle data
    battles = load_battles()
    for battle_id, battle_data in battles.items():
        # Count scores from battles that have final_announced (finished battles)
        if battle_data.get('final_announced', False):
            # Add team1 scores
            team1_name = battle_data.get('team1')
            if team1_name in team_scores:
                team_scores[team1_name] += sum(battle_data.get('team1_scores', {}).values())

            # Add team2 scores
            team2_name = battle_data.get('team2')
            if team2_name in team_scores:
                team_scores[team2_name] += sum(battle_data.get('team2_scores', {}).values())

    return team_scores

async def shout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the shout command - only for authorized users"""
    user_id = str(update.effective_user.id)
    if user_id not in authorized_users:
        await update.message.reply_text("🔒 You need authorization to use shout command. Use /prepcentre first.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📢 **Shout Mode Activated!**\n\n"
        "Send me the message you want to broadcast to all groups.\n"
        "You can send:\n"
        "• Text messages\n"
        "• Images/Photos\n" 
        "• Stickers\n"
        "• Emojis\n"
        "• Any other message type\n\n"
        "Use /cancel to abort.",
        parse_mode="Markdown"
    )
    return WAIT_FOR_SHOUT_MESSAGE

async def receive_shout_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and broadcast the shout message to all active chats"""
    user_id = str(update.effective_user.id)
    user_name = await get_user_name(context, user_id)
    
    # Initialize bot_data if needed
    if not hasattr(context, 'bot_data'):
        context.bot_data = {}
    if 'active_chats' not in context.bot_data:
        context.bot_data['active_chats'] = set()
    
    # Get all possible chat IDs from various sources
    all_possible_chats = set()
    
    # Add active chats
    all_possible_chats.update(context.bot_data.get('active_chats', set()))
    
    # Add battle chat IDs from current battles
    battles = context.bot_data.get('battles', {})
    for battle_data in battles.values():
        if battle_data.get('team1_chat'):
            all_possible_chats.add(battle_data['team1_chat'])
        if battle_data.get('team2_chat'):
            all_possible_chats.add(battle_data['team2_chat'])
    
    # Add battle chat IDs from saved battles file
    saved_battles = load_battles()
    for battle_data in saved_battles.values():
        if battle_data.get('team1_chat'):
            all_possible_chats.add(battle_data['team1_chat'])
        if battle_data.get('team2_chat'):
            all_possible_chats.add(battle_data['team2_chat'])
    
    # If still no chats found, try to send to the current chat at least
    if not all_possible_chats:
        all_possible_chats.add(update.effective_chat.id)
    
    successful_broadcasts = 0
    failed_broadcasts = 0
    
    # Get the message to broadcast
    message_to_broadcast = update.message
    
    # First, send to current chat to confirm
    await update.message.reply_text("📢 Broadcasting announcement to all groups...", parse_mode="Markdown")
    
    # Broadcast to all possible chats
    for chat_id in all_possible_chats.copy():
        try:
            # Skip sending to the same chat where command was issued (to avoid duplicate)
            if chat_id == update.effective_chat.id:
                continue
                
            # Handle different message types
            if message_to_broadcast.text:
                # Text message
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"📢 **ANNOUNCEMENT**\n\n{message_to_broadcast.text}",
                    parse_mode="Markdown"
                )
            elif message_to_broadcast.photo:
                # Photo message
                caption = message_to_broadcast.caption or ""
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=message_to_broadcast.photo[-1].file_id,
                    caption=f"📢 **ANNOUNCEMENT**\n\n{caption}",
                    parse_mode="Markdown"
                )
            elif message_to_broadcast.sticker:
                # Sticker message
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="📢 **ANNOUNCEMENT**",
                    parse_mode="Markdown"
                )
                await context.bot.send_sticker(
                    chat_id=chat_id,
                    sticker=message_to_broadcast.sticker.file_id
                )
            elif message_to_broadcast.document:
                # Document/file message
                caption = message_to_broadcast.caption or ""
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=message_to_broadcast.document.file_id,
                    caption=f"📢 **ANNOUNCEMENT**\n\n{caption}",
                    parse_mode="Markdown"
                )
            elif message_to_broadcast.video:
                # Video message
                caption = message_to_broadcast.caption or ""
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=message_to_broadcast.video.file_id,
                    caption=f"📢 **ANNOUNCEMENT**\n\n{caption}",
                    parse_mode="Markdown"
                )
            elif message_to_broadcast.voice:
                # Voice message
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="📢 **ANNOUNCEMENT**",
                    parse_mode="Markdown"
                )
                await context.bot.send_voice(
                    chat_id=chat_id,
                    voice=message_to_broadcast.voice.file_id
                )
            elif message_to_broadcast.animation:
                # GIF/Animation message
                caption = message_to_broadcast.caption or ""
                await context.bot.send_animation(
                    chat_id=chat_id,
                    animation=message_to_broadcast.animation.file_id,
                    caption=f"📢 **ANNOUNCEMENT**\n\n{caption}",
                    parse_mode="Markdown"
                )
            else:
                # Fallback for other message types
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="📢 **ANNOUNCEMENT**\n\nSpecial message broadcasted!",
                    parse_mode="Markdown"
                )
            
            successful_broadcasts += 1
            
        except Exception as e:
            failed_broadcasts += 1
            print(f"Failed to broadcast to chat {chat_id}: {e}")
            # Remove inactive chats from active_chats only
            if 'active_chats' in context.bot_data:
                context.bot_data['active_chats'].discard(chat_id)
    
    # Send confirmation to the user
    confirmation_msg = (
        f"✅ **Broadcast Complete!**\n\n"
        f"📤 Successfully sent to: {successful_broadcasts} groups\n"
    )
    
    if failed_broadcasts > 0:
        confirmation_msg += f"❌ Failed to send to: {failed_broadcasts} groups\n"
    
    confirmation_msg += f"\n👤 **Broadcasted by:** {user_name}"
    
    await update.message.reply_text(confirmation_msg, parse_mode="Markdown")
    return ConversationHandler.END

async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show individual player's quiz statistics and prep tokens"""
    user_id = str(update.effective_user.id)
    user_name = await get_user_name(context, user_id)
    
    # Track active chats
    track_active_chat(update, context)

    # Get current prep tokens
    current_tokens = stars_data.get(user_id, 0)

    # Count quiz participation from battles
    total_questions_attempted = 0
    total_correct_answers = 0
    total_wrong_answers = 0
    battles_participated = 0
    total_battles_won = 0

    # Analyze battle participation
    battles = load_battles()
    for battle_id, battle_data in battles.items():
        user_participated = False
        user_questions_in_battle = 0
        user_correct_in_battle = 0
        user_wrong_in_battle = 0

        # Check team1 scores
        for key, score in battle_data.get('team1_scores', {}).items():
            if key.startswith(f"{user_id}_q"):
                user_participated = True
                user_questions_in_battle += 1
                if score > 0:  # Correct answer gives +4
                    user_correct_in_battle += 1
                else:  # Wrong answer gives -1
                    user_wrong_in_battle += 1

        # Check team2 scores  
        for key, score in battle_data.get('team2_scores', {}).items():
            if key.startswith(f"{user_id}_q"):
                user_participated = True
                user_questions_in_battle += 1
                if score > 0:  # Correct answer gives +4
                    user_correct_in_battle += 1
                else:  # Wrong answer gives -1
                    user_wrong_in_battle += 1

        if user_participated:
            battles_participated += 1
            total_questions_attempted += user_questions_in_battle
            total_correct_answers += user_correct_in_battle
            total_wrong_answers += user_wrong_in_battle

            # Check if user's team won this battle (only for completed battles)
            if battle_data.get('final_announced', False):
                team1_total = sum(battle_data.get('team1_scores', {}).values())
                team2_total = sum(battle_data.get('team2_scores', {}).values())

                # Determine which team user was on
                user_team = None
                if any(key.startswith(f"{user_id}_q") for key in battle_data.get('team1_scores', {})):
                    user_team = 'team1'
                elif any(key.startswith(f"{user_id}_q") for key in battle_data.get('team2_scores', {})):
                    user_team = 'team2'

                # Check if user's team won
                if user_team == 'team1' and team1_total > team2_total:
                    total_battles_won += 1
                elif user_team == 'team2' and team2_total > team1_total:
                    total_battles_won += 1

    # Calculate accuracy
    accuracy = 0
    if total_questions_attempted > 0:
        accuracy = (total_correct_answers / total_questions_attempted) * 100

    # Create stats message
    stats_message = (
        f"📊 **{user_name}'s Prep Stats**\n"
        f"{'='*30}\n\n"
        f"💎 **Current Prep Tokens:** {current_tokens}\n\n"
        f"⚔️ **Battle Statistics:**\n"
        f"   • Battles Participated: {battles_participated}\n"
        f"   • Battles Won: {total_battles_won}\n\n"
        f"🎯 **Quiz Performance:**\n"
        f"   • Questions Attempted: {total_questions_attempted}\n"
        f"   • Correct Answers: {total_correct_answers}\n"
        f"   • Wrong Answers: {total_wrong_answers}\n"
        f"   • Accuracy: {accuracy:.1f}%\n\n"
    )

    # Add performance rating
    if total_questions_attempted == 0:
        stats_message += "🆕 **Status:** New Player - Start participating in battles!"
    elif accuracy >= 80:
        stats_message += "🌟 **Performance:** Excellent!"
    elif accuracy >= 60:
        stats_message += "👍 **Performance:** Good!"
    elif accuracy >= 40:
        stats_message += "📈 **Performance:** Average - Keep improving!"
    else:
        stats_message += "💪 **Performance:** Needs improvement - Practice more!"

    await update.message.reply_text(stats_message, parse_mode="Markdown")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global stars_data
    
    # Track active chats
    track_active_chat(update, context)

    if not stars_data and not teams:
        await update.message.reply_text("📊 No leaderboard data available yet.\nStart playing quizzes to see rankings!")
        return

    # Calculate real team scores
    team_scores = await calculate_real_team_scores()

    # Sort teams by score
    sorted_teams = sorted(team_scores.items(), key=lambda x: x[1], reverse=True)

    # Prepare team leaderboard text with better formatting
    if not sorted_teams:
        leaderboard_text = "🏆 **Team Leaderboard**\n\n📭 No team scores yet.\nComplete battles to see rankings!"
    else:
        leaderboard_text = "🏆 **Team Leaderboard**\n" + "="*30 + "\n\n"

        for i, (team_name, score) in enumerate(sorted_teams, 1):
            # Add emoji based on ranking
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈" 
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"{i}."

            leaderboard_text += f"{emoji} **{team_name}**\n"
            leaderboard_text += f"   💎 {score} prep tokens\n\n"

    # Add button to switch to individual view
    keyboard = [[InlineKeyboardButton("👤 View Individual Rankings", callback_data="individual_leaderboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(leaderboard_text, parse_mode="Markdown", reply_markup=reply_markup)

async def individual_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    global stars_data

    if not stars_data:
        await query.edit_message_text("👤 **Individual Leaderboard**\n\n📭 No individual scores yet.\nAnswer quiz questions to earn prep tokens!")
        return

    # Sort users by score
    sorted_users = sorted(stars_data.items(), key=lambda x: x[1], reverse=True)

    # Prepare individual leaderboard text with real names
    leaderboard_text = "👤 **Individual Leaderboard**\n" + "="*30 + "\n\n"

    for i, (user_id, score) in enumerate(sorted_users, 1):
        # Add emoji based on ranking
        if i == 1:
            emoji = "🥇"
        elif i == 2:
            emoji = "🥈"
        elif i == 3:
            emoji = "🥉"
        else:
            emoji = f"{i}."

        # Get real user name
        user_name = await get_user_name(context, user_id)

        leaderboard_text += f"{emoji} **{user_name}**\n"
        leaderboard_text += f"   💎 {score} prep tokens\n\n"

    # Add button to switch back to team view
    keyboard = [[InlineKeyboardButton("🏆 View Team Rankings", callback_data="team_leaderboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(leaderboard_text, parse_mode="Markdown", reply_markup=reply_markup)

async def handle_announcement_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle battle maker's decision on announcements"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("announce_question:"):
        # Announce question result
        _, battle_id, question_index = data.split(":")
        question_index = int(question_index)
        
        await announce_question_result(battle_id, question_index, context, update_leaderboard=True)
        await query.edit_message_text("✅ Question result announced to all groups!", parse_mode="Markdown")
        
    elif data.startswith("show_result:"):
        # Just show result privately without announcing
        _, battle_id, question_index = data.split(":")
        question_index = int(question_index)
        
        battle_data = context.bot_data['battles'].get(battle_id)
        if battle_data:
            team1_gains = sum(score for key, score in battle_data["team1_scores"].items() if key.endswith(f"_q{question_index}"))
            team2_gains = sum(score for key, score in battle_data["team2_scores"].items() if key.endswith(f"_q{question_index}"))
            
            team1_name = battle_data["team1"]
            team2_name = battle_data["team2"]
            
            result_text = (
                f"👁️ **Private Result View**\n\n"
                f"Question {question_index + 1} Results:\n"
                f"Team {team1_name}: {team1_gains} prep tokens\n"
                f"Team {team2_name}: {team2_gains} prep tokens\n\n"
                f"*Note: This result was not announced publicly and leaderboards were not updated.*"
            )
            
            await query.edit_message_text(result_text, parse_mode="Markdown")
        
    elif data.startswith("announce_final:"):
        # Announce final battle results
        _, battle_id = data.split(":")
        
        await announce_final_results(battle_id, context)
        await query.edit_message_text("🏆 Final battle results announced to all groups!", parse_mode="Markdown")
        
    elif data.startswith("show_final:"):
        # Show final result privately without announcing
        _, battle_id = data.split(":")
        
        battle_data = context.bot_data['battles'].get(battle_id)
        if battle_data:
            team1_total_gains = sum(battle_data["team1_scores"].values())
            team2_total_gains = sum(battle_data["team2_scores"].values())
            
            team1_name = battle_data["team1"]
            team2_name = battle_data["team2"]
            
            # Find Man of the Match
            all_individual_scores = {}
            for key, score in battle_data["team1_scores"].items():
                user_id = key.split('_q')[0]
                if user_id not in all_individual_scores:
                    all_individual_scores[user_id] = 0
                all_individual_scores[user_id] += score
            
            for key, score in battle_data["team2_scores"].items():
                user_id = key.split('_q')[0]
                if user_id not in all_individual_scores:
                    all_individual_scores[user_id] = 0
                all_individual_scores[user_id] += score
            
            man_of_match_user_id = max(all_individual_scores.items(), key=lambda x: x[1], default=(None, 0))
            man_of_match_name = await get_user_name(context, man_of_match_user_id[0]) if man_of_match_user_id[0] else "Unknown"
            
            if team1_total_gains > team2_total_gains:
                winner_text = f"🎉 Team {team1_name} wins!"
            elif team2_total_gains > team1_total_gains:
                winner_text = f"🎉 Team {team2_name} wins!"
            else:
                winner_text = "🤝 It's a tie!"
            
            final_text = (
                f"👁️ **Private Final Results**\n\n"
                f"{winner_text}\n\n"
                f"Team {team1_name}: {team1_total_gains} prep tokens\n"
                f"Team {team2_name}: {team2_total_gains} prep tokens\n\n"
                f"⭐ Man of the Match: **{man_of_match_name}** ({man_of_match_user_id[1]} prep tokens)\n\n"
                f"*Note: These results were not announced publicly and leaderboards were not updated.*"
            )
            
            await query.edit_message_text(final_text, parse_mode="Markdown")

async def team_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Calculate real team scores
    team_scores = await calculate_real_team_scores()

    # Sort teams by score
    sorted_teams = sorted(team_scores.items(), key=lambda x: x[1], reverse=True)

    # Prepare team leaderboard text with better formatting
    if not sorted_teams:
        leaderboard_text = "🏆 **Team Leaderboard**\n\n📭 No team scores yet.\nComplete battles to see rankings!"
    else:
        leaderboard_text = "🏆 **Team Leaderboard**\n" + "="*30 + "\n\n"

        for i, (team_name, score) in enumerate(sorted_teams, 1):
            # Add emoji based on ranking
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"{i}."

            leaderboard_text += f"{emoji} **{team_name}**\n"
            leaderboard_text += f"   💎 {score} prep tokens\n\n"

    # Add button to switch to individual view
    keyboard = [[InlineKeyboardButton("👤 View Individual Rankings", callback_data="individual_leaderboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(leaderboard_text, parse_mode="Markdown", reply_markup=reply_markup)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Shout conversation handler
    shout_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("shout", shout_command)],
        states={
            WAIT_FOR_SHOUT_MESSAGE: [
                MessageHandler(
                    filters.ALL & ~filters.COMMAND, 
                    receive_shout_message
                )
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("quiz", create_quiz)],
        states={
            QUIZ_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quiz_name)],
            WAIT_FOR_POLL: [
                MessageHandler(filters.POLL, receive_poll),
                CommandHandler("skip", skip_image),
                CommandHandler("undo", undo_last),
                CommandHandler("end", end_quiz),
                CommandHandler("cancel", cancel),
            ],
            WAIT_FOR_IMAGE: [
                MessageHandler(filters.PHOTO, receive_image),
                CommandHandler("skip", skip_image),
                CommandHandler("undo", undo_last),
                CommandHandler("end", end_quiz),
                CommandHandler("cancel", cancel),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("end", end_quiz),
        ],
    )

    # Handlers
    app.add_handler(conv_handler)
    app.add_handler(shout_conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("prepcentre", unlock_quiz_access))
    app.add_handler(CommandHandler("myquiz", show_my_quizzes))
    app.add_handler(CommandHandler("poll", poll_instructions))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("myprep", my_stats))

    # Team management
    app.add_handler(CommandHandler("create_team", create_team))
    app.add_handler(CommandHandler("dlt", delete_team))
    app.add_handler(CommandHandler("teams", list_teams))
    app.add_handler(CommandHandler("battle", battle_quiz))

    # Quiz interaction
    app.add_handler(CallbackQueryHandler(handle_quiz_selection, pattern="^select_quiz:"))
    app.add_handler(CallbackQueryHandler(handle_quiz_action, pattern="^(give_quiz|delete_quiz|see_quiz)$"))
    app.add_handler(CallbackQueryHandler(next_quiz_callback, pattern="^next_quiz_question$"))
    app.add_handler(CallbackQueryHandler(skip_quiz_callback, pattern="^skip_quiz_question$"))

    # Battle handlers
    app.add_handler(CallbackQueryHandler(handle_battle_selection, pattern="^(battleteam1:|battleteam2:|battlequiz:)"))
    app.add_handler(CallbackQueryHandler(start_battle, pattern="^start_battle:"))
    app.add_handler(CallbackQueryHandler(handle_battle_answer, pattern="^(answer:|next_battle:|skip_battle:)"))

    # Leaderboard handlers
    app.add_handler(CallbackQueryHandler(individual_leaderboard, pattern="^individual_leaderboard$"))
    app.add_handler(CallbackQueryHandler(team_leaderboard, pattern="^team_leaderboard$"))

    # Announcement decision handlers
    app.add_handler(CallbackQueryHandler(handle_announcement_decision, pattern="^(announce_question:|show_result:|announce_final:|show_final:)"))

    # Team code detection
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_team_code_detection))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()