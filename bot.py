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
LANGUAGE_CHOICE, SERVICE_CHOICE, IELTS_DEGREE_CHOICE, ANSWER_QUESTION = range(4)


# Services
SERVICE_IELTS_UNI = "IELTS bilan Yaponiyada Universitet"
SERVICE_JLPT_SENMON = "JLPT bilan 専門学校"
SERVICE_JLPT_UNI = "JLPT bilan Universitet"
SERVICE_NO_CERT_SCHOOL = "Til sertifikatisiz Yapon tili maktabi"
SERVICE_NO_CERT_SCHOOL_ALT = "Til sertifikatisiz Yapon tili maktabi"

SERVICES = [
    SERVICE_IELTS_UNI,
    SERVICE_JLPT_SENMON,
    SERVICE_JLPT_UNI,
    SERVICE_NO_CERT_SCHOOL,
]

IELTS_DEGREES = ["Bakalavr", "Magistratura", "PhD"]

DEFAULT_LANGUAGE = "uz"

LANGUAGE_OPTIONS = {
    "English": "en",
    "Русский": "ru",
    "O‘zbek": "uz",
}

LANGUAGE_NAMES = {
    "en": "English",
    "ru": "Русский",
    "uz": "O‘zbek",
}

LANGUAGE_PROMPT = "Please choose your language.\nВыберите язык.\nTilni tanlang."

SERVICE_TRANSLATIONS = {
    SERVICE_IELTS_UNI: {
        "en": "University in Japan with IELTS",
        "ru": "Университет в Японии с IELTS",
        "uz": "IELTS bilan Yaponiyada Universitet",
    },
    SERVICE_JLPT_SENMON: {
        "en": "Vocational school in Japan with JLPT",
        "ru": "Профессиональная школа в Японии с JLPT",
        "uz": "JLPT bilan Yaponiyada senmon maktab",
    },
    SERVICE_JLPT_UNI: {
        "en": "University in Japan with JLPT",
        "ru": "Университет в Японии с JLPT",
        "uz": "JLPT bilan Universitet",
    },
    SERVICE_NO_CERT_SCHOOL: {
        "en": "Japanese language school in Japan without a certificate",
        "ru": "Школа японского языка в Японии без сертификата",
        "uz": "Til sertifikatisiz Yapon tili maktabi",
    },
}

DEGREE_TRANSLATIONS = {
    "Bakalavr": {"en": "Bachelor", "ru": "Бакалавриат", "uz": "Bakalavr"},
    "Magistratura": {"en": "Master's", "ru": "Магистратура", "uz": "Magistratura"},
    "PhD": {"en": "PhD", "ru": "PhD", "uz": "PhD"},
}

