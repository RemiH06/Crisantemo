FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY shared /app/shared
COPY training/requirements.txt /app/training/requirements.txt
RUN pip install --no-cache-dir -r /app/training/requirements.txt \
    && pip install --no-cache-dir -e /app/shared

COPY training/scripts /app/scripts

CMD ["python", "scripts/04_train_model.py"]
