from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
import requests
import datetime
from babel.dates import format_date
import os.path

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I'm a bot, please talk to me!"
    )
    
async def upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #TODO: locale programmatically
    upcoming = context.bot_data["api"].getUpcomingMovies(language="de", region="DE")
    upcoming = upcoming["results"]
    upcoming.sort(key=lambda x: x["release_date"])

    print(upcoming)
    buttons = []
    
    for i in range(0, min(10, len(upcoming))):
        movie = upcoming[i]
        date = datetime.datetime.strptime(movie["release_date"], "%Y-%m-%d")
        #TODO: locale programmatically
        date = format_date(date, format="short", locale="de")
        buttons.append([InlineKeyboardButton(movie["title"] + " (" +  date + ")", callback_data="movie_" + str(movie["id"]))])
    
    await context.bot.send_message(
        update.effective_chat.id,
        "Upcoming movies:\n",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
async def movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    image_size = "original"
    cache_folder = "cache/"
    movie_id = int(update.callback_query.data.split("_")[1])
    #TODO: locale programmatically
    movie = context.bot_data["api"].getMovie(movie_id, language="de", region="DE")
    
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


def add_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upcoming", upcoming))
    app.add_handler(CallbackQueryHandler(movie, pattern="movie_.*"))