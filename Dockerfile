FROM python:3.12-slim

# Install system dependencies (ffmpeg and nodejs are mandatory for yt-dlp in 2026)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Force update yt-dlp to the latest version to bypass YouTube changes
RUN pip install --no-cache-dir -U yt-dlp

# Copy the rest of the project
COPY . .

# Ensure the cookie file is readable by the app
# Make sure youtube_cookies.txt is in the same folder as manage.py on your PC
RUN chmod 644 youtube_cookies.txt

CMD ["gunicorn", "musicproject.wsgi:application", "--bind", "0.0.0.0:10000"]
