CREATE TABLE
    IF NOT EXISTS users (
        chat_id integer,
        language text,
        country text,
        PRIMARY KEY (chat_id)
    )