TEXTS = {
    "en": {
        "choose_service": "Hello! Please choose the service you are interested in.",
        "choose_degree": "Which degree are you interested in?",
        "choose_button": "Please choose one of the buttons below.",
        "choose_degree_button": "Please choose a degree using the buttons.",
        "empty_answer": "The answer cannot be empty.",
        "age_numeric": "Age must be a number (for example: 19).",
        "age_range": "Age must be between 10 and 80.",
        "year_numeric": "Year must be a number (for example: 2024).",
        "year_range": "Year must be between 1950 and {max_year}.",
        "question_label": "{number}-question",
        "session_missing": "Session not found. Please restart with /start.",
        "missing_group": "Technical error: group chat ID was not found. Please contact the admin.",
        "send_error": "Sorry, there was a problem sending your information. Please try again with /start.",
        "done": (
            "Thank you! Your inquiry has been received. We will contact you soon.\n\n"
            "If we do not reply within 3 days, please message @maeda_jpn."
        ),
        "cancel": "The conversation was cancelled. Send /start to begin again.",
        "unknown_command": "This command does not exist. Please use /start to begin again.",
        "non_text": "Please enter text or choose one of the buttons.",
        "technical_error": "A technical error occurred. Please try again with /start.",
    },
    "ru": {
        "choose_service": "Здравствуйте! Выберите интересующую услугу.",
        "choose_degree": "Какая степень вас интересует?",
        "choose_button": "Пожалуйста, выберите один из вариантов ниже.",
        "choose_degree_button": "Пожалуйста, выберите степень с помощью кнопок.",
        "empty_answer": "Ответ не может быть пустым.",
        "age_numeric": "Возраст должен быть числом (например: 19).",
        "age_range": "Возраст должен быть от 10 до 80.",
        "year_numeric": "Год должен быть числом (например: 2024).",
        "year_range": "Год должен быть между 1950 и {max_year}.",
        "question_label": "{number}-вопрос",
        "session_missing": "Сессия не найдена. Пожалуйста, начните заново с /start.",
        "missing_group": "Техническая ошибка: ID группового чата не найден. Пожалуйста, свяжитесь с администратором.",
        "send_error": "Извините, возникла проблема при отправке информации. Пожалуйста, попробуйте снова через /start.",
        "done": (
            "Спасибо! Ваша заявка принята. Мы скоро с вами свяжемся.\n\n"
            "Если мы не ответим в течение 3 дней, напишите @maeda_jpn."
        ),
        "cancel": "Диалог отменен. Отправьте /start, чтобы начать заново.",
        "unknown_command": "Такой команды нет. Используйте /start, чтобы начать заново.",
        "non_text": "Пожалуйста, введите текст или выберите один из вариантов.",
        "technical_error": "Произошла техническая ошибка. Пожалуйста, попробуйте снова через /start.",
    },
    "uz": {
        "choose_service": "Assalomu alaykum! Xizmatni tanlang.",
        "choose_degree": "Qaysi daraja?",
        "choose_button": "Iltimos, pastdagi tugmalardan birini tanlang.",
        "choose_degree_button": "Iltimos, darajani tugmalardan tanlang.",
        "empty_answer": "Javob bo‘sh bo‘lishi mumkin emas.",
        "age_numeric": "Yosh faqat raqam bo‘lishi kerak (masalan: 19).",
        "age_range": "Yosh 10 dan 80 gacha bo‘lishi kerak.",
        "year_numeric": "Yil faqat raqam bo‘lishi kerak (masalan: 2024).",
        "year_range": "Yil 1950 va {max_year} oralig‘ida bo‘lishi kerak.",
        "question_label": "{number}-savol",
        "session_missing": "Sessiya topilmadi. Iltimos, /start buyrug‘i bilan qayta boshlang.",
        "missing_group": "Texnik xatolik: guruh chat ID topilmadi. Iltimos, admin bilan bog‘laning.",
        "send_error": "Kechirasiz, ma’lumotni yuborishda muammo bo‘ldi. Iltimos, /start bilan qayta urinib ko‘ring.",
        "done": (
            "Rahmat! Arizangiz qabul qilindi. Tez orada siz bilan bog‘lanamiz.\n\n"
            "Sizga 3 kun ichida javob bermasak, @maeda_jpn ga yozing."
        ),
        "cancel": "Suhbat bekor qilindi. Qayta boshlash uchun /start buyrug‘ini yuboring.",
        "unknown_command": "Bu buyruq mavjud emas. Qayta boshlash uchun /start buyrug‘idan foydalaning.",
        "non_text": "Iltimos, matn kiriting yoki tugmalardan birini tanlang.",
        "technical_error": "Texnik xatolik yuz berdi. Iltimos, /start buyrug‘i bilan qayta urinib ko‘ring.",
    },
}

