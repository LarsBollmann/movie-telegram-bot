import telegram
import commands
import handlers
import dotenv
import os
import db
import moviedbapi
from telegram.ext import ApplicationBuilder
import logging


dotenv.load_dotenv()
bot = telegram.Bot(token=os.getenv("BOT_TOKEN"))
api = moviedbapi.MovieAPI(os.getenv("API_KEY"))
db = db.DB()
app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
app.bot_data["api"] = api
app.bot_data["db"] = db
handlers.add_handlers(app)
app.run_polling()