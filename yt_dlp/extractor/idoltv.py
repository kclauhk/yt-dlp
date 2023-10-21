import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    float_or_none,
    url_or_none,
)


class IdoltvIE(InfoExtractor):
    IE_NAME = 'IDOLTV線上看'

    _VALID_URL = r'https?://idoltv\.tv/play/(?P<id>\d+)-(?P<source_id>\d+)-(?P<episode_id>\d+)\.html'

    _TESTS = [
        {
            'url': 'https://idoltv.tv/play/5943-3-2.html',
            'info_dict': {
                'id': '5943-2',
                'title': '摸心第六感 | 第2集',
                'description': '講述一段鄉村的愛情故事。奉藝奮（韓志旼 飾）是一位擁有讀 心術的獸醫，某天，被下放到鄉村的熱血刑警文張烈（李民基 飾）無意間發現她的這項超能力。在這個清淨的村莊裡，兩人聯手解決著 居民們的各種問題，卻意外捲入一場連續殺人事件。一段搞笑的聯手搜查故事就此展開！',
                'thumbnail': 'https://idoltv.tv/upload/vod/20230813-1/1da9f9ee7fc5a9797496699f782359ce.jpg',
                'catagory': ['韓劇'],
                'tags': ['2023','韓國','奇幻','喜劇','愛情','警察'],
                'release_year': 2023,
                'upload_date': '20230813',
                'average_rating': 10.0,
                'fulltitle': '摸心第六感 第2集 KR5943 Ep2 | 韓劇 | IDOLTV線上看',
                'episode': '第2集',
                'episode_number': 2
            }
        },
    ]

    def _real_extract(self, url):
        id, source_id, episode_id = self._match_valid_url(url).group('id', 'source_id', 'episode_id')
        video_id = str(id) + '-' + str(episode_id)
        webpage = (self._download_webpage(url, video_id)).replace('&nbsp;', ' ')
        fulltitle = (self._html_extract_title(webpage) or
                     self._html_search_meta(['og:title', 'twitter:title'], webpage, 'title'))
        title = (self._html_search_regex(r'<h2 class="title margin_0">(.+?)</h2>', webpage, 'title', default=None, fatal=False) or
                 fulltitle.split(' | ')[0])
        catagory = fulltitle.split(' | ')[1]
        description = (self._html_search_regex(r'<div class="panel play_content" style="display:none;">((.|\s)*?)</div>', webpage, 'description', default=None, fatal=False) or
                       self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage, 'description').split('|')[-1]).split('\n')[-1]
        thumbnail = self._html_search_meta(['og:image', 'twitter:image'], webpage, 'thumbnail')
        upload_date = self._html_search_regex(r'vod/(\d{8})-', thumbnail, 'upload_date', default=None, fatal=False)
        average_rating = float_or_none(self._html_search_regex(r'<span class="text_score">(\d+\.\d+)', webpage, 'text_score', default=None, fatal=False))
        tags = (self._html_search_regex(r'<span class="split_line"></span></span>\s*(.*)[^</p>]', webpage, 'tag', default=None, fatal=False) or
                self._html_search_regex(r'<p class="nstem data ms_p margin_0">\s*(.*)[^</p>]', webpage, 'tag', default=None, fatal=False)).split(' ')
        conch = re.findall(r'<li class="tab-play conch-01" title="(.+)"><a href="(.+?)">', webpage)
        tab_play = re.findall(r'<li class="tab-play " title="(.+)"><a href="(.+?)">', webpage)
        playlist = re.findall(r'<li ><a href="(.+?)">(.+?)</a></li>',
                    re.sub(r'(\n|\t)+', '', (re.findall(r'<ul class="content_playlist list_scroll clearfix">((.|\s)+?)</ul>', webpage) or (' '))[0][0]))
        video_data = [self._parse_json(j, video_id, fatal=False) for j in re.findall(r'>var player_data=({.*})</script>', webpage)]

        formats = []
        if url_or_none(video_data[0]['url']):
            f = self._extract_m3u8_formats_and_subtitles(video_data[0]['url'], video_id, fatal=False)[0]
            if f:
                f[0]['format_id'] = re.sub('[^0-9]+', '', conch[0][0])
                f[0]['ext'] = ('mp4' if not f[0]['ext'] else f[0]['ext'])
                f[0]['format_note'] = conch[0][0]
                if not 'width' in f[0].keys() and not 'height' in f[0].keys() and title.count(' 1080P') > 0:
                    f[0]['width'], f[0]['height'] = 1920, 1080
                # ‘雲播15’ provides lesser info but usually higher resolution and faster download
                if f[0]['url'].count('.haiwaikan.com') > 0:
                    f[0]['preference'] = 1
                formats.append(f[0])

        for s in tab_play:
            page = (self._download_webpage('https://idoltv.tv%s' % (s[1]), video_id)).replace('&nbsp;', ' ')
            t = (self._html_search_regex(r'<h2 class="title margin_0">(.+?)</h2>', page, 'title', default=None, fatal=False) or
                 self._html_extract_title(page).split(' | ')[0])
            v = [self._parse_json(j, video_id, fatal=False) for j in re.findall(r'>var player_data=({.*})</script>', page)]
            if url_or_none(v[0]['url']):
                f = self._extract_m3u8_formats_and_subtitles(v[0]['url'], video_id, fatal=False)[0]
                if f:
                    f[0]['format_id'] = re.sub('[^0-9]+', '', s[0])
                    f[0]['ext'] = ('mp4' if not f[0]['ext'] else f[0]['ext'])
                    f[0]['format_note'] = s[0]
                    if not 'width' in f[0].keys() and not 'height' in f[0].keys() and t.count(' 1080P') > 0:
                        f[0]['width'], f[0]['height'] = 1920, 1080
                    # ‘雲播15’ provides lesser info but usually higher resolution and faster download
                    if f[0]['url'].count('.haiwaikan.com') > 0:
                        f[0]['preference'] = 1
                    formats.append(f[0])

        if not formats:
            self.raise_no_formats('Video unavailable', video_id=video_id, expected=True)

        info_dict = {
            'id': str(video_id),
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'catagory': [catagory],
            'tags': tags,
            'release_year': int_or_none(tags[0]),
            'upload_date': upload_date,
            'average_rating': average_rating,
            'formats': formats,
            'fulltitle': fulltitle,
        }
        if (video_data[0]['link_next'] or video_data[0]['link_pre']) and len(playlist) > 1:
            info_dict['episode'] = (self._html_search_regex(r'<h2 class="title margin_0">(.+?)</h2>', webpage, 'title', fatal=False).split(' | '))[1]
            info_dict['episode_number'] = int(episode_id)

        return info_dict


