from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from .models import Song
import os
import re
from pytube import Search, YouTube
from yt_dlp import YoutubeDL
from django.conf import settings

# --- SETUP ABSOLUTE PATHS FOR DOCKER ---
# This ensures Python finds the cookies regardless of where the script runs
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COOKIE_PATH = os.path.join(BASE_DIR, 'youtube_cookies.txt')

download_folder = os.path.join(settings.MEDIA_ROOT, 'downloads/music')
FFMPEG_BIN_DIR = None

def download_progress_hook(d):
    """
    Called by yt-dlp to report download status and updates the user's session.
    """
    if d['status'] == 'downloading':
        if d.get('_percent_str'):
            clean_percent_str = re.sub(r'[^0-9.]', '', d['_percent_str'])
            try:
                percent = float(clean_percent_str)
            except ValueError:
                percent = 0
        elif d.get('total_bytes') and d.get('downloaded_bytes'):
            percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
        else:
            percent = 0

        # Store percentage in the session
        d['info']['request'].session['dl_percent'] = round(percent)
        d['info']['request'].session.modified = True

def get_thumbnail_url(video_url):
    # CRITICAL: Added cookies here too to prevent IP flagging
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'extract_flat': True,
        'cookiefile': COOKIE_PATH, 
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if 'thumbnails' in info and info['thumbnails']:
                return info['thumbnails'][-1]['url']
            return None
    except Exception as e:
        print(f"Thumbnail Extraction Error: {e}")
        return None

def search_song(request):
    search_results = []
    error_message = None

    if request.method == 'POST':
        searched = request.POST.get("search_bar")
        search_term = searched.strip()

        if search_term:
            try:
                tube_search = Search(search_term)
                for video in tube_search.results[:20]:
                    search_results.append({
                        "title": video.title,
                        "url": video.watch_url,
                        "pic": None,
                    })
                if not search_results:
                    error_message = f"No results for '{search_term}'."
            except Exception as e:
                error_message = f"Search Error: {e}"
        else:
            error_message = "Please enter a search query."

    context = {
        'search_results': search_results,
        'error': error_message,
    }
    return render(request, "home.html", context)

def get_thumbnail_api(request):
    video_url = request.GET.get('url')
    if video_url:
        thumbnail_url = get_thumbnail_url(video_url)
        return JsonResponse({'pic': thumbnail_url})
    return JsonResponse({'pic': None})

def download_song(request):
    youtube_url = request.GET.get('url')
    print("Received URL:", youtube_url)

    if youtube_url:
        request.session['dl_percent'] = 0
        try:
            os.makedirs(download_folder, exist_ok=True)

            def custom_hook(d):
                d['info'] = {'request': request}
                download_progress_hook(d)

            ydl_opts = {
                'format': 'bestaudio/best',
                'cookiefile': COOKIE_PATH,  # Use absolute path
                'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),
                'noplaylist': True,
                'ffmpeg_location': FFMPEG_BIN_DIR,
                'writethumbnail': True,
                'progress_hooks': [custom_hook],
                'postprocessors': [
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192', # Changed from 0 to 192 for stability
                    },
                    {
                        'key': 'FFmpegMetadata',
                        'add_metadata': True,
                    },
                    {
                        'key': 'EmbedThumbnail',
                    },
                ],
                'extractor_args': {
                    'youtube': {
                        'player_client': ['default', '-android_sdkless']
                    }
                },
            }

            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(youtube_url, download=True)
                title = info_dict.get('title', 'Unknown Title')
                artist = info_dict.get('artist', 'Unknown Artist')
                final_filename = ydl.prepare_filename(info_dict)
                
                # Update extension to .mp3 since post-processor changes it
                final_filename = os.path.splitext(final_filename)[0] + ".mp3"
                relative_file_path = os.path.relpath(final_filename, os.getcwd())

            Song.objects.create(
                title=title,
                artist=artist,
                file_path=relative_file_path
            )

            return JsonResponse({'status': 'completed', 'title': title}, status=200)

        except Exception as e:
            request.session['dl_percent'] = -1
            print(f"yt-dlp ERROR: {e}")
            return JsonResponse({'status': 'failed', 'error': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'error': 'No URL provided.'}, status=400)
