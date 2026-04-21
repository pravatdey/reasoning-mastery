"""
YouTube Uploader - Uploads videos to YouTube with metadata
"""

import time
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import http.client
import httplib2

from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from .auth import YouTubeAuth
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 10
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]


@dataclass
class UploadResult:
    """Result of video upload"""
    success: bool
    video_id: str
    video_url: str
    title: str
    error: Optional[str] = None


class YouTubeUploader:
    """Uploads videos to YouTube with resumable upload support."""

    def __init__(self, auth: YouTubeAuth = None):
        self.auth = auth or YouTubeAuth()
        logger.info("YouTubeUploader initialized")

    def upload(
        self, video_path: str, title: str, description: str,
        tags: list = None, category_id: str = "27",
        privacy_status: str = "public", thumbnail_path: str = None,
        made_for_kids: bool = False
    ) -> UploadResult:
        video_file = Path(video_path)
        if not video_file.exists():
            return UploadResult(False, "", "", title,
                                error=f"Video file not found: {video_path}")

        youtube = self.auth.get_service()
        if not youtube:
            return UploadResult(False, "", "", title,
                                error="Failed to authenticate with YouTube")

        try:
            body = {
                "snippet": {
                    "title": title[:100],
                    "description": description[:5000],
                    "tags": tags[:500] if tags else [],
                    "categoryId": category_id,
                    "defaultLanguage": "en",
                    "defaultAudioLanguage": "en"
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": made_for_kids,
                    "embeddable": True,
                    "publicStatsViewable": True
                }
            }

            media = MediaFileUpload(
                str(video_path), chunksize=10 * 1024 * 1024,
                resumable=True, mimetype="video/*"
            )

            request = youtube.videos().insert(
                part="snippet,status", body=body, media_body=media
            )

            logger.info(f"Starting upload: {title}")
            response = self._resumable_upload(request)

            if response:
                video_id = response.get("id", "")
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                logger.info(f"Upload successful: {video_url}")

                if thumbnail_path and Path(thumbnail_path).exists():
                    self._upload_thumbnail(youtube, video_id, thumbnail_path)

                return UploadResult(True, video_id, video_url, title)

            return UploadResult(False, "", "", title, error="Upload failed - no response")

        except HttpError as e:
            error_msg = f"HTTP error {e.resp.status}: {e.content.decode()}"
            logger.error(f"Upload failed: {error_msg}")
            return UploadResult(False, "", "", title, error=error_msg)
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return UploadResult(False, "", "", title, error=str(e))

    def _resumable_upload(self, request) -> Optional[Dict]:
        response = None
        error = None
        retry = 0

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"Upload progress: {int(status.progress() * 100)}%")
            except HttpError as e:
                if e.resp.status in RETRIABLE_STATUS_CODES:
                    error = f"Retriable HTTP error {e.resp.status}"
                else:
                    raise
            except RETRIABLE_EXCEPTIONS as e:
                error = f"Retriable error: {e}"

            if error:
                retry += 1
                if retry > MAX_RETRIES:
                    logger.error(f"Max retries exceeded: {error}")
                    return None
                sleep_seconds = 2 ** retry
                logger.warning(f"Retrying in {sleep_seconds}s: {error}")
                time.sleep(sleep_seconds)
                error = None

        return response

    def _upload_thumbnail(self, youtube, video_id: str, thumbnail_path: str) -> bool:
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            logger.info(f"Thumbnail uploaded for: {video_id}")
            return True
        except HttpError as e:
            if "forbidden" in str(e).lower():
                logger.warning("Thumbnail upload failed - channel may need verification")
            else:
                logger.error(f"Thumbnail upload failed: {e}")
            return False