QUESTION_TRANSLATIONS = {
    "Qaysi davlatdan murojaat qilyapsiz?": {
        "en": "Which country are you applying from?",
        "ru": "Из какой страны вы обращаетесь?",
    },
    "IELTS darajasi:": {"en": "IELTS level:", "ru": "Уровень IELTS:"},
    "Yoshingiz:": {"en": "Your age:", "ru": "Ваш возраст:"},
    "Qayerni bitirgansiz?": {"en": "What did you graduate from?", "ru": "Что вы окончили?"},
    "Qachon bitirgansiz? (yil)": {"en": "Graduation year:", "ru": "Год окончания:"},
    "Bitirgan yil:": {"en": "Graduation year:", "ru": "Год окончания:"},
    "Sertifikatlaringiz:": {"en": "Certificates:", "ru": "Сертификаты:"},
    "Sertifikatlar:": {"en": "Certificates:", "ru": "Сертификаты:"},
    "Qo‘shimcha sertifikatlar:": {
        "en": "Additional certificates:",
        "ru": "Дополнительные сертификаты:",
    },
    "Qaysi yo‘nalishda o‘qimoqchisiz?": {
        "en": "What field would you like to study?",
        "ru": "По какому направлению хотите учиться?",
    },
    "Yo‘nalish:": {"en": "Field:", "ru": "Направление:"},
    "Qaysi yo‘nalish?": {
        "en": "What field would you like to study?",
        "ru": "По какому направлению хотите учиться?",
    },
    "Baholaringiz qanday?": {"en": "How are your grades?", "ru": "Какие у вас оценки?"},
    "Baholar:": {"en": "Grades:", "ru": "Оценки:"},
    "Baholar (%):": {"en": "Grades (%):", "ru": "Оценки (%):"},
    "Qo‘shimcha savol yoki izoh:": {
        "en": "Additional question or comment:",
        "ru": "Дополнительный вопрос или комментарий:",
    },
    "Izoh:": {"en": "Comment:", "ru": "Комментарий:"},
    "Qaysi darajani bitirgansiz?": {
        "en": "Which degree have you completed?",
        "ru": "Какую степень вы окончили?",
    },
    "Ilmiy ish yozganmisiz?": {
        "en": "Have you written a research paper?",
        "ru": "Писали ли вы научную работу?",
    },
    "JLPT darajasi:": {"en": "JLPT level:", "ru": "Уровень JLPT:"},
    "Qayerda o‘qiy olasiz?": {
        "en": "Where in Japan can you study?",
        "ru": "Где в Японии вы можете учиться?",
    },
    "Qaysi sertifikat bor?": {
        "en": "Which certificate do you have?",
        "ru": "Какой сертификат у вас есть?",
    },
    "Oxirgi bitirgan joyingiz?": {
        "en": "What is the last institution you graduated from?",
        "ru": "Какое последнее учебное заведение вы окончили?",
    },
    "Til maktabidan keyin nima o‘qimoqchisiz?": {
        "en": "What would you like to study after language school?",
        "ru": "Что вы хотите изучать после языковой школы?",
    },
    "Nega to‘g‘ridan-to‘g‘ri ishlash emas, til maktabi?": {
        "en": "Why do you want language school instead of working directly?",
        "ru": "Почему вы выбираете языковую школу, а не работу напрямую?",
    },
}

OPTION_TRANSLATIONS = {
    "Yo‘q": {"en": "No", "ru": "Нет"},
    "Ha": {"en": "Yes", "ru": "Да"},
    "5.5 yoki past": {"en": "5.5 or lower", "ru": "5.5 или ниже"},
    "Maktab": {"en": "School", "ru": "Школа"},
    "Universitet": {"en": "University", "ru": "Университет"},
    "Yapon tili padkurs": {
        "en": "Japanese language preparatory course",
        "ru": "Подготовительный курс японского языка",
    },
    "Asosan 5": {"en": "Mostly excellent", "ru": "В основном отлично"},
    "4-5": {"en": "Good and excellent", "ru": "Хорошо и отлично"},
    "Asosan 4": {"en": "Mostly good", "ru": "В основном хорошо"},
    "3-4": {"en": "Average to good", "ru": "Средне и хорошо"},
    "Bakalavr": {"en": "Bachelor", "ru": "Бакалавриат"},
    "Magistratura": {"en": "Master's", "ru": "Магистратура"},
    "70 dan past": {"en": "Below 70", "ru": "Ниже 70"},
    "Istalgan joy": {"en": "Anywhere", "ru": "Любой регион"},
    "Faqat Tokio": {"en": "Tokyo only", "ru": "Только Токио"},
    "Faqat katta shaharlar": {
        "en": "Large cities only",
        "ru": "Только крупные города",
    },
}

