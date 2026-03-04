FROM python:3.12-slim
RUN apt-get update && apt-get install -y ffmpeg nodejs && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# COPY THE COOKIES FILE HERE
COPY youtube_cookies.txt /app/youtube_cookies.txt

COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -U yt-dlp
CMD ["gunicorn", "musicproject.wsgi:application", "--bind", "0.0.0.0:10000"]
