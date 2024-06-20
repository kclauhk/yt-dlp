from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class GiphyIE(InfoExtractor):
    _VALID_URL = r'https?://giphy\.com/(?!channel/)(?:[^/]+/)(?:[^/]+-)?(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://giphy.com/gifs/l2JIcQ4UH5SoPtMJi',
        'info_dict': {
            'id': 'l2JIcQ4UH5SoPtMJi',
            'ext': 'mp4',
            'title': 'excited slow motion GIF by Cats the Musical',
            'tags': ['giphyupload', 'excited', 'cats', 'musical', 'flip', 'slow motion', 'somersault', 'cats musical'],
            'thumbnail': r're:^https?://.*',
            'upload_date': '20160125',
            'uploader': 'Cats the Musical',
            'uploader_id': 'catsmusical',
            'uploader_url': 'https://giphy.com/catsmusical/',
        },
    }, {
        'url': 'http://giphy.com/gifs/l3vR8BKU0m8uX2mAg',
        'info_dict': {
            'id': 'l3vR8BKU0m8uX2mAg',
            'ext': 'mp4',
            'title': 'Giphy video #l3vR8BKU0m8uX2mAg',
            'tags': ['giphyupload'],
            'thumbnail': r're:^https?://.*',
            'upload_date': '20161022',
            'uploader': 'gus123',
            'uploader_id': 'gus123',
            'uploader_url': 'https://giphy.com/channel/gus123/',
        },
    }, {
        'url': 'https://giphy.com/gifs/digitalpratik-digital-pratik-happy-fathers-day-dad-E1trcBzr59SGvmRDPY',
        'info_dict': {
            'id': 'E1trcBzr59SGvmRDPY',
            'ext': 'mp4',
            'title': 'Happy Fathers Day GIF by Digital Pratik',
            'tags': 'count:14',
            'thumbnail': r're:^https?://.*',
            'upload_date': '20210619',
            'uploader': 'Digital Pratik',
            'uploader_id': 'digitalpratik',
            'uploader_url': 'https://giphy.com/digitalpratik/',
        },
    }, {
        'url': 'https://giphy.com/clips/southpark-south-park-episode-4-season-20-YyOPrvilA8FdiuSiQi',
        'info_dict': {
            'id': 'YyOPrvilA8FdiuSiQi',
            'ext': 'mp4',
            'title': 'You Can\'t Break Up With Me',
            'description': 'South Park, Season 20, Episode 4, Wieners Out',
            'tags': 'count:17',
            'thumbnail': r're:^https?://.*',
            'upload_date': '20220516',
            'uploader': 'South Park',
            'uploader_id': 'southpark',
            'uploader_url': 'https://giphy.com/southpark/',
        },
    }, {
        'url': 'https://giphy.com/embed/00xGP4zv8xENZ2tc3Y',
        'info_dict': {
            'id': '00xGP4zv8xENZ2tc3Y',
            'ext': 'mp4',
            'title': 'Love Is Blind Wow GIF by NETFLIX',
            'description': 'md5:89445e21c848eef12af249faef4fcf9f',
            'tags': 'count:24',
            'thumbnail': r're:^https?://.*',
            'upload_date': '20220214',
            'uploader': 'NETFLIX',
            'uploader_id': 'netflix',
            'uploader_url': 'https://giphy.com/netflix/',
        },
    }, {
        'url': 'https://giphy.com/stickers/mario-PFxFYEZNUavG8',
        'info_dict': {
            'id': 'PFxFYEZNUavG8',
            'ext': 'mp4',
            'title': 'nintendo mario STICKER',
            'tags': ['transparent', 'gaming', 'nintendo', 'mario', 'giphynintendos'],
            'thumbnail': r're:^https?://.*',
            'upload_date': '20160908',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(f'https://giphy.com/gifs/{video_id}', video_id)

        if json_str := self._html_search_regex(r'\\"\w+\\":({\\"type\\":\\"(?!emoji).*?is_dynamic\\":\w+}),',
                                               webpage, 'video_data', default=None):
            video_data = self._parse_json(json_str.encode('utf-8').decode('unicode_escape'), video_id)
        elif json_str := self._html_search_regex(r'\s+\w+:\s*({".*?}),\n\s+', webpage, 'video_data', default={}):
            video_data = self._parse_json(json_str, video_id)

        def extract_formats(video_dict, is_still=False):
            f = []
            for format_id in video_dict:
                if ('_still' in format_id) == is_still:
                    for key in [k for k, v in video_dict[format_id].items() if str(v)[:4] == 'http']:
                        i = traverse_obj(video_dict[format_id], {
                            'width': ('width', {int_or_none}),
                            'height': ('height', {int_or_none}),
                            'url': (key, {url_or_none}),
                        })
                        f.append({
                            'format_id': format_id,
                            **i,
                        })
            return f

        formats, thumbnails, subtitles = [], [], {}
        if data := video_data.get('video'):
            for lang in data.get('captions', {}):
                for key in data['captions'][lang]:
                    subtitles.setdefault(lang, []).append({'url': data['captions'][lang][key]})
            for category in ['assets', 'previews']:
                formats.extend(extract_formats(data.get(category, {})))
            if data.get('hls_manifest_url'):
                hls_fmts, hls_subs = self._extract_m3u8_formats_and_subtitles(
                    data['hls_manifest_url'], video_id, 'mp4', m3u8_id='hls', fatal=False)
                formats.extend(hls_fmts)
                self._merge_subtitles(hls_subs, target=subtitles)
            if data.get('dash_manifest_url'):
                dash_fmts, dash_subs = self._extract_mpd_formats_and_subtitles(
                    data['dash_manifest_url'], video_id, mpd_id='dash', fatal=False)
                formats.extend(dash_fmts)
                self._merge_subtitles(dash_subs, target=subtitles)
        if data := video_data.get('images'):
            sorted_data = dict(sorted(data.items(), reverse=True))
            formats.extend(extract_formats(sorted_data))
            thumbnails.extend(extract_formats(data, is_still=True))
        if not formats:
            if url := self._og_search_video_url(webpage):
                formats.append({
                    'format_id': determine_ext(url),
                    'width': int_or_none(self._og_search_property('video:width', webpage)),
                    'height': int_or_none(self._og_search_property('video:height', webpage)),
                    'url': url,
                })
            if url := self._og_search_thumbnail(webpage):
                formats.append({
                    'format_id': determine_ext(url),
                    'width': int_or_none(self._og_search_property('image:width', webpage)),
                    'height': int_or_none(self._og_search_property('image:height', webpage)),
                    'url': url,
                })
            if url := self._html_search_meta('twitter:image', webpage):
                thumbnails = [{
                    'width': int_or_none(self._html_search_meta('twitter:image:width', webpage)),
                    'height': int_or_none(self._html_search_meta('twitter:image:height', webpage)),
                    'url': url,
                }]
        self._remove_duplicate_formats(formats)
        for f in formats:
            f.setdefault('http_headers', {})['Accept'] = 'video/*,image/*'
        for l in subtitles:
            for s in subtitles[l]:
                s.setdefault('http_headers', {})['Accept'] = 'text/*'
        for t in thumbnails:
            t.setdefault('http_headers', {})['Accept'] = 'image/*'

        title = (self._html_search_meta('twitter:title', webpage)
                 or self._og_search_title(webpage).replace(' - Find & Share on GIPHY', '').strip())
        description = (self._html_search_meta('twitter:description', webpage)
                       or self._og_search_description(webpage))
        description = description if not description.startswith('Discover & share') else None

        if data := video_data.get('user'):
            if isinstance(data, str):
                idx = data.replace('$', '')
                if json_str := self._html_search_regex(rf'"{idx}:({{.*?}})\\n"]\)</script>', webpage, 'video_data', default=None):
                    data = self._parse_json(json_str.encode('utf-8').decode('unicode_escape'), video_id, fatal=False)
            if isinstance(data, dict):
                uploader = traverse_obj(data, {
                    'uploader': (('display_name', 'name', 'attribution_display_name', 'username'), {str_or_none},
                                 {lambda v: v if v else video_data.get('username')}),
                    'uploader_id': ('username', {str_or_none}),
                    'uploader_url': (('profile_url', 'website_url'), {url_or_none},
                                     {lambda v: f'https://giphy.com{v}' if v[0] == '/' else v}),
                }, get_all=False)
        if 'uploader' not in locals():
            up_id = (video_data.get('username')
                     or self._html_search_regex(r'<div>@(\w+)</div>', webpage, 'uploader_id', default=None)
                     or self._html_search_regex(r'"woff2"/><link[^>]+\.giphy\.com/(?:channel_assets|avatars)/(.+?)/',
                                                webpage, 'uploader_id', default=None))
            up_name = (title[(title.rfind(' by ') + 4):] if title.rfind(' by ') > 0 else None
                       or self._html_search_regex(r'(?s)<h2\b[^>]*>([^<]+)</h2>', webpage, 'uploader', default=None)
                       or self._html_search_regex(r'twitter:creator"[^>]+="((?!@giphy").*?)"', webpage, 'uploader', default=None)
                       or up_id)
            uploader = {
                'uploader': up_name,
                'uploader_id': up_id,
                'uploader_url': (f'https://giphy.com/channel/{up_id}/' if up_id else None),
            }

        info = {
            **traverse_obj(video_data, {
                'id': ('id', {str}, {lambda v: v or video_id}),
                'title': ('title', {str_or_none}, {lambda v: v.strip() if v else title}),
                'description': ((None, 'video'), ('alt_text', 'description'), {str_or_none},
                                {lambda v: v.strip() if v and not v.startswith('Discover & share') else description}),
                'tags': ('tags', {list}),
                'upload_date': (('import_datetime', 'create_datetime'), {str_or_none},
                                {lambda v: v[:10].replace('-', '') if v else None}),
            }, get_all=False),
        }

        return {
            **info,
            **{k: v for k, v in uploader.items() if v is not None},
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
        }