COUNTRY_QUESTION = {
    "key": "country",
    "prompt": "Qaysi davlatdan murojaat qilyapsiz?",
    "input_type": "text",
}


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
    SERVICE_JLPT_SENMON: FLOW_JLPT,
    SERVICE_JLPT_UNI: FLOW_JLPT,
    SERVICE_NO_CERT_SCHOOL: FLOW_NO_CERT,
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


def get_language(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("language", DEFAULT_LANGUAGE)


def get_text(lang: str, key: str, **kwargs) -> str:
    return TEXTS.get(lang, TEXTS[DEFAULT_LANGUAGE])[key].format(**kwargs)


def translate_value(value: str, lang: str, translations: dict[str, dict[str, str]]) -> str:
    if lang == DEFAULT_LANGUAGE:
        return value
    return translations.get(value, {}).get(lang, value)


def language_keyboard() -> ReplyKeyboardMarkup:
    return make_keyboard(list(LANGUAGE_OPTIONS.keys()))


def service_labels(lang: str) -> list[str]:
    return [SERVICE_TRANSLATIONS[service][lang] for service in SERVICES]


def service_from_label(label: str, lang: str) -> str | None:
    for service in SERVICES:
        if label == SERVICE_TRANSLATIONS[service][lang] or label == service:
            return service
    return None


def degree_labels(lang: str) -> list[str]:
    return [DEGREE_TRANSLATIONS[degree][lang] for degree in IELTS_DEGREES]


def degree_from_label(label: str, lang: str) -> str | None:
    for degree in IELTS_DEGREES:
        if label == DEGREE_TRANSLATIONS[degree][lang] or label == degree:
            return degree
    return None


def localize_question(question: dict, lang: str) -> dict:
    localized = question.copy()
    localized["prompt"] = translate_value(question["prompt"], lang, QUESTION_TRANSLATIONS)
    if question.get("options"):
        localized["options"] = [
            translate_value(option, lang, OPTION_TRANSLATIONS)
            for option in question["options"]
        ]
    return localized


def init_flow(context: ContextTypes.DEFAULT_TYPE, questions: list[dict]) -> None:
    lang = get_language(context)
    localized_questions = [localize_question(COUNTRY_QUESTION, lang)]
    localized_questions.extend(localize_question(question, lang) for question in questions)
    context.user_data["questions"] = localized_questions
    context.user_data["question_index"] = 0
    context.user_data.setdefault("answers", {})


def get_current_question(context: ContextTypes.DEFAULT_TYPE) -> dict | None:
    questions = context.user_data.get("questions")
    idx = context.user_data.get("question_index", 0)
    if not questions or idx >= len(questions):
        return None
    return questions[idx]


def validate_answer(question: dict, user_input: str, lang: str) -> tuple[bool, str]:
    text = user_input.strip()
    if not text:
        return False, get_text(lang, "empty_answer")

    options = question.get("options")
    if options and text not in options:
        return False, get_text(lang, "choose_button")

    input_type = question.get("input_type", "text")
    if input_type == "age":
        if not text.isdigit():
            return False, get_text(lang, "age_numeric")
        age = int(text)
        if age < 10 or age > 80:
            return False, get_text(lang, "age_range")
        return True, str(age)

    if input_type == "year":
        if not text.isdigit():
            return False, get_text(lang, "year_numeric")
        year = int(text)
        current_year = datetime.now(ZoneInfo("Asia/Tashkent")).year
        max_year = current_year + 2
        if year < 1950 or year > max_year:
            return False, get_text(lang, "year_range", max_year=max_year)
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

    if answers.get("completed_degree"):
        parts.append(f"Completed degree: {answers['completed_degree']}")
    if answers.get("research_paper"):
        parts.append(f"Research paper: {answers['research_paper']}")
    if answers.get("why_language_school"):
        parts.append(f"Language school reason: {answers['why_language_school']}")
    if answers.get("extra_comment"):
        parts.append(f"Comment: {answers['extra_comment']}")

    return " | ".join(parts) if parts else "-"


def build_group_message(user, service: str, lang: str, answers: dict) -> str:
    tashkent_time = datetime.now(ZoneInfo("Asia/Tashkent")).strftime("%Y-%m-%d %H:%M:%S")
    username = f"@{user.username}" if user.username else "none"
    service_label = SERVICE_TRANSLATIONS.get(service, {}).get(lang, service)

    degree = answers.get("degree")
    if not degree and service == SERVICE_NO_CERT_SCHOOL:
        degree = service_label
    degree = degree or "-"

    ielts_or_jlpt = first_available(
        answers, ["ielts_level", "jlpt_level", "certificate_level", "japanese_level"]
    )

    chosen_field = first_available(answers, ["study_field", "after_language_plan"])

    additional_info = build_additional_info(answers)

    full_name = user.full_name or "Unknown"

    return (
        "📌 <b>NEW INQUIRY</b>\n\n"
        f"🌐 <b>Language:</b> {escape(LANGUAGE_NAMES.get(lang, lang))}\n"
        f"🌍 <b>Country:</b> {escape(first_available(answers, ['country']))}\n"
        f"👤 <b>Name:</b> {escape(full_name)}\n"
        f"📚 <b>Service:</b> {escape(service_label)}\n"
        f"🎓 <b>Degree:</b> {escape(degree)}\n"
        f"📊 <b>IELTS/JLPT:</b> {escape(ielts_or_jlpt)}\n"
        f"🎂 <b>Age:</b> {escape(first_available(answers, ['age']))}\n"
        f"🏫 <b>Graduated from:</b> {escape(first_available(answers, ['graduated_place']))}\n"
        f"📅 <b>Graduation year:</b> {escape(first_available(answers, ['graduation_year']))}\n"
        f"📑 <b>Certificates:</b> {escape(first_available(answers, ['certificates']))}\n"
        f"📖 <b>Chosen field:</b> {escape(chosen_field)}\n"
        f"📈 <b>Grades:</b> {escape(first_available(answers, ['grades']))}\n"
        f"📍 <b>Region preference:</b> {escape(first_available(answers, ['region_preference']))}\n"
        f"📝 <b>Additional info:</b> {escape(additional_info)}\n\n"
        f"🔗 <b>Telegram username:</b> {escape(username)}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"⏰ <b>Time:</b> {escape(tashkent_time)}"
    )


async def ask_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    question = get_current_question(context)
    if not question:
        return await finish_form(update, context)

    idx = context.user_data["question_index"]
    lang = get_language(context)

    question_label = get_text(lang, "question_label", number=idx + 1)
    text = f"{question_label}\n{question['prompt']}"

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
        LANGUAGE_PROMPT,
        reply_markup=language_keyboard(),
    )
    return LANGUAGE_CHOICE


