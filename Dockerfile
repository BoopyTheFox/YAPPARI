FROM python:3.12-slim

ENV path=/YAPPARI

VOLUME ${path}
WORKDIR ${path}

COPY app/ ${path}

RUN apt-get update
RUN pip install -r requirements.txt

CMD python y_bot.py
