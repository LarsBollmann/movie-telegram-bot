from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineQueryResultArticle, InputTextMessageContent, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, InlineQueryHandler
import requests
import datetime
import constants
from db import Chat
from moviedbapi import MovieAPI
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
    chat = context.bot_data["db"].getChat(update.effective_chat.id)

    keyboard = [
        [InlineKeyboardButton("Genres" + (" (active)" if chat.excluded_genres else ""), callback_data="filter_genres")],
        #[InlineKeyboardButton("Age rating" + (" (active)" if chat.excluded_ages else ""), callback_data="filter_agerating")],
        [InlineKeyboardButton("Done", callback_data="deletemessage")]
    ]

    if update.callback_query is not None:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.message_id,
            text="Which filter do you want to change?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Which filter do you want to change?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def get_genre_buttons(api, chat):
    genres = api.genres.copy()

    keyboard = []
    for (i, genre) in enumerate(genres):
        if genre["id"] in chat.excluded_genres:
            button = InlineKeyboardButton(genre["name"] + " (excluded)", callback_data="remove_genre_" + str(genre["id"]))
        else:
            button = InlineKeyboardButton(genre["name"], callback_data="add_genre_" + str(genre["id"]))
        if i % 2 == 0:
            keyboard.append([button])
        else:
            keyboard[-1].append(button)

    keyboard.append([InlineKeyboardButton("Done", callback_data="filter")])

    return keyboard

async def filter_genres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Genres to exclude
    db = context.bot_data["db"]
    chat = db.getChat(update.effective_chat.id)

    keyboard = get_genre_buttons(context.bot_data["api"], chat)

    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.message_id,
        text="What genres do you want to exclude from your results?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def filter_genres_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    api = context.bot_data["api"]
    genres = api.genres.copy()
    db = context.bot_data["db"]
    chat = db.getChat(update.effective_chat.id)

    if query.data.startswith("add_genre_"):
        genre_id = int(query.data.split("_")[2])
        if genre_id not in chat.excluded_genres:
            chat.excluded_genres.append(genre_id)
        db.setExcludedGenres(update.effective_chat.id, chat.excluded_genres)
    elif query.data.startswith("remove_genre_"):
        genre_id = int(query.data.split("_")[2])
        if genre_id in chat.excluded_genres:
            chat.excluded_genres.remove(genre_id)
        db.setExcludedGenres(update.effective_chat.id, chat.excluded_genres)

    keyboard = get_genre_buttons(api, chat)

    await query.edit_message_text(
        text="What genres do you want to exclude from your results?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return 0

def get_age_rating_buttons(api, chat, certifications):
    certifications.sort(key=lambda x: x["order"])
    keyboard = []
    for (i, certification) in enumerate(certifications):
        if certification["certification"] in chat.excluded_ages:
            button = InlineKeyboardButton(certification["certification"] + " (excluded)", callback_data="remove_agerating_" + certification["certification"])
        else:
            button = InlineKeyboardButton(certification["certification"], callback_data="add_agerating_" + certification["certification"])
        if i % 2 == 0:
            keyboard.append([button])
        else:
            keyboard[-1].append(button)
    
    keyboard.append([InlineKeyboardButton("Done", callback_data="filter")])

    return keyboard

async def filter_age_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api = context.bot_data["api"]
    chat = context.bot_data["db"].getChat(update.effective_chat.id)

    certifications = api.getCertifications(chat.country)
    if certifications is None:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No age ratings found for your country. This means you can not filter by age rating.",
            reply_markup=ReplyKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="filter")]])
        )
        return
    
    keyboard = get_age_rating_buttons(api, chat, certifications)
    
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.message_id,
        text="What age ratings do you want to exclude from your results?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def filter_age_rating_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    api = context.bot_data["api"]
    chat = context.bot_data["db"].getChat(update.effective_chat.id)
    certifications = api.getCertifications(chat.country)


    if not certifications:
        await query.edit_message_text(
            text="No age ratings found for your country. This means you can not filter by age rating.",
            reply_markup=ReplyKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="filter")]])
        )
        return

    if query.data.startswith("add_agerating_"):
        certification = query.data.split("_")[2]
        if certification not in chat.excluded_ages:
            if len(chat.excluded_ages) + 1 == len(certifications):
                await query.answer("You can not exclude all age ratings.", show_alert=True)
                return
            chat.excluded_ages.append(certification)
        context.bot_data["db"].setExcludedAges(update.effective_chat.id, chat.excluded_ages)
    elif query.data.startswith("remove_agerating_"):
        certification = query.data.split("_")[2]
        if certification in chat.excluded_ages:
            chat.excluded_ages.remove(certification)
        context.bot_data["db"].setExcludedAges(update.effective_chat.id, chat.excluded_ages)

    keyboard = get_age_rating_buttons(api, chat, certifications)

    await query.edit_message_text(
        text="What age ratings do you want to exclude from your results?",
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
        text="What country do you want your release dates to be for? By changing this you will also reset your age rating filter.",
        reply_markup=ReplyKeyboardMarkup(countries, one_time_keyboard=True)
    )

    return 1

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I your input was invalid."
    )

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.bot_data["db"]
    chat = context.bot_data["db"].getChat(update.effective_chat.id)
    countries = context.bot_data["api"].countries
    country_iso = next(country['iso_3166_1'] for country in countries if country["english_name"].lower() == update.message.text.lower())
    if country_iso.lower() != chat.country.lower():
        chat.excluded_ages = []
        db.setExcludedAges(update.effective_chat.id, chat.excluded_ages)        
    db.setCountry(update.effective_chat.id, country_iso)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Settings saved.",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

