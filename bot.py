import logging
import os
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)


# Conversation states
SERVICE_CHOICE, IELTS_DEGREE_CHOICE, ANSWER_QUESTION = range(3)


# Services
SERVICE_IELTS_UNI = "IELTS bilan Yaponiyada Universitet"
SERVICE_ONLINE_JP = "Onlayn Yapon tili kurslari"
SERVICE_JLPT_SENMON = "JLPT bilan 専門学校"
SERVICE_JLPT_UNI = "JLPT bilan Universitet"
SERVICE_NO_CERT_SCHOOL = "Til sertifikatisiz Yapon tili padkursi"
SERVICE_NO_CERT_SCHOOL_ALT = "Til sertifikatisiz Yapon tili maktabi"

SERVICES = [
    SERVICE_IELTS_UNI,
    SERVICE_ONLINE_JP,
    SERVICE_JLPT_SENMON,
    SERVICE_JLPT_UNI,
    SERVICE_NO_CERT_SCHOOL,
]

IELTS_DEGREES = ["Bakalavr", "Magistratura", "PhD"]


# Question flows
FLOW_IELTS_BACHELOR = [
    {
        "key": "ielts_level",
        "prompt": "IELTS darajasi:",
        "options": ["7+", "6.5", "6.0", "5.5 yoki past", "Yo‘q"],
        "input_type": "choice",
    },
    {"key": "age", "prompt": "Yoshingiz:", "input_type": "age"},
    {
        "key": "graduated_place",
        "prompt": "Qayerni bitirgansiz?",
        "options": ["Maktab", "Universitet"],
        "input_type": "choice",
    },
    {
        "key": "graduation_year",
        "prompt": "Qachon bitirgansiz? (yil)",
        "input_type": "year",
    },
    {
        "key": "certificates",
        "prompt": "Sertifikatlaringiz:",
        "options": ["SAT", "ACT", "JLPT", "EJU", "AP", "Yo‘q"],
        "input_type": "choice",
    },
    {
        "key": "study_field",
        "prompt": "Qaysi yo‘nalishda o‘qimoqchisiz?",
        "input_type": "text",
    },
    {
        "key": "grades",
        "prompt": "Baholaringiz qanday?",
        "options": ["Asosan 5", "4-5", "Asosan 4", "3-4"],
        "input_type": "choice",
    },
    {
        "key": "extra_comment",
        "prompt": "Qo‘shimcha savol yoki izoh:",
        "input_type": "text",
    },
]

FLOW_IELTS_GRAD_PHD = [
    {
        "key": "ielts_level",
        "prompt": "IELTS darajasi:",
        "options": ["7+", "6.5", "6.0", "5.5 yoki past", "Yo‘q"],
        "input_type": "choice",
    },
    {"key": "age", "prompt": "Yoshingiz:", "input_type": "age"},
    {
        "key": "completed_degree",
        "prompt": "Qaysi darajani bitirgansiz?",
        "options": ["Bakalavr", "Magistratura"],
        "input_type": "choice",
    },
    {"key": "graduation_year", "prompt": "Bitirgan yil:", "input_type": "year"},
    {
        "key": "certificates",
        "prompt": "Sertifikatlar:",
        "options": ["GMAT", "GRE", "JLPT", "EJU", "Yo‘q"],
        "input_type": "choice",
    },
    {"key": "study_field", "prompt": "Yo‘nalish:", "input_type": "text"},
    {
        "key": "grades",
        "prompt": "Baholar:",
        "options": ["Asosan 5", "4-5", "Asosan 4", "3-4"],
        "input_type": "choice",
    },
    {
        "key": "research_paper",
        "prompt": "Ilmiy ish yozganmisiz?",
        "options": ["Ha", "Yo‘q"],
        "input_type": "choice",
    },
    {
        "key": "extra_comment",
        "prompt": "Qo‘shimcha savol yoki izoh:",
        "input_type": "text",
    },
]

