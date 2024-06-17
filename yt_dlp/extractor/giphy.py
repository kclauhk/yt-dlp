import json
import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class GiphyIE(InfoExtractor):
    _VALID_URL = r'https?://giphy\.com/(?:[^/]+/)?(?:[^/]+-)?(?P<id>\w+)'
    _TESTS = [{
        'url': 'http://giphy.com/gifs/l3vR8BKU0m8uX2mAg',
        'info_dict': {
            'id': 'l3vR8BKU0m8uX2mAg',
            'title': 'Giphy video #l3vR8BKU0m8uX2mAg',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*',
            'upload_date': '20161022',
            'uploader': 'gus123',
            'uploader_id': 'gus123',
            'uploader_url': 'https://giphy.com/channel/gus123',
        },
    }, {
        'url': 'https://giphy.com/gifs/digitalpratik-digital-pratik-happy-fathers-day-dad-E1trcBzr59SGvmRDPY',
        'info_dict': {
            'id': 'E1trcBzr59SGvmRDPY',
            'title': 'Happy Fathers Day GIF by Digital Pratik',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*',
            'upload_date': '20210619',
            'uploader': 'Digital Pratik',
            'uploader_id': 'digitalpratik',
            'uploader_url': 'https://giphy.com/digitalpratik',
        },
    }, {
        'url': 'https://giphy.com/embed/00xGP4zv8xENZ2tc3Y',
        'info_dict': {
            'id': '00xGP4zv8xENZ2tc3Y',
            'title': 'Love Is Blind Wow GIF by NETFLIX',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*',
            'upload_date': '20220214',
            'uploader': 'NETFLIX',
            'uploader_id': 'netflix',
            'uploader_url': 'https://giphy.com/netflix',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        info, formats, thumbnails = None, [], []
        if embed := self._download_webpage(f'https://giphy.com/embed/{video_id}/twitter/iframe', video_id):
            if data := self._html_search_regex(r'gif:\s*({.*?}),\s*\w', embed, 'video_data', default=None):
                data = json.loads(data)
                for format_id in sorted(data['images'].keys(), reverse=True):
                    if format_id == 'original_still':
                        thumbnails = [{
                            **traverse_obj(data['images'][format_id], {
                                'height': ('height', {int_or_none}),
                                'width': ('width', {int_or_none}),
                                'url': ('url', {url_or_none}),
                            }, get_all=False),
                            'http_headers': {'Accept': 'image/*'},
                        }]
                    for key in ['mp4', 'url', 'webp']:
                        if key in data['images'][format_id]:
                            formats.append({
                                'format_id': format_id,
                                'preference': -10 if '_still' in format_id else -1,
                                **traverse_obj(data['images'][format_id], {
                                    'height': ('height', {int_or_none}),
                                    'width': ('width', {int_or_none}),
                                    'url': (key, {url_or_none}),
                                }, get_all=False),
                            })

                info = {
                    **traverse_obj(data, {
                        'id': ('id', {str}),
                        'title': ('title', {str_or_none}),
                        'uploader': ('user', ('name', 'display_name',
                                              'attribution_display_name', 'username'),
                                     {str_or_none}),
                        'uploader_id': ((None, 'user'), 'username', {str_or_none}),
                        'uploader_url': ('user', ('profile_url', 'website_url'), {url_or_none}),
                    }, get_all=False),
                }

        if webpage := self._download_webpage(f'https://giphy.com/gifs/{video_id}', video_id):
            if not info:
                title = self._og_search_title(webpage).replace(' - Find & Share on GIPHY', '').strip()
                uploader_id = (self._html_search_regex(r'\.giphy\.com/avatars/([^/]+)/', webpage, 'uploader_id', default=None, fatal=False)
                               or self._html_search_meta(['twitter:creator'], webpage, 'uploader_id', default=None))
                uploader = (self._html_search_regex(r'(?s)<h2\b[^>]*>([^<]+)</h2>', webpage, 'uploader', default=None, fatal=False)
                            or title[(title.rfind(' by ') + 4):]
                            or uploader_id)
                info = {
                    'id': video_id,
                    'title': title,
                    'uploader': uploader,
                    'uploader_id': uploader_id,
                }
            info['upload_date'] = self._html_search_regex(
                r'"datePublished\W+(\d{4}-\d{2}-\d{2}) ', webpage, 'upload_date', default='', fatal=False).replace('-', '')

            f_data, manifest_idx = '', None
            for f in re.findall(r'<script>self\.__next_f\.push\((\[.*?\])\)</script>', webpage):
                f = self._parse_json(f, video_id)
                if manifest := re.search(r'([0-9]?[0-9a-f]):\{"original":', f[1]):
                    manifest_idx = manifest.group(1)
                    f[1] = re.sub(r':"\$([^"]+)"', r':"\1"', f[1])
                    f_data += f[1]
                    break
                f_data += f[1]
            if f_data and manifest_idx:
                f_data = re.sub(r'\n$', '}', f_data)
                f_data = re.sub(r'\n([0-9]?[0-9a-f]):', r',"\1":', f_data)
                f_data = re.sub(r'^([0-9]?[0-9a-f]):', r'{"\1":', f_data)
                f_data = json.loads(re.sub(r':\w+\[', r':[', f_data))
                for format_id in f_data[manifest_idx]:
                    if format_id not in [f['format_id'] for f in formats]:
                        idx = f_data[manifest_idx][format_id]
                        if format_id == 'original_still':
                            thumbnails = [{
                                **traverse_obj(f_data[idx], {
                                    'height': ('height', {int_or_none}),
                                    'width': ('width', {int_or_none}),
                                    'url': ('url', {url_or_none}),
                                }, get_all=False),
                                'http_headers': {'Accept': 'image/*'},
                            }]
                        for key in ['mp4', 'url', 'webp']:
                            if key in f_data[idx]:
                                formats.append({
                                    'format_id': format_id,
                                    'preference': -10 if '_still' in format_id else -1,
                                    **traverse_obj(f_data[idx], {
                                        'height': ('height', {int_or_none}),
                                        'width': ('width', {int_or_none}),
                                        'url': (key, {url_or_none}),
                                    }, get_all=False),
                                })
            if not formats:
                if url := self._og_search_video_url(webpage):
                    formats.append({
                        'format_id': determine_ext(url),
                        'url': url,
                    })
                if url := self._og_search_thumbnail(webpage):
                    formats.append({
                        'format_id': determine_ext(url),
                        'url': self._og_search_thumbnail(webpage),
                        'height': int_or_none(self._og_search_property('video:height', webpage)),
                        'width': int_or_none(self._og_search_property('video:width', webpage)),
                    })

        self._remove_duplicate_formats(formats)
        for f in formats:
            f.setdefault('http_headers', {})['Accept'] = 'video/*,image/*'

        return {
            **info,
            'thumbnails': thumbnails,
            'formats': formats,
        }
