from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, InlineQueryHandler
import requests
import datetime
from babel.dates import format_date
import os.path
import re

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    languages = context.bot_data["api"].languages.copy()
    for i in range(0, len(languages)):
        languages[i] = [KeyboardButton(languages[i]["english_name"])]

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="What language do you want your results in?",
        reply_markup=ReplyKeyboardMarkup(languages, one_time_keyboard=True)
    )

    return 0

async def country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    languages = context.bot_data["api"].languages
    print(update.message.text.lower())
    language_iso = next(language['iso_639_1'] for language in languages if language["english_name"].lower() == update.message.text.lower())
    language_iso += "-en"

    db = context.bot_data["db"]
    db.setLanguage(update.effective_chat.id, language_iso)

    countries = context.bot_data["api"].countries.copy()
    for i in range(0, len(countries)):
        countries[i] = [KeyboardButton(countries[i]["english_name"])]

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="What country do you want your release dates to be for?",
        reply_markup=ReplyKeyboardMarkup(countries, one_time_keyboard=True)
    )

    return 1

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I your input was invalid."
    )

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    countries = context.bot_data["api"].countries
    country_iso = next(country['iso_3166_1'] for country in countries if country["english_name"].lower() == update.message.text.lower())
    db = context.bot_data["db"]
    db.setCountry(update.effective_chat.id, country_iso)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Settings saved.",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

async def upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.bot_data["db"]
    chat = db.getChat(update.effective_chat.id)

    upcoming = context.bot_data["api"].getUpcomingMovies(**chat.getQueryParams())
    upcoming = upcoming["results"]
    upcoming.sort(key=lambda x: x["release_date"])

    buttons = []
    
    for i in range(0, min(10, len(upcoming))):
        movie = upcoming[i]
        date = datetime.datetime.strptime(movie["release_date"], "%Y-%m-%d")
        date = format_date(date, format="short", locale=chat.language.split("-")[0])
        buttons.append([InlineKeyboardButton(movie["title"] + " (" +  date + ")", callback_data="movie_" + str(movie["id"]))])
    
    await context.bot.send_message(
        update.effective_chat.id,
        "Upcoming movies:\n",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
async def movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = context.bot_data["db"].getChat(update.effective_chat.id)
    image_size = "original"
    cache_folder = "cache/"
    movie_id = int(update.callback_query.data.split("_")[1])
    movie = context.bot_data["api"].getMovie(movie_id, **chat.getQueryParams())
    if movie["overview"] == "":
        overview_eng = context.bot_data["api"].getMovie(movie_id, language="en-US")
        movie["overview"] = "There was no description in you language available, so here is the english one:\n\n" + overview_eng["overview"]
    if movie["poster_path"] == None:
        await context.bot.send_message(
            update.effective_chat.id,
            movie["overview"]
        )
        return

    if not os.path.exists(cache_folder):
        os.makedirs(cache_folder)
    
    file_path = cache_folder + str(movie_id) + "_" + image_size + movie["poster_path"].split(".")[-1]
    if not os.path.isfile(file_path):
        file_url = context.bot_data["api"].image_base_url + "w154" + movie["poster_path"]
        response = requests.get(file_url)
        with open(file_path, "wb") as f:
            f.write(response.content)
        
    await context.bot.send_photo(
        update.effective_chat.id,
        open(file_path, "rb"),
        caption=movie["overview"],
    )

async def inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if query == "":
        return

    chat = context.bot_data["db"].getChat(update.inline_query.from_user.id)
    country_name = next(country['english_name'] for country in context.bot_data["api"].countries if country["iso_3166_1"] == chat.country)
    results = []
    for movie in context.bot_data["api"].search(query, **chat.getQueryParams())["results"]:
        date = datetime.datetime.strptime(movie["release_date"], "%Y-%m-%d")
        date = format_date(date, format="short", locale=chat.language.split("-")[0])
        results.append(
            InlineQueryResultArticle(
                id=movie["id"],
                title=movie["title"] + " (" +  date + ")",
                input_message_content=InputTextMessageContent(movie["title"] + " release in " + country_name + ": " + date + "."),
                description=movie["overview"],
                thumb_url=context.bot_data["api"].image_base_url + "w154" + movie["poster_path"] if movie["poster_path"] != None else None
            )
        )
    await context.bot.answer_inline_query(update.inline_query.id, results)


def add_handlers(app):
    language = app.bot_data["api"].languages.copy()
    for i in range(0, len(language)):
        language[i] = language[i]["english_name"]
    language_regex = str.join("|", language)

    countries = app.bot_data["api"].countries.copy()
    for i in range(0, len(countries)):
        countries[i] = countries[i]["english_name"] 
    region_regex = str.join("|", countries)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            0: [MessageHandler(filters.Regex(re.compile(f"^({language_regex})$", re.IGNORECASE)), country)],
            1: [MessageHandler(filters.Regex(re.compile(f"^({region_regex})$", re.IGNORECASE)), done)]
        },
        fallbacks=[MessageHandler(filters.ALL, fallback)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("upcoming", upcoming))
    app.add_handler(CallbackQueryHandler(movie, pattern="movie_.*"))
    app.add_handler(InlineQueryHandler(inline))