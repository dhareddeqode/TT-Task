FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1
RUN mkdir /orders_hub
WORKDIR /orders_hub

RUN apt-get update && apt-get install -y libpq-dev build-essential

COPY . .
RUN pip install -r requirements.txt

EXPOSE 8000
