from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineQueryResultArticle, InputTextMessageContent, constants
from telegram.helpers import escape_markdown
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, InlineQueryHandler
import requests
import datetime
from babel.dates import format_date
import os.path
import re

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    languages = context.bot_data["api"].languages.copy()
    for i in range(0, len(languages)):
        languages[i] = [KeyboardButton(languages[i]["english_name"])]

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="What language do you want your results in?",
        reply_markup=ReplyKeyboardMarkup(languages, one_time_keyboard=True)
    )

    return 0

async def filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Genres to exclude
    genres = context.bot_data["api"].genres.copy()
    db = context.bot_data["db"]
    chat = db.getChat(update.effective_chat.id)

    keyboard = []
    for genre in genres:
        if genre["id"] in chat.excluded_genres:
            keyboard.append([InlineKeyboardButton(genre["name"] + " (excluded)", callback_data="remove_genre_" + str(genre["id"]))])
        else:
            keyboard.append([InlineKeyboardButton(genre["name"], callback_data="add_genre_" + str(genre["id"]))])

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="What genres do you want to exclude from your results?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return 0

async def filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    api = context.bot_data["api"]
    genres = api.genres.copy()
    db = context.bot_data["db"]
    chat = db.getChat(update.effective_chat.id)

    if query.data.startswith("add_genre_"):
        genre_id = int(query.data.split("_")[2])
        chat.excluded_genres.append(genre_id)
        db.setExcludedGenres(update.effective_chat.id, chat.excluded_genres)
    elif query.data.startswith("remove_genre_"):
        genre_id = int(query.data.split("_")[2])
        if genre_id in chat.excluded_genres:
            chat.excluded_genres.remove(genre_id)
        db.setExcludedGenres(update.effective_chat.id, chat.excluded_genres)

    keyboard = []
    for genre in genres:
        if genre["id"] in chat.excluded_genres:
            keyboard.append([InlineKeyboardButton(genre["name"] + " (excluded)", callback_data="remove_genre_" + str(genre["id"]))])
        else:
            keyboard.append([InlineKeyboardButton(genre["name"], callback_data="add_genre_" + str(genre["id"]))])

    await query.edit_message_text(
        text="What genres do you want to exclude from your results?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return 0

async def country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    languages = context.bot_data["api"].languages
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
    number = 10
    db = context.bot_data["db"]
    chat = db.getChat(update.effective_chat.id)

    upcoming = context.bot_data["api"].getUpcomingMovies(**chat.getQueryParams())
    upcoming = upcoming["results"]
    upcoming.sort(key=lambda x: x["popularity"], reverse=True)
    upcoming = upcoming[:10]
    upcoming.sort(key=lambda x: x["release_date"])

    buttons = []
    
    for i in range(0, min(number, len(upcoming))):
        movie = upcoming[i]
        date = datetime.datetime.strptime(movie["release_date"], "%Y-%m-%d")
        date = format_date(date, locale=chat.language.split("-")[0])
        buttons.append([InlineKeyboardButton(movie["title"] + " (" +  date + ")", callback_data="movie_" + str(movie["id"]))])
    


    await context.bot.send_message(
        update.effective_chat.id,
        "Upcoming movies" + (" (some genres are excluded, use /filter to change that)" if chat.excluded_genres else "" ) + ":",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def now_playing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.bot_data["db"]
    chat = db.getChat(update.effective_chat.id)

    current = context.bot_data["api"].getNowPlayingMovies(**chat.getQueryParams())
    current = current["results"]
    current.sort(key=lambda x: x["popularity"], reverse=True)

    buttons = []
    
    for i in range(0, min(10, len(current))):
        movie = current[i]
        date = datetime.datetime.strptime(movie["release_date"], "%Y-%m-%d")
        date = format_date(date, locale=chat.language.split("-")[0])
        buttons.append([InlineKeyboardButton(movie["title"] + " (" +  date + ")", callback_data="movie_" + str(movie["id"]))])
    
    await context.bot.send_message(
        update.effective_chat.id,
        "Currently playing movies" + ( " (some genres are excluded, use /filter to change that)" if chat.excluded_genres else "" ) + ":",
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
        if overview_eng["overview"] != "":
            movie["overview"] = "There was no description in you language available, so here is the english one:\n\n" + overview_eng["overview"]
        else:
            movie["overview"] = "There was no description available for this movie."

    age_rating = "Not available"
    for release_date in movie["release_dates"]["results"]:
        if release_date["iso_3166_1"].lower() == chat.country.lower():
            certification = release_date["release_dates"][0]["certification"]
            if certification != "":
                age_rating = certification
            break
    
    # TODO locale specific datestring in seperate function
    release_date = format_date(datetime.datetime.strptime(movie["release_date"], "%Y-%m-%d"), locale=chat.language.split("-")[0])
    cast = movie["credits"]["cast"]
    director = [crew["name"] for crew in movie["credits"]["crew"] if crew["job"] == "Director"]

    caption = \
        "*" + escape_markdown(movie["title"], version=2) + "*" + "\n" + \
        escape_markdown(movie["overview"], version=2) + "\n\n" + \
        "*Cast*: " + \
            escape_markdown(", ".join([cast[i]["name"] for i in range(0, min(3, len(cast)))]), version=2) + \
        "\n*Directed by*: " + \
            escape_markdown(", ".join(director), version=2) + \
        "\n*Age rating*: " + \
            escape_markdown(age_rating + " (" + chat.country + ")",version=2) + \
        "\n*Release date*: " + \
            escape_markdown(release_date + " (" + chat.country + ")", version=2 )
    
    if movie["poster_path"] == None:
        await context.bot.send_message(
            update.effective_chat.id,
            caption
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
        caption=caption,
        parse_mode=constants.ParseMode.MARKDOWN_V2
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
        print(chat.language)
        date = format_date(date, locale=chat.language.split("-")[0])
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
        entry_points=[CommandHandler("start", settings), CommandHandler("settings", settings)],
        states={
            0: [MessageHandler(filters.Regex(re.compile(f"^({language_regex})$", re.IGNORECASE)), country)],
            1: [MessageHandler(filters.Regex(re.compile(f"^({region_regex})$", re.IGNORECASE)), done)]
        },
        fallbacks=[MessageHandler(filters.ALL, fallback)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("upcoming", upcoming))
    app.add_handler(CommandHandler("nowplaying", now_playing))
    app.add_handler(CommandHandler("filter", filter))
    app.add_handler(CallbackQueryHandler(movie, pattern="movie_.*"))
    app.add_handler(CallbackQueryHandler(filter_callback, pattern=".*_genre_.*"))
    app.add_handler(InlineQueryHandler(inline))