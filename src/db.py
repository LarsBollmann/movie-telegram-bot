import psycopg2
import os
from urllib.parse import urlparse
from moviedbapi import MovieAPI

class Chat:
    chat_id = None
    language = None
    country = None
    excluded_genres = []
    excluded_ages = []
    
    def __init__(self, chat_id, language, country, excluded_genres, excluded_ages):
        self.chat_id = chat_id
        self.language = language
        self.country = country
        if excluded_genres == None or excluded_genres == "":
            self.excluded_genres = []
        else:
            # as int
            self.excluded_genres = list(map(int, excluded_genres.split(",")))
        if excluded_ages == None or excluded_ages == "":
            self.excluded_ages = []
        else:
            self.excluded_ages = excluded_ages.split(",")

    def __str__(self):
        return "Chat(" + str(self.chat_id) + ")"

    def get_included_ages(self):
        api = MovieAPI(os.getenv("API_KEY"))
        certifications = api.getCertifications(self.country)
        if certifications == None:
            return [], None
        included = []
        for certification in certifications:
            if certification["certification"] not in self.excluded_ages:
                included.append(certification["certification"])
        return included, certifications

    def getQueryParams(self):
        extra = {}
        if self.excluded_ages != None and len(self.excluded_ages) > 0:
            included_ages, certifications = self.get_included_ages()
            if certifications != None:
                extra["certification_country"] = self.country.upper()
                extra["certification"] = "|".join(included_ages)
        return { "language": self.language, "region": self.country, "without_genres": ",".join(map(str, self.excluded_genres)), **extra }


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

    def setExcludedAges(self, chat_id, excluded_ages):
        c = self.conn.cursor()
        agestring = ",".join(str(x) for x in excluded_ages)
        c.execute("INSERT INTO users(chat_id, excluded_ages) VALUES (%s, %s) ON CONFLICT (chat_id) DO UPDATE SET excluded_ages = %s", (chat_id, agestring, agestring))
        self.conn.commit()

    def getChat(self, chat_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users WHERE chat_id = %s", (chat_id,))
        row = c.fetchone()
        if row == None:
            return Chat(-1, "en", "US", "", "")
        return Chat(row[0], row[1] if row[1] != None else "en", row[2] if row[2] != None else "US", row[3], row[4])