from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
import datetime
from babel.dates import format_date

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
    movie_id = int(update.callback_query.data.split("_")[1])
    #TODO: locale programmatically
    movie = context.bot_data["api"].getMovie(movie_id, language="de", region="DE")
    
    if movie["poster_path"] == None:
        await context.bot.send_message(
            update.effective_chat.id,
            movie["overview"]
        )
        return
    
    photo = context.bot_data["api"].image_base_url + "w500" + movie["poster_path"]
    await context.bot.send_photo(
        update.effective_chat.id,
        photo,
        caption=movie["overview"]
    )


def add_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upcoming", upcoming))
    app.add_handler(CallbackQueryHandler(movie, pattern="movie_.*"))