def filter_warning(chat):
    if chat.excluded_ages or chat.excluded_genres:
        return "\n(Not all results are shown because of your filters, use /filter to change them)"
    return ""

async def upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.bot_data["db"]
    chat = db.getChat(update.effective_chat.id)

    upcoming = context.bot_data["api"].getUpcomingMovies(**chat.getQueryParams())
    upcoming = upcoming["results"]
    upcoming.sort(key=lambda x: x["popularity"], reverse=True)
    upcoming = upcoming[:10]
    upcoming.sort(key=lambda x: x["release_date"])

    buttons = []
    
    for i in range(0, min(constants.RESULT_NUMBER, len(upcoming))):
        movie = upcoming[i]
        date = datetime.datetime.strptime(movie["release_date"], "%Y-%m-%d")
        date = format_date(date, locale=chat.language.split("-")[0])
        buttons.append([InlineKeyboardButton(movie["title"] + " (" +  date + ")", callback_data="movie_" + str(movie["id"]))])

    await context.bot.send_message(
        update.effective_chat.id,
        "Upcoming movies: " + filter_warning(chat),
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
        "Currently playing movies: " + filter_warning(chat),
        reply_markup=InlineKeyboardMarkup(buttons)
    )

def getMovieDetails(movie_id: int, chat: Chat, api: MovieAPI):
    movie = api.getMovie(movie_id, **chat.getQueryParams())

    if movie["overview"] == "":
        overview_eng = api.getMovie(movie_id, language="en-US")
        if overview_eng["overview"] != "":
            movie["overview"] = "There was no description in your language available. I will show you the english one instead:\n\n" + overview_eng["overview"]
        else:
            movie["overview"] = "There was no description available for this movie."

    age_rating = "Not available"
    release_date = "Not available"
    for release_date in movie["release_dates"]["results"]:
        if release_date["iso_3166_1"].lower() == chat.country.lower():
            certification = release_date["release_dates"][0]["certification"]
            rl_date = None
            for release in release_date["release_dates"]:
                if release["note"] == "":
                    rl_date = release["release_date"]
                    break
            if rl_date == None:
                rl_date = release_date["release_dates"][0]["release_date"]

            if certification != "":
                age_rating = certification
            if rl_date != "":
                release_date = format_date(datetime.datetime.fromisoformat(rl_date.replace("Z", "")).date(), locale=chat.language.split("-")[0])
            break
    
    # TODO locale specific datestring in seperate function
    cast = movie["credits"]["cast"]
    director = [crew["name"] for crew in movie["credits"]["crew"] if crew["job"] == "Director"]

    title_and_overview = \
        "*" + escape_markdown(movie["title"], version=2) + "*" + "\n" + \
        escape_markdown(movie["overview"], version=2) + "\n\n"

    info = \
        "*Cast*: " + \
            escape_markdown(", ".join([cast[i]["name"] for i in range(0, min(3, len(cast)))]), version=2) + \
        "\n*Directed by*: " + \
            escape_markdown(", ".join(director), version=2) + \
        "\n*Age rating*: " + \
            escape_markdown(age_rating + " (" + chat.country + ")",version=2) + \
        "\n*Release date*: " + \
            escape_markdown(release_date + " (" + chat.country + ")", version=2 )
    
    overview_shortened = False
    if len(title_and_overview) + len(info) > constants.MAX_OVERVIEW_LENGTH:
        new_title_and_overview = title_and_overview[:constants.MAX_OVERVIEW_LENGTH - len(info) - 5] + "\.\.\."
        overview_shortened = True
    else:
        new_title_and_overview = title_and_overview
    caption = new_title_and_overview + "\n\n" + info

    if movie["poster_path"] == None:
        return None, caption

    if not os.path.exists(constants.CACHE_FOLDER):
        os.makedirs(constants.CACHE_FOLDER)
    
    file_path = constants.CACHE_FOLDER + str(movie_id) + "_" + constants.IMAGE_SIZE + movie["poster_path"].split(".")[-1]
    if not os.path.isfile(file_path):
        file_url = api.image_base_url + "w154" + movie["poster_path"]
        response = requests.get(file_url)
        with open(file_path, "wb") as f:
            f.write(response.content)

    return file_path, caption, title_and_overview[:constants.MAX_MESSAGE_LENGTH] if overview_shortened else None
    