FLOW_ONLINE_JP = [
    {
        "key": "japanese_level",
        "prompt": "Yapon tili darajasi:",
        "options": ["0", "Hiragana-Katakana", "N5 o‘rtasi", "N5 tugatgan", "N4 o‘rtasi"],
        "input_type": "choice",
    },
    {
        "key": "study_reason",
        "prompt": "Nima sababdan o‘rganmoqchisiz?",
        "input_type": "text",
    },
    {
        "key": "gender",
        "prompt": "Jins:",
        "options": ["Erkak", "Ayol"],
        "input_type": "choice",
    },
]

FLOW_JLPT = [
    {
        "key": "jlpt_level",
        "prompt": "JLPT darajasi:",
        "options": ["N1", "N2", "N3", "N4/5", "Yo‘q"],
        "input_type": "choice",
    },
    {"key": "age", "prompt": "Yoshingiz:", "input_type": "age"},
    {
        "key": "graduated_place",
        "prompt": "Qayerni bitirgansiz?",
        "options": ["Yapon tili padkurs", "Maktab", "Universitet"],
        "input_type": "choice",
    },
    {"key": "graduation_year", "prompt": "Bitirgan yil:", "input_type": "year"},
    {
        "key": "certificates",
        "prompt": "Qo‘shimcha sertifikatlar:",
        "options": ["SAT", "EJU", "IELTS", "Yo‘q"],
        "input_type": "choice",
    },
    {"key": "study_field", "prompt": "Qaysi yo‘nalish?", "input_type": "text"},
    {
        "key": "grades",
        "prompt": "Baholar (%):",
        "options": ["90-100", "80-90", "70-80", "70 dan past"],
        "input_type": "choice",
    },
    {
        "key": "region_preference",
        "prompt": "Qayerda o‘qiy olasiz?",
        "options": ["Istalgan joy", "Faqat Tokio", "Faqat katta shaharlar"],
        "input_type": "choice",
    },
    {"key": "extra_comment", "prompt": "Izoh:", "input_type": "text"},
]

FLOW_NO_CERT = [
    {
        "key": "certificate_level",
        "prompt": "Qaysi sertifikat bor?",
        "options": ["N3", "N4", "N5", "Yo‘q"],
        "input_type": "choice",
    },
    {"key": "age", "prompt": "Yoshingiz:", "input_type": "age"},
    {
        "key": "graduated_place",
        "prompt": "Oxirgi bitirgan joyingiz?",
        "options": ["Maktab", "Universitet"],
        "input_type": "choice",
    },
    {"key": "graduation_year", "prompt": "Bitirgan yil:", "input_type": "year"},
    {
        "key": "certificates",
        "prompt": "Sertifikatlar:",
        "options": ["SAT", "EJU", "IELTS", "Yo‘q"],
        "input_type": "choice",
    },
    {
        "key": "after_language_plan",
        "prompt": "Til maktabidan keyin nima o‘qimoqchisiz?",
        "input_type": "text",
    },
    {
        "key": "grades",
        "prompt": "Baholar (%):",
        "options": ["90-100", "80-90", "70-80", "70 dan past"],
        "input_type": "choice",
    },
    {
        "key": "region_preference",
        "prompt": "Qayerda o‘qiy olasiz?",
        "options": ["Istalgan joy", "Faqat Tokio", "Faqat katta shaharlar"],
        "input_type": "choice",
    },
    {
        "key": "why_language_school",
        "prompt": "Nega to‘g‘ridan-to‘g‘ri ishlash emas, til maktabi?",
        "input_type": "text",
    },
    {"key": "extra_comment", "prompt": "Izoh:", "input_type": "text"},
]

FLOW_BY_SERVICE = {
    SERVICE_ONLINE_JP: FLOW_ONLINE_JP,
    SERVICE_JLPT_SENMON: FLOW_JLPT,
    SERVICE_JLPT_UNI: FLOW_JLPT,
    SERVICE_NO_CERT_SCHOOL: FLOW_NO_CERT,
    SERVICE_NO_CERT_SCHOOL_ALT: FLOW_NO_CERT,
}


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def make_keyboard(options: list[str]) -> ReplyKeyboardMarkup:
    """Return one-button-per-row keyboard for clear user selection."""
    return ReplyKeyboardMarkup(
        [[option] for option in options], resize_keyboard=True, one_time_keyboard=True
    )


