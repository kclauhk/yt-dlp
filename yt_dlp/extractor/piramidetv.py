import re

from .common import InfoExtractor
from ..utils import (
    parse_iso8601,
    traverse_obj,
    url_or_none,
)


class PiramideTVBaseIE(InfoExtractor):
    def _extract_video(self, video_id, fatal=True):
        video_data = self._download_json(
            f'https://hermes.piramide.tv/video/data/{video_id}', video_id, fatal=fatal)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'https://cdn.piramide.tv/video/{video_id}/manifest.m3u8', video_id, fatal=fatal)
        video_dict = {
            'id': video_id,
            **traverse_obj(video_data, ('video', {
                'id': ('id', {str}),
                'title': ('title', {str}),
                'description': ('description', {str}),
                'thumbnail': ('media', 'thumbnail', {url_or_none}),
                'channel': ('channel', 'name', {str}),
                'channel_id': ('channel', 'id', {str}),
                'timestamp': ('date', {parse_iso8601}),
            })),
            'formats': formats,
            'subtitles': subtitles,
            'webpage_url': f'https://piramide.tv/video/{video_id}',
            'webpage_url_basename': video_id,
        }
        next_video_id = traverse_obj(video_data, ('video', 'next_video', 'id', {str}))
        return video_dict, next_video_id


class PiramideTVIE(PiramideTVBaseIE):
    _VALID_URL = r'https?://piramide\.tv/video/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://piramide.tv/video/wWtBAORdJUTh',
        'info_dict': {
            'id': 'wWtBAORdJUTh',
            'ext': 'mp4',
            'title': 'md5:79f9c8183ea6a35c836923142cf0abcc',
            'description': '',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/W86PgQDn/thumbnails/B9gpIxkH.jpg',
            'channel': 'León Picarón',
            'channel_id': 'leonpicaron',
            'timestamp': 1696460362,
            'upload_date': '20231004',
        },
    }, {
        'url': 'https://piramide.tv/video/wcYn6li79NgN',
        'info_dict': {
            'id': 'wcYn6li79NgN',
            'title': 'ACEPTO TENER UN BEBE CON MI NOVIA\u2026?',
            'description': '',
            'channel': 'ARTA GAME',
            'channel_id': 'arta_game',
        },
        'playlist_count': 4,
    }]

    def _entries(self, video, video_id):
        if video:
            yield video
        while video_id is not None:
            video, next_video_id = self._extract_video(video_id, False)
            if video.get('formats'):
                yield video
            video_id = next_video_id if next_video_id != video_id else None

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video, next_video_id = self._extract_video(video_id)
        if next_video_id and self._yes_playlist(video_id, video_id):
            return self.playlist_result(self._entries(video, next_video_id),
                **traverse_obj(video, {
                    'id': ('id', {str}),
                    'title': ('title', {str}, {lambda x: re.split(r'\s+\|?\s*Parte\s*\d', x,
                                                                  flags=re.IGNORECASE)[0]}),
                    'description': ('description', {str}),
                    'channel': ('channel', {str}),
                    'channel_id': ('channel_id', {str}),
                }))
        return video


class PiramideTVChannelIE(PiramideTVBaseIE):
    _VALID_URL = r'https?://piramide\.tv/channel/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://piramide.tv/channel/thekalo',
        'info_dict': {
            'id': 'thekalo',
        },
        'playlist_mincount': 10,
    }]

    def _entries(self, channel_id):
        videos = self._download_json(
            f'https://hermes.piramide.tv/channel/list/{channel_id}/date/100000', channel_id)
        if self.get_param('extract_flat') == 'in_playlist':
            for video in videos.get('videos', []):
                yield self.url_result(f"https://piramide.tv/video/{video['id']}",
                    **traverse_obj(video, {
                        'title': ('title', {str}),
                        'description': ('description', {str}),
                        'thumbnail': ('media', 'thumbnail', {url_or_none}),
                        'channel': ('channel', 'name', {str}),
                        'channel_id': ('channel', 'id', {str}),
                    }))
        else:
            video_done = [None]
            for video_id in traverse_obj(videos, ('videos', ..., 'id', {str})):
                while video_id not in video_done:
                    video, next_video_id = self._extract_video(video_id, fatal=False)
                    if video:
                        yield video
                    video_done.append(video_id)
                    video_id = next_video_id

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        return self.playlist_result(self._entries(channel_id), channel_id)