async def movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.callback_query.data.split("_")
    chat = context.bot_data["db"].getChat(update.effective_user.id)
    api = context.bot_data["api"]
    movie_id = int(args[1])

    file_path, caption, full_overview = getMovieDetails(movie_id, chat, api)

    buttons = []

    buttons.append([InlineKeyboardButton("Back", callback_data="deletemessage")])

    # If user clicked on "Show full description" button
    if len(args) > 2 and args[2] == "full":
        await context.bot.delete_message(
            update.effective_chat.id,
            update.callback_query.message.message_id
        )
        buttons = [[InlineKeyboardButton("Back", callback_data="movie_" + str(movie_id) + "_delete")]]
        await context.bot.send_message(
            update.effective_chat.id,
            full_overview,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # If user clicks on "Back" button while full description is shown
    if len(args) > 2 and args[2] == "delete":
        await context.bot.delete_message(
            update.effective_chat.id,
            update.callback_query.message.message_id
        )

    # Add "Show full description" button if description was shortened
    if full_overview != None:
        buttons.append([InlineKeyboardButton("Show full description", callback_data="movie_" + str(movie_id) + "_full")])

    # Send message
    if update.effective_chat != None:
        await context.bot.send_photo(
            update.effective_chat.id,
            open(file_path, "rb") if file_path != None else None,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        # If message was sent inline
        await context.bot.edit_message_text(
            text=caption,
            inline_message_id=update.callback_query.inline_message_id,
            parse_mode=ParseMode.MARKDOWN_V2,
        )

async def inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if query == "":
        return

    chat = context.bot_data["db"].getChat(update.inline_query.from_user.id)
    country_name = next(country['english_name'] for country in context.bot_data["api"].countries if country["iso_3166_1"] == chat.country)
    results = []
    for movie in context.bot_data["api"].searchMovie(query, **chat.getQueryParams())["results"]:
        try:
            date = datetime.datetime.strptime(movie["release_date"], "%Y-%m-%d")
            date = format_date(date, "yyyy", locale=chat.language.split("-")[0])
        except:
            date = "???"
        results.append(
            InlineQueryResultArticle(
                id=movie["id"],
                title=movie["title"] + " (" +  date + ")",
                input_message_content=InputTextMessageContent(movie["title"]),
                description=movie["overview"],
                thumb_url=context.bot_data["api"].image_base_url + "w154" + movie["poster_path"] if movie["poster_path"] != None else None,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Show Details", callback_data="movie_" + str(movie["id"]))]])
            )
        )
    await context.bot.answer_inline_query(update.inline_query.id, results)


async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    success = await context.bot.delete_message(update.effective_chat.id, update.callback_query.message.message_id)
    if not success:
        await context.bot.edit_message(reply_markup=None, message_id=update.callback_query.message.message_id, chat_id=update.effective_chat.id)

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = context.bot_data["db"].getChat(update.effective_user.id)
    api = context.bot_data["api"]

    text = "*Language*: " + escape_markdown(chat.language.split("-")[0].upper(), version=2) + "\n" + \
        "*Country*: " + escape_markdown(next(country['english_name'] for country in context.bot_data["api"].countries if country["iso_3166_1"] == chat.country), version=2) + "\n" + \
        "*Excluded genres*: " + escape_markdown(", ".join([genre["name"] for genre in api.genres if genre["id"] in chat.excluded_genres]), version=2)
        #"*Excluded age ratings*: " + escape_markdown(",".join(chat.excluded_ages) if api.getCertifications(chat.country) != None else "Not available for your country", version=2)
    
    await context.bot.send_message(
        update.effective_chat.id,
        text,
        parse_mode=ParseMode.MARKDOWN_V2
    )