def init_flow(context: ContextTypes.DEFAULT_TYPE, questions: list[dict]) -> None:
    context.user_data["questions"] = questions
    context.user_data["question_index"] = 0
    context.user_data.setdefault("answers", {})


def get_current_question(context: ContextTypes.DEFAULT_TYPE) -> dict | None:
    questions = context.user_data.get("questions")
    idx = context.user_data.get("question_index", 0)
    if not questions or idx >= len(questions):
        return None
    return questions[idx]


def validate_answer(question: dict, user_input: str) -> tuple[bool, str]:
    text = user_input.strip()
    if not text:
        return False, "Javob bo‘sh bo‘lishi mumkin emas."

    options = question.get("options")
    if options and text not in options:
        return False, "Iltimos, tugmalardan birini tanlang."

    input_type = question.get("input_type", "text")
    if input_type == "age":
        if not text.isdigit():
            return False, "Yosh faqat raqam bo‘lishi kerak (masalan: 19)."
        age = int(text)
        if age < 10 or age > 80:
            return False, "Yosh 10 dan 80 gacha bo‘lishi kerak."
        return True, str(age)

    if input_type == "year":
        if not text.isdigit():
            return False, "Yil faqat raqam bo‘lishi kerak (masalan: 2024)."
        year = int(text)
        current_year = datetime.now().year
        if year < 1950 or year > current_year + 2:
            return False, f"Yil 1950 va {current_year + 2} oralig‘ida bo‘lishi kerak."
        return True, str(year)

    return True, text


def first_available(answers: dict, keys: list[str], default: str = "-") -> str:
    for key in keys:
        value = answers.get(key)
        if value:
            return str(value)
    return default


def build_additional_info(answers: dict) -> str:
    parts = []

    if answers.get("study_reason"):
        parts.append(f"O‘rganish sababi: {answers['study_reason']}")
    if answers.get("gender"):
        parts.append(f"Jins: {answers['gender']}")
    if answers.get("completed_degree"):
        parts.append(f"Bitirgan daraja: {answers['completed_degree']}")
    if answers.get("research_paper"):
        parts.append(f"Ilmiy ish: {answers['research_paper']}")
    if answers.get("why_language_school"):
        parts.append(f"Til maktabi sababi: {answers['why_language_school']}")
    if answers.get("extra_comment"):
        parts.append(f"Izoh: {answers['extra_comment']}")

    return " | ".join(parts) if parts else "-"


def build_group_message(user, service: str, answers: dict) -> str:
    tashkent_time = datetime.now(ZoneInfo("Asia/Tashkent")).strftime("%Y-%m-%d %H:%M:%S")
    username = f"@{user.username}" if user.username else "yo‘q"

    degree = answers.get("degree")
    if not degree and service == SERVICE_ONLINE_JP:
        degree = "Onlayn kurs"
    if not degree and service == SERVICE_NO_CERT_SCHOOL:
        degree = "Til maktabi"
    degree = degree or "-"

    ielts_or_jlpt = first_available(
        answers, ["ielts_level", "jlpt_level", "certificate_level", "japanese_level"]
    )

    chosen_field = first_available(answers, ["study_field", "after_language_plan"])

    additional_info = build_additional_info(answers)

    full_name = user.full_name or "Noma’lum"

    return (
        "📌 <b>YANGI ARIZA</b>\n\n"
        f"👤 <b>Ismi:</b> {escape(full_name)}\n"
        f"📚 <b>Yo‘nalish turi:</b> {escape(service)}\n"
        f"🎓 <b>Daraja:</b> {escape(degree)}\n"
        f"📊 <b>IELTS/JLPT:</b> {escape(ielts_or_jlpt)}\n"
        f"🎂 <b>Yosh:</b> {escape(first_available(answers, ['age']))}\n"
        f"🏫 <b>Bitirgan joy:</b> {escape(first_available(answers, ['graduated_place']))}\n"
        f"📅 <b>Bitirgan yil:</b> {escape(first_available(answers, ['graduation_year']))}\n"
        f"📑 <b>Sertifikatlar:</b> {escape(first_available(answers, ['certificates']))}\n"
        f"📖 <b>Tanlagan yo‘nalish:</b> {escape(chosen_field)}\n"
        f"📈 <b>Baholar:</b> {escape(first_available(answers, ['grades']))}\n"
        f"📍 <b>Hudud tanlovi:</b> {escape(first_available(answers, ['region_preference']))}\n"
        f"📝 <b>Qo‘shimcha ma’lumot:</b> {escape(additional_info)}\n\n"
        f"🔗 <b>Telegram username:</b> {escape(username)}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"⏰ <b>Vaqt:</b> {escape(tashkent_time)}"
    )


