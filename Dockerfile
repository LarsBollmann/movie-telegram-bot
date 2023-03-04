FROM python:3.9.1-alpine

# Install dependencies
RUN python -m pip install --upgrade pip
RUN pip install pipenv
RUN apk add postgresql-dev gcc musl-dev


COPY Pipfile Pipfile.lock ./

RUN pipenv install

COPY migrations/ migrations/
COPY *.py ./

CMD ["pipenv", "run", "python", "bot.py"]