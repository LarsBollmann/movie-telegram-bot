CREATE TABLE
    IF NOT EXISTS users (
        user_id integer,
        language text,
        region text,
        PRIMARY KEY (user_id)
    )