async def ask_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    question = get_current_question(context)
    if not question:
        return await finish_form(update, context)

    questions = context.user_data["questions"]
    idx = context.user_data["question_index"]
    total = len(questions)

    text = f"{idx + 1}/{total} savol\n{question['prompt']}"

    if question.get("options"):
        await update.effective_message.reply_text(
            text,
            reply_markup=make_keyboard(question["options"]),
        )
    else:
        await update.effective_message.reply_text(text, reply_markup=ReplyKeyboardRemove())

    return ANSWER_QUESTION


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()

    await update.effective_message.reply_text(
        "Assalomu alaykum! 🇯🇵\nXizmatni tanlang.",
        reply_markup=make_keyboard(SERVICES),
    )
    return SERVICE_CHOICE


async def service_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    selected_service = update.effective_message.text.strip()
    if selected_service == SERVICE_NO_CERT_SCHOOL_ALT:
        selected_service = SERVICE_NO_CERT_SCHOOL

    if selected_service not in SERVICES:
        await update.effective_message.reply_text(
            "Iltimos, pastdagi tugmalardan birini tanlang.",
            reply_markup=make_keyboard(SERVICES),
        )
        return SERVICE_CHOICE

    context.user_data["service"] = selected_service
    context.user_data["answers"] = {}

    if selected_service == SERVICE_IELTS_UNI:
        await update.effective_message.reply_text(
            "Qaysi daraja?",
            reply_markup=make_keyboard(IELTS_DEGREES),
        )
        return IELTS_DEGREE_CHOICE

    init_flow(context, FLOW_BY_SERVICE[selected_service])
    return await ask_next_question(update, context)


async def ielts_degree_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    selected_degree = update.effective_message.text.strip()

    if selected_degree not in IELTS_DEGREES:
        await update.effective_message.reply_text(
            "Iltimos, darajani tugmalardan tanlang.",
            reply_markup=make_keyboard(IELTS_DEGREES),
        )
        return IELTS_DEGREE_CHOICE

    context.user_data["answers"]["degree"] = selected_degree

    if selected_degree == "Bakalavr":
        init_flow(context, FLOW_IELTS_BACHELOR)
    else:
        init_flow(context, FLOW_IELTS_GRAD_PHD)

    return await ask_next_question(update, context)


async def answer_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    question = get_current_question(context)
    if not question:
        await update.effective_message.reply_text(
            "Sessiya topilmadi. Iltimos, /start buyrug‘i bilan qayta boshlang."
        )
        return ConversationHandler.END

    user_text = update.effective_message.text
    is_valid, cleaned = validate_answer(question, user_text)

    if not is_valid:
        retry_text = (
            f"{cleaned}\n\n"
            f"{context.user_data['question_index'] + 1}/{len(context.user_data['questions'])} savol\n"
            f"{question['prompt']}"
        )
        if question.get("options"):
            await update.effective_message.reply_text(
                retry_text,
                reply_markup=make_keyboard(question["options"]),
            )
        else:
            await update.effective_message.reply_text(
                retry_text, reply_markup=ReplyKeyboardRemove()
            )
        return ANSWER_QUESTION

    context.user_data["answers"][question["key"]] = cleaned
    context.user_data["question_index"] += 1

    if context.user_data["question_index"] >= len(context.user_data["questions"]):
        return await finish_form(update, context)

    return await ask_next_question(update, context)


