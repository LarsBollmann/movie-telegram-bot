import psycopg2
import os
from urllib.parse import urlparse

class Chat:
    chat_id = None
    language = None
    country = None
    excluded_genres = []
    
    def __init__(self, chat_id, language, country, excluded_genres):
        self.chat_id = chat_id
        self.language = language
        self.country = country
        if excluded_genres == None or excluded_genres == "":
            self.excluded_genres = []
        else:
            # as int
            self.excluded_genres = list(map(int, excluded_genres.split(",")))

    def __str__(self):
        return "Chat(" + str(self.chat_id) + ")"

    def getQueryParams(self):
        return { "language": self.language, "region": self.country, "without_genres": ",".join(map(str, self.excluded_genres)) }


class DB:
    conn = None

    def __init__(self):
        result = urlparse(os.getenv("DATABASE_URL"))
        username = result.username
        password = result.password
        database = result.path[1:]
        hostname = result.hostname
        port = result.port

        self.conn = psycopg2.connect(
            database = database,
            user = username,
            password = password,
            host = hostname,
            port = port
        )
        self.initDB()

    def initDB(self):
        
        c = self.conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS migrations (id TEXT PRIMARY KEY)")
        
        migration_list = os.listdir("migrations");
        migration_list.sort();
        
        for migration in migration_list:
            c.execute("SELECT id FROM migrations WHERE id = %s", (migration.replace(".sql", ""),))
            if c.fetchone() == None:
                print("Running migration " + migration)
                with open("migrations/" + migration, "r") as f:
                    c.execute(f.read())
                c.execute("INSERT INTO migrations VALUES (%s)", (migration.replace(".sql", ""),))
                self.conn.commit()
            
        print("Migrations done")

    def setLanguage(self, chat_id, language):
        c = self.conn.cursor()
        c.execute("INSERT INTO users(chat_id, language) VALUES (%s, %s) ON CONFLICT (chat_id) DO UPDATE SET language = %s", (chat_id, language, language))
        self.conn.commit()
        
    def setCountry(self, chat_id, country):
        c = self.conn.cursor()
        c.execute("INSERT INTO users(chat_id, country) VALUES (%s, %s) ON CONFLICT (chat_id) DO UPDATE SET country = %s", (chat_id, country, country))
        self.conn.commit()

    def setExcludedGenres(self, chat_id, excluded_genres):
        c = self.conn.cursor()
        genrestring = ",".join(str(x) for x in excluded_genres)
        c.execute("INSERT INTO users(chat_id, excluded_genres) VALUES (%s, %s) ON CONFLICT (chat_id) DO UPDATE SET excluded_genres = %s", (chat_id, genrestring, genrestring))
        self.conn.commit()

    def getChat(self, chat_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users WHERE chat_id = %s", (chat_id,))
        row = c.fetchone()
        if row == None:
            return Chat(-1, "en", "us", "")
        return Chat(row[0], row[1], row[2], row[3])