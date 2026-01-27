from django.urls import path
from . import views

urlpatterns = [
    path('', views.search_song, name="search_song"),
    path('download/', views.download_song, name="download_song"),
    path('get_pic/', views.get_thumbnail_api, name='get_thumbnail_api'),
]