async def finish_form(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    service = context.user_data.get("service", "-")
    answers = context.user_data.get("answers", {})
    group_chat_id = context.bot_data.get("group_chat_id")

    if not group_chat_id:
        logger.error("GROUP_CHAT_ID sozlanmagan.")
        await update.effective_message.reply_text(
            "Texnik xatolik: guruh chat ID topilmadi. Iltimos, admin bilan bog‘laning."
        )
        context.user_data.clear()
        return ConversationHandler.END

    message_text = build_group_message(update.effective_user, service, answers)

    try:
        await context.bot.send_message(
            chat_id=group_chat_id,
            text=message_text,
            parse_mode=ParseMode.HTML,
        )
    except TelegramError:
        logger.exception("Guruhga xabar yuborishda xatolik yuz berdi.")
        await update.effective_message.reply_text(
            "Kechirasiz, ma’lumotni yuborishda muammo bo‘ldi. Iltimos, /start bilan qayta urinib ko‘ring.",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data.clear()
        return ConversationHandler.END

    await update.effective_message.reply_text(
        "Rahmat! Arizangiz qabul qilindi. Tez orada siz bilan bog‘lanamiz.\n\n"
        "Yangi ariza yuborish uchun /start buyrug‘ini bosing.",
        reply_markup=ReplyKeyboardRemove(),
    )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_message.reply_text(
        "Suhbat bekor qilindi. Qayta boshlash uchun /start buyrug‘ini yuboring.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Bu buyruq mavjud emas. Qayta boshlash uchun /start buyrug‘idan foydalaning."
    )


async def unexpected_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Iltimos, matn kiriting yoki tugmalardan birini tanlang."
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Yangilanishni qayta ishlashda xatolik:", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Texnik xatolik yuz berdi. Iltimos, /start buyrug‘i bilan qayta urinib ko‘ring."
        )


def build_application(bot_token: str, group_chat_id: str) -> Application:
    application = Application.builder().token(bot_token).build()
    application.bot_data["group_chat_id"] = group_chat_id

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SERVICE_CHOICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, service_chosen),
                MessageHandler(~filters.TEXT & ~filters.COMMAND, unexpected_non_text),
            ],
            IELTS_DEGREE_CHOICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ielts_degree_chosen),
                MessageHandler(~filters.TEXT & ~filters.COMMAND, unexpected_non_text),
            ],
            ANSWER_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, answer_question),
                MessageHandler(~filters.TEXT & ~filters.COMMAND, unexpected_non_text),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,
    )

    application.add_handler(conversation_handler)
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    application.add_error_handler(error_handler)

    return application


def run() -> None:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN")
    group_chat_id = os.getenv("GROUP_CHAT_ID")

    if not bot_token:
        raise RuntimeError("BOT_TOKEN topilmadi. .env yoki Railway env ga BOT_TOKEN kiriting.")
    if not group_chat_id:
        raise RuntimeError(
            "GROUP_CHAT_ID topilmadi. .env yoki Railway env ga GROUP_CHAT_ID kiriting."
        )

    application = build_application(bot_token, group_chat_id)

    port = int(os.getenv("PORT", "8080"))

    webhook_base = os.getenv("WEBHOOK_BASE_URL")
    railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    if not webhook_base and railway_domain:
        webhook_base = f"https://{railway_domain}"

    if webhook_base:
        webhook_path = os.getenv("WEBHOOK_PATH", bot_token).lstrip("/")
        webhook_url = f"{webhook_base.rstrip('/')}/{webhook_path}"
        secret_token = os.getenv("WEBHOOK_SECRET")

        webhook_kwargs = {
            "listen": "0.0.0.0",
            "port": port,
            "url_path": webhook_path,
            "webhook_url": webhook_url,
            "drop_pending_updates": True,
            "allowed_updates": Update.ALL_TYPES,
        }
        if secret_token:
            webhook_kwargs["secret_token"] = secret_token

        logger.info("Webhook rejimi ishga tushmoqda: %s", webhook_url)
        application.run_webhook(**webhook_kwargs)
    else:
        logger.info("WEBHOOK_BASE_URL topilmadi. Polling rejimi ishga tushmoqda.")
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
        )


if __name__ == "__main__":
    run()
