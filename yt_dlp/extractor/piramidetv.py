import re

from .common import InfoExtractor, SearchInfoExtractor
from ..utils import (
    parse_iso8601,
    smuggle_url,
    traverse_obj,
    unsmuggle_url,
    url_or_none,
)


class PiramideTVIE(InfoExtractor):
    _VALID_URL = r'https?://piramide\.tv/video/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://piramide.tv/video/eH1OUbYfTRr6',
        'info_dict': {
            'id': 'eH1OUbYfTRr6',
            'ext': 'mp4',
            'title': 'md5:8aa59265c67c2a28f1946b8cd7d4af92',
            'description': '',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/PnWmNChb/thumbnails/5WqhxTSm.jpg',
            'channel': 'León Picarón',
            'channel_id': 'leonpicaron',
            'timestamp': 1699811623,
            'upload_date': '20231112',
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

    def _extract_video(self, video_id, fatal=True):
        video_data = self._download_json(
            f'https://hermes.piramide.tv/video/data/{video_id}', video_id, fatal=fatal)
        if not video_data:
            return None, {'id': video_id}
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'https://cdn.piramide.tv/video/{video_id}/manifest.m3u8', video_id, fatal=fatal)
        next_video = traverse_obj(video_data, ('video', 'next_video', 'id', {str}))
        return next_video, {
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
        }

    def _entries(self, video_info, video_id):
        visited = set()
        if video_info:
            visited.add(video_info['id'])
            yield video_info
        while True:
            visited.add(video_id)
            next_video, info = self._extract_video(video_id, False)
            yield info
            if not next_video or next_video in visited:
                break
            video_id = next_video

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        video_id = self._match_id(url)
        next_video, info = self._extract_video(video_id)
        if next_video and self._yes_playlist(video_id, video_id, smuggled_data):
            return self.playlist_result(
                self._entries(info, next_video),
                **traverse_obj(info, {
                    'id': ('id', {str}),
                    'title': ('title', {str}, {lambda x: re.split(r'\s+\|?\s*Parte\s*\d', x,
                                                                  flags=re.IGNORECASE)[0]}),
                    'description': ('description', {str}),
                    'channel': ('channel', {str}),
                    'channel_id': ('channel_id', {str}),
                }))
        return info


class PiramideTVChannelURLIE(InfoExtractor):
    _VALID_URL = r'https?://piramide\.tv/channel/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://piramide.tv/channel/thekalo',
        'playlist_mincount': 10,
        'info_dict': {
            'id': 'thekalo',
            'title': 'thekalo',
        },
    }]

    def _real_extract(self, url):
        if channel_id := self._match_id(url):
            return self.url_result(url=f'piramidetvall:{channel_id}', url_transparent=True)


class PiramideTVChannelIE(SearchInfoExtractor):
    IE_NAME = 'PiramideTV:channel'
    _SEARCH_KEY = 'piramidetv'
    _TESTS = [{
        'url': 'piramidetv5:bobicraft',
        'playlist_count': 5,
        'info_dict': {
            'id': 'bobicraft',
            'title': 'bobicraft',
        },
    }]

    def _search_results(self, channel_id):
        videos = self._download_json(
            f'https://hermes.piramide.tv/channel/list/{channel_id}/date/100000', channel_id)
        for video in traverse_obj(videos, ('videos', lambda _, v: v['id'])):
            yield self.url_result(smuggle_url(
                f'https://piramide.tv/video/{video["id"]}', {'force_noplaylist': True}),
                **traverse_obj(video, {
                    'id': ('id', {str}),
                    'title': ('title', {str}),
                    'description': ('description', {str}),
                    'thumbnail': ('media', 'thumbnail', {url_or_none}),
                    'webpage_url': ('id', {str}, {lambda v: f'https://piramide.tv/video/{v}'}),
                }))
