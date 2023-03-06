from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, InlineQueryHandler
import re
from commands import *

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
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CallbackQueryHandler(filter_genres, pattern="filter_genres"))
    app.add_handler(CallbackQueryHandler(filter_genres_callback, pattern=".*_genre_.*"))
    app.add_handler(CallbackQueryHandler(filter_age_rating, pattern="filter_agerating"))
    app.add_handler(CallbackQueryHandler(filter_age_rating_callback, pattern=".*_agerating_.*"))
    app.add_handler(CallbackQueryHandler(filter, pattern="filter"))
    app.add_handler(CallbackQueryHandler(movie, pattern="movie_.*"))
    app.add_handler(CallbackQueryHandler(delete_message, pattern="deletemessage"))
    app.add_handler(InlineQueryHandler(inline))