async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    selected_language = update.effective_message.text.strip()
    lang = LANGUAGE_OPTIONS.get(selected_language)

    if not lang:
        await update.effective_message.reply_text(
            LANGUAGE_PROMPT,
            reply_markup=language_keyboard(),
        )
        return LANGUAGE_CHOICE

    context.user_data["language"] = lang
    return await ask_service(update, context)


async def ask_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_language(context)
    await update.effective_message.reply_text(
        get_text(lang, "choose_service"),
        reply_markup=make_keyboard(service_labels(lang)),
    )
    return SERVICE_CHOICE


async def service_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_language(context)
    selected_service = service_from_label(update.effective_message.text.strip(), lang)

    if not selected_service:
        await update.effective_message.reply_text(
            get_text(lang, "choose_button"),
            reply_markup=make_keyboard(service_labels(lang)),
        )
        return SERVICE_CHOICE

    context.user_data["service"] = selected_service
    context.user_data["answers"] = {}

    if selected_service == SERVICE_IELTS_UNI:
        await update.effective_message.reply_text(
            get_text(lang, "choose_degree"),
            reply_markup=make_keyboard(degree_labels(lang)),
        )
        return IELTS_DEGREE_CHOICE

    init_flow(context, FLOW_BY_SERVICE[selected_service])
    return await ask_next_question(update, context)


