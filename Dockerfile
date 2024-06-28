FROM python:3.11-slim

RUN apt-get update

WORKDIR /app

RUN pip install --upgrade pip

COPY ./rex.txt ./

RUN pip install -r rex.txt

COPY . .

RUN ["chmod", "+x", "./web-runner.sh"]
