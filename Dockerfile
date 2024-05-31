FROM python:3.12-bullseye
#FROM python:3.11-slim-buster

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN mkdir /code
WORKDIR /code/
ADD . /code/
RUN pip install -r requirements.txt
