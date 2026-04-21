"""
YouTube Playlist Manager - Creates and manages the reasoning series playlist
"""

from typing import Optional, Dict

import yaml

from .auth import YouTubeAuth
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PlaylistManager:
    """Manages the YouTube playlist for the 200-part series."""

    def __init__(self, auth: YouTubeAuth, config_path: str = "config/settings.yaml"):
        self.auth = auth
        self.config = self._load_config(config_path)
        # Use existing playlist ID from config if available
        self._playlist_id: Optional[str] = self.config.get("youtube", {}).get("playlist_id")

    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    def get_or_create_playlist(self) -> Optional[str]:
        """Get existing playlist or create a new one."""
        if self._playlist_id:
            return self._playlist_id

        youtube = self.auth.get_service()
        if not youtube:
            return None

        yt_config = self.config.get("youtube", {})
        title = yt_config.get("playlist_title", "Reasoning Mastery - Complete 200 Parts Series")
        description = yt_config.get("playlist_description", "")

        try:
            # Search for existing playlist
            request = youtube.playlists().list(
                part="snippet",
                mine=True,
                maxResults=50
            )
            response = request.execute()

            for item in response.get("items", []):
                if item["snippet"]["title"] == title:
                    self._playlist_id = item["id"]
                    logger.info(f"Found existing playlist: {self._playlist_id}")
                    return self._playlist_id

            # Create new playlist
            request = youtube.playlists().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title,
                        "description": description[:5000],
                    },
                    "status": {
                        "privacyStatus": "public"
                    }
                }
            )
            response = request.execute()
            self._playlist_id = response["id"]
            logger.info(f"Created new playlist: {self._playlist_id}")
            return self._playlist_id

        except Exception as e:
            logger.error(f"Failed to get/create playlist: {e}")
            return None

    def add_video(self, video_id: str, position: int = None) -> bool:
        """Add a video to the playlist."""
        playlist_id = self.get_or_create_playlist()
        if not playlist_id:
            return False

        youtube = self.auth.get_service()
        if not youtube:
            return False

        try:
            body = {
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }

            # Don't set position — add to end of playlist
            # YouTube playlists need "manual sorting" enabled for position to work

            youtube.playlistItems().insert(
                part="snippet",
                body=body
            ).execute()

            logger.info(f"Video {video_id} added to playlist {playlist_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add video to playlist: {e}")
            return False

    def update_description(self, completed: int, total: int = 200) -> bool:
        """Update playlist description with progress."""
        playlist_id = self.get_or_create_playlist()
        if not playlist_id:
            return False

        youtube = self.auth.get_service()
        if not youtube:
            return False

        try:
            yt_config = self.config.get("youtube", {})
            base_desc = yt_config.get("playlist_description", "")
            progress_text = f"\n\nProgress: {completed}/{total} parts uploaded ({completed * 100 // total}% complete)"

            youtube.playlists().update(
                part="snippet",
                body={
                    "id": playlist_id,
                    "snippet": {
                        "title": yt_config.get("playlist_title", "Reasoning Mastery"),
                        "description": (base_desc + progress_text)[:5000]
                    }
                }
            ).execute()

            logger.info(f"Playlist description updated: {completed}/{total}")
            return True

        except Exception as e:
            logger.error(f"Failed to update playlist description: {e}")
            return False
