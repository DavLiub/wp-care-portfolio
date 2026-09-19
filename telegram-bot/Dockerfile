FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py guide.py ./
COPY knowledge ./knowledge
COPY tests ./tests

USER 10001:10001

CMD ["python", "bot.py"]
