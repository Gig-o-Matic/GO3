FROM python:3.11-alpine

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apk add --no-cache tini gcc musl-dev mysql-dev

RUN pip install --upgrade pip
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY requirements.mysql.txt ./
RUN pip install --no-cache-dir -r requirements.mysql.txt

COPY . .

RUN addgroup -g 1000 appuser; \
    adduser -u 1000 -G appuser -D -h /app appuser; \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000/tcp
ENTRYPOINT [ "tini", "--" ]
