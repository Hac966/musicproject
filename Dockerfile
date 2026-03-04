FROM python:3.12-slim

# Added nodejs: yt-dlp needs it for YouTube signature decryption in 2026
RUN apt-get update && apt-get install -y ffmpeg nodejs && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt

# Force update yt-dlp specifically to bypass recent 403 blocks
RUN pip install --no-cache-dir -U yt-dlp

CMD ["gunicorn", "musicproject.wsgi:application", "--bind", "0.0.0.0:10000"]
