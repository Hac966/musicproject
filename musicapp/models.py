from django.db import models


class Song(models.Model):
    """Model to store metadata and local path of downloaded songs."""

    # Stores the title of the song (retrieved from YouTube)
    title = models.CharField(max_length=255)

    # Stores the artist (optional field, as Pytube doesn't always provide it easily)
    artist = models.CharField(max_length=255, null=True, blank=True)

    # Stores the local path (string) where the file is physically saved on the server
    file_path = models.CharField(max_length=500)

    # Timestamp for when the song was added/downloaded
    download_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.file_path})"

    class Meta:
        # Optional: Order songs by the newest download date
        ordering = ['-download_date']