class IdoltvVodIE(IdoltvIE):
    IE_NAME = 'IDOLTV線上看:VOD'

    _VALID_URL = r'https?://idoltv\.tv/vod/(?P<id>\d+)\.html'

    _TESTS = [
        {
            'url': 'https://idoltv.tv/vod/5943.html',
            'info_dict': {
                'id': '5943',
                'title': '摸心第六感',
                'fulltitle': '摸心第六感 線上看 | 韓劇 | IDOLTV線上看',
                'description': '講述一段鄉村的愛情故事。奉藝奮（韓志旼 飾）是一位擁有讀心術的獸醫，某天，被下放到鄉村的熱血刑警文張烈（李民基 飾）無意間發現她的這項超能力。在這個清淨的村莊裡，兩人聯手解決著居民們的各種問題，卻意外捲入一場連續殺人事件。一段搞笑的聯手搜查故事就此展開！',
                'thumbnail': 'https://idoltv.tv/upload/vod/20230813-1/1da9f9ee7fc5a9797496699f782359ce.jpg',
                'catagory': ['韓劇'],
                'region': '韓國',
                'release_year': 2023,
                'upload_date': '20230813',
                'average_rating': 10.0
            }
        },
    ]

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = (self._download_webpage(url, id)).replace('&nbsp;', ' ')
        fulltitle = (self._html_extract_title(webpage) or
                     self._html_search_meta(['og:title', 'twitter:title'], webpage, 'title'))
        title = (self._html_search_regex(r'<h2 class="title" id="name">\s*<span itemprop="name">(.+)</span>\s*</h2>', webpage, 'title', default=None, fatal=False) or
                 fulltitle.split(' | ')[0])
        catagory = (self._html_search_regex(r'分類：</span><a href=".+">(.+)</a>', webpage, 'title', default=None, fatal=False) or
                    fulltitle.split(' | ')[1])
        description = (self._html_search_regex(r'<div class="content_desc full_text clearfix" id="description">((.|\s)*?)</span>', webpage, 'description', default=None, fatal=False) or
                       self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage, 'description').split('|')[-1])
        thumbnail = self._html_search_meta(['og:image', 'twitter:image'], webpage, 'thumbnail')
        upload_date = self._html_search_regex(r'vod/(\d{8})-', thumbnail, 'upload_date', default=None, fatal=False)
        average_rating = float_or_none(self._html_search_regex(r'<span class="star_tips">(\d+\.\d+)</span>', webpage, 'star_tips', default=None, fatal=False))
        year = self._html_search_regex(r'年份：</span><a href=".+" target="_blank">(\d+)</a>', webpage, 'year', default=None, fatal=False)
        region = self._html_search_regex(r'地區：</span><a href=".+" target="_blank">(.+)</a>', webpage, 'region', default=None, fatal=False)
        playlist = re.findall(r'<li><a itemprop="url" href="(.+?)">',
                    re.sub(r'(\n|\t)+', '', (re.findall(r'<ul class="content_playlist list_scroll clearfix">((.|\s)+?)</ul>', webpage) or (' '))[0][0]))
        entries = [
            self.url_result('https://idoltv.tv' + h, IdoltvIE)
            for h in playlist]

        info_dict = {
            'id': id,
            'title': title,
            'fulltitle': fulltitle,
            'description': description,
            'thumbnail': thumbnail,
            'catagory': [catagory],
            'region': region,
            'release_year': int_or_none(year),
            'upload_date': upload_date,
            'average_rating': average_rating,
        }

        return self.playlist_result(entries, **info_dict)