async def ielts_degree_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_language(context)
    selected_degree = degree_from_label(update.effective_message.text.strip(), lang)

    if not selected_degree:
        await update.effective_message.reply_text(
            get_text(lang, "choose_degree_button"),
            reply_markup=make_keyboard(degree_labels(lang)),
        )
        return IELTS_DEGREE_CHOICE

    context.user_data["answers"]["degree"] = DEGREE_TRANSLATIONS[selected_degree][lang]

    if selected_degree == "Bakalavr":
        init_flow(context, FLOW_IELTS_BACHELOR)
    else:
        init_flow(context, FLOW_IELTS_GRAD_PHD)

    return await ask_next_question(update, context)


async def answer_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_language(context)
    question = get_current_question(context)
    if not question:
        await update.effective_message.reply_text(get_text(lang, "session_missing"))
        return ConversationHandler.END

    user_text = update.effective_message.text
    is_valid, cleaned = validate_answer(question, user_text, lang)

    if not is_valid:
        question_label = get_text(
            lang,
            "question_label",
            number=context.user_data["question_index"] + 1,
        )
        retry_text = (
            f"{cleaned}\n\n"
            f"{question_label}\n"
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
    lang = get_language(context)
    service = context.user_data.get("service", "-")
    answers = context.user_data.get("answers", {})
    group_chat_id = context.bot_data.get("group_chat_id")

    if not group_chat_id:
        logger.error("GROUP_CHAT_ID is not configured.")
        await update.effective_message.reply_text(get_text(lang, "missing_group"))
        context.user_data.clear()
        return ConversationHandler.END

    message_text = build_group_message(update.effective_user, service, lang, answers)

    try:
        await context.bot.send_message(
            chat_id=group_chat_id,
            text=message_text,
            parse_mode=ParseMode.HTML,
        )
    except TelegramError:
        logger.exception("Failed to send the inquiry to the group.")
        await update.effective_message.reply_text(
            get_text(lang, "send_error"),
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data.clear()
        return ConversationHandler.END

    await update.effective_message.reply_text(
        get_text(lang, "done"),
        reply_markup=ReplyKeyboardRemove(),
    )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_language(context)
    context.user_data.clear()
    await update.effective_message.reply_text(
        get_text(lang, "cancel"),
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_language(context)
    await update.effective_message.reply_text(get_text(lang, "unknown_command"))


async def unexpected_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_language(context)
    await update.effective_message.reply_text(get_text(lang, "non_text"))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Error while processing update:", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        lang = get_language(context)
        await update.effective_message.reply_text(get_text(lang, "technical_error"))


def build_application(bot_token: str, group_chat_id: str) -> Application:
    application = Application.builder().token(bot_token).build()
    application.bot_data["group_chat_id"] = group_chat_id

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE_CHOICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, language_chosen),
                MessageHandler(~filters.TEXT & ~filters.COMMAND, unexpected_non_text),
            ],
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
