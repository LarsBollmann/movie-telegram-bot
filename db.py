import psycopg2
import os
from urllib.parse import urlparse

def initDB():
    result = urlparse(os.getenv("DATABASE_URL"))
    username = result.username
    password = result.password
    database = result.path[1:]
    hostname = result.hostname
    port = result.port
    
    conn = psycopg2.connect(
        database = database,
        user = username,
        password = password,
        host = hostname,
        port = port
    )
    
    c = conn.cursor()
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
            conn.commit()
        
    print("Migrations done")