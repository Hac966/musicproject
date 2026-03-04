from django.shortcuts import render
from django.http import JsonResponse
from .models import Song
import os
import re
from pytube import Search
from yt_dlp import YoutubeDL
from django.conf import settings

# --- SIMPLE ABSOLUTE PATH ---
# This looks for the file in the same folder as manage.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COOKIE_PATH = os.path.join(BASE_DIR, 'youtube_cookies.txt')
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'

download_folder = os.path.join(settings.MEDIA_ROOT, 'downloads/music')

def download_progress_hook(d):
    if d['status'] == 'downloading':
        clean_percent_str = re.sub(r'[^0-9.]', '', d.get('_percent_str', '0'))
        try:
            percent = float(clean_percent_str)
        except ValueError:
            percent = 0
        req = d.get('info', {}).get('request')
        if req:
            req.session['dl_percent'] = round(percent)
            req.session.modified = True

def get_thumbnail_url(video_url):
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'extract_flat': True,
        'cookiefile': COOKIE_PATH,
        'user_agent': USER_AGENT,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info['thumbnails'][-1]['url'] if 'thumbnails' in info else None
    except:
        return None

def search_song(request):
    search_results = []
    if request.method == 'POST':
        search_term = request.POST.get("search_bar", "").strip()
        if search_term:
            try:
                tube_search = Search(search_term)
                for video in tube_search.results[:20]:
                    search_results.append({"title": video.title, "url": video.watch_url, "pic": None})
            except Exception as e:
                print(f"Search Error: {e}")
    return render(request, "home.html", {'search_results': search_results})

def get_thumbnail_api(request):
    video_url = request.GET.get('url')
    return JsonResponse({'pic': get_thumbnail_url(video_url) if video_url else None})

def download_song(request):
    youtube_url = request.GET.get('url')
    if not youtube_url:
        return JsonResponse({'status': 'error', 'error': 'No URL provided.'}, status=400)

    request.session['dl_percent'] = 0
    try:
        os.makedirs(download_folder, exist_ok=True)

        def custom_hook(d):
            d['info'] = {'request': request}
            download_progress_hook(d)

        ydl_opts = {
            'format': 'bestaudio/best',
            'cookiefile': COOKIE_PATH,
            'user_agent': USER_AGENT,
            'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'writethumbnail': True,
            'progress_hooks': [custom_hook],
            'extractor_args': {'youtube': {'player_client': ['web', 'default', '-android_sdkless']}},
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                {'key': 'FFmpegMetadata', 'add_metadata': True},
                {'key': 'EmbedThumbnail'},
            ],
        }

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=True)
            title = info_dict.get('title', 'Unknown')
            final_filename = ydl.prepare_filename(info_dict)
            final_filename = os.path.splitext(final_filename)[0] + ".mp3"
            relative_path = os.path.relpath(final_filename, os.getcwd())

            Song.objects.create(title=title, artist=info_dict.get('artist', 'Unknown'), file_path=relative_path)
            return JsonResponse({'status': 'completed', 'title': title})

    except Exception as e:
        request.session['dl_percent'] = -1
        return JsonResponse({'status': 'failed', 'error': str(e)}, status=500)
