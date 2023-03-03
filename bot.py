import telegram
import commands
import dotenv
import os
import db
import moviedbapi
from telegram.ext import ApplicationBuilder
import logging


dotenv.load_dotenv()
bot = telegram.Bot(token=os.getenv("BOT_TOKEN"))
api = moviedbapi.MovieAPI(os.getenv("API_KEY"))
app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
app.bot_data["api"] = api
app.bot_data["db"] = db
commands.add_handlers(app)
app.run_polling()