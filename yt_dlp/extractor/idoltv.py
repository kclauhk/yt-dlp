import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    float_or_none,
    int_or_none,
    url_or_none,
    ExtractorError,
)
from .bilibili import BiliBiliIE
from .odnoklassniki import OdnoklassnikiIE
from .youtube import YoutubeIE


def simp_episode(string):
    if re.search(r'\d{6,8}', string):
        return [re.findall(r'\d{6,8}', string)[0][-6:], 'd']
    elif re.search(r'^(SD|HD|FHD|\d{,4}P|標清|超清|高清|正片)', string, re.IGNORECASE):
        return ['RES', 'r']
    elif re.search(r'(第\d+集)|(ep\s*\d+)|(episode\s*\d+)', string, re.IGNORECASE):
        return [re.findall(r'(第|ep\s*|episode\s*)?(\d+)集?', string, re.IGNORECASE)[0][-1], 'e']
    elif re.search(r'^\d{1,4}\D*$', string):
        return [str(int(re.findall(r'\d{1,4}', string)[0])), 'e']
    elif re.search(r'\D\d+-\d+', string):
        return [re.findall(r'\D(\d+-\d+)', string)[0], 'n']
    else:
        return [string, 'n']


class IdoltvIE(InfoExtractor):
    IE_NAME = 'IDOLTV線上看'

    _VALID_URL = r'https?://idoltv\.tv/play/(?P<id>\d+)-(?P<source_id>\d+)-(?P<episode_id>\d+)\.html'

    _TESTS = [
        {
            'url': 'https://idoltv.tv/play/5943-3-2.html',
            'info_dict': {
                'id': '5943-2',
                'title': '摸心第六感 | 第2集',
                'fulltitle': '摸心第六感 第2集 KR5943 Ep2 | 韓劇 | IDOLTV線上看',
                'description': '導演：金錫允 崔寶允 \n主演：韓志旼 李民基 金俊勉 周敏京 \n講述一段鄉村的愛情故事。奉藝奮（韓志旼 飾）是一位擁 有讀心術的獸醫，某天，被下放到鄉村的熱血刑警文張烈（李民基 飾）無意間發現她的這項超能力。在這個清淨的村莊裡，兩人聯手解 決著居民們的各種問題，卻意外捲入一場連續殺人事件。一段搞笑的聯手搜查故事就此展開！',
                'episode': '第2集',
                'episode_number': 2,
                'thumbnail': 'https://idoltv.tv/upload/vod/20230813-1/1da9f9ee7fc5a9797496699f782359ce.jpg',
                'catagory': ['韓劇'],
                'tags': ['2023', '韓國', '奇幻', '喜劇', '愛情', '警察'],
                'release_year': 2023,
                'upload_date': '20230813',
                'average_rating': 10.0
            }
        },
    ]

    def _extract_format(self, video_id, label, media_provider, player_data):
        """
        @param video_id         string
        @param media_provider   string
        @param player_data      dict    player_data json
        return {}               dict    info_dict / formats of a video
        """
        if player_data['from'] == 'bilibili':
            self.to_screen('Extracting embedded URL: ' + player_data['url'])
            if player_data['url'].count('search.bilibili.com') > 0:
                # BiliBiliSearchIE not working
                return {}
            else:
                bili = BiliBiliIE()
                bili._downloader = self._downloader
                return bili._real_extract(player_data['url'])

        elif player_data['from'] == 'okru':
            self.to_screen('Extracting embedded URL: https://ok.ru/videoembed/' + player_data['url'])
            okru = OdnoklassnikiIE()
            okru._downloader = self._downloader
            return okru._real_extract('https://ok.ru/videoembed/' + player_data['url'])

        elif player_data['from'] == 'youtube' and len(player_data['url']) == 11:
            self.to_screen('Extracting embedded URL: https://youtu.be/' + player_data['url'])
            youtube = YoutubeIE()
            youtube._downloader = self._downloader
            return youtube._real_extract('https://youtu.be/' + player_data['url'])

        elif url_or_none(player_data['url']):
            f = self._extract_m3u8_formats_and_subtitles(player_data['url'], video_id, fatal=False)[0]
            if f:
                f[0]['format_id'] = media_provider.replace('雲播', 'yunbo')
                f[0]['ext'] = ('mp4' if not f[0]['ext'] else f[0]['ext'])
                f[0]['format_note'] = media_provider + ' (' + label + ')'
                # ‘雲播15’ provides lesser info but usually higher resolution and faster download
                if f[0]['url'].count('.haiwaikan.com') > 0:
                    f[0]['preference'] = 1
                return {'formats': [f[0]]}
            else:
                return {}

    def _real_extract(self, url):
        id, source_id, episode_id = self._match_valid_url(url).group('id', 'source_id', 'episode_id')
        video_id = str(id) + '-' + str(episode_id)
        webpage = (self._download_webpage(url, video_id)).replace('&nbsp;', ' ')
        if webpage.count('<h1>404</h1>'):
            raise ExtractorError('Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)')
        fulltitle = self._html_extract_title(webpage) or self._html_search_meta(['og:title', 'twitter:title'], webpage, 'title')
        video_inf = re.findall(r'<h2 class="title margin_0">(.+)</h2>[\S\s]*<p class="nstem data ms_p margin_0">\s*(<span class[\S\s]+</span></span>)?\s*(<a href=.+</a>)[\S\s]*<div class="panel play_content.+>\s*<p>([\S\s]+)</p>\s*</div>[\S\s]*播放地址', webpage)[0]
        title = video_inf[0] or fulltitle.split(' | ')[0]
        episode = title.split(' | ')[1]
        description = clean_html(video_inf[3]) or (self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage, 'description').split('|')[-1])
        catagory = fulltitle.split(' | ')[1]
        tags = clean_html(video_inf[2]).split(' ')
        average_rating = float_or_none(clean_html(video_inf[1]))
        thumbnail = self._html_search_meta(['og:image', 'twitter:image'], webpage, 'thumbnail')
        upload_date = self._html_search_regex(r'vod/(\d{8})-', thumbnail, 'upload_date', default=None, fatal=False)
        # current video media source
        media_src = re.findall(r'<li class="tab-play conch-01" title="(.+)"><a href=.*>', webpage)
        player_data = [self._parse_json(j, video_id, fatal=False) for j in re.findall(r'>var player_data=({.+})</script>', webpage)][0]
        # other video media sources: [('source_name', 'webpage_url')]
        video_src = re.findall(r'<li class="tab-play " title="(.+)"><a href="(.+?)">.*nbsp;(.+)</a></li>', webpage)
        needle = simp_episode(episode)
        for h in re.findall(r'當前資源由(.+?)提供([\S\s]*?)展開', webpage):
            url_found = None
            if needle[1] == 'd':
                url_found = re.findall(r'<li.*><a href="(.+)">\d{0,2}%s.*</a></li>' % (needle[0]), h[1])
            elif needle[1] == 'e':
                url_found = re.findall(r'<li.*><a href="(.+)">[第|0]?%s[集|\D|<]*\/a><\/li>' % (needle[0]), h[1])
            elif needle[1] == 'n':
                url_found = re.findall(r'<li.*><a href="(.+)">[第|0]?%s集?\D*<\/a><\/li>' % (needle[0]), h[1])

            if url_found and url.count(url_found[0]) == 0 and video_src.count((h[0], url_found[0])) == 0:
                video_src.append((h[0], url_found[0], True))

        entries = None
        formats = []
        if player_data['url']:
            fmt = self._extract_format(video_id, episode, media_src[0], player_data)
            if fmt:
                if 'entries' in fmt:
                    entries = fmt['entries']
                elif 'formats' in fmt:
                    formats = formats + fmt['formats']

        for src in video_src:
            ep = self._html_search_regex(r'<li ><a href="%s">(.+)</a></li>' % (src[1]), webpage, 'episode', default='', fatal=False)
            if simp_episode(ep)[0] == simp_episode(episode)[0] or src[2]:
                self.to_screen('Extracting URL: ' 'https://idoltv.tv' + src[1])
                page = (self._download_webpage('https://idoltv.tv' + src[1], video_id)).replace('&nbsp;', ' ')
                data = [self._parse_json(j, video_id, fatal=False) for j in re.findall(r'>var player_data=({.*})</script>', page)][0]

                if data['url']:
                    fmt = self._extract_format(video_id, ep, src[0], data)
                    # add Bilibili playlist if video not yet found
                    if fmt:
                        if 'entries' in fmt and not formats:
                            entries = fmt['entries']
                        elif 'formats' in fmt:
                            formats = formats + fmt['formats']

        info_dict = {
            'id': str(video_id),
            'title': title,
            'fulltitle': fulltitle,
            'description': description,
            'episode': None,
            'episode_number': None,
            'thumbnail': thumbnail,
            'catagory': [catagory],
            'tags': tags,
            'release_year': int_or_none(tags[0]),
            'upload_date': upload_date,
            'average_rating': average_rating,
        }
        if (player_data['link_next'] or player_data['link_pre']):
            info_dict['episode'] = episode
            info_dict['episode_number'] = int(episode_id)

        if formats:
            info_dict['formats'] = formats
            return info_dict
        elif entries:
            return self.playlist_result(entries, **info_dict)
        else:
            self.raise_no_formats('Video unavailable', video_id=video_id, expected=True)


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
                'description': '導演：金錫允 崔寶允 \n主演：韓志旼 李民基 金俊勉 周敏京 \n講述一段鄉村的愛情故事。奉藝奮（韓志旼 飾）是一位擁有讀心術的獸醫，某天 ，被下放到鄉村的熱血刑警文張烈（李民基 飾）無意間發現她的這項超能力。在這個清淨的村莊裡，兩人聯手解決著居民們的各種問題 ，卻意外捲入一場連續殺人事件。一段搞笑的聯手搜查故事就此展開！',
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
        if webpage.count('<h1>404</h1>'):
            raise ExtractorError('Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)')
        fulltitle = (self._html_extract_title(webpage)
                     or self._html_search_meta(['og:title', 'twitter:title'], webpage, 'title'))
        video_inf = re.findall(r'<h2 class="title[\S\s]*itemprop="name">(.+)</span>[\S\s]*id="year">.*>(\d+)</a>[\S\s]*id="area">.*>(.+)</a>[\S\s]*id="class">.*>(.+)</a>', webpage)[0]
        cast = re.findall(r'id="actor">(.+)</li>[\S\s]*id="director">(.+?)</li>', webpage)[0]
        title = video_inf[0] or fulltitle.split(' | ')[0]
        release_year = int_or_none(video_inf[1])
        region = video_inf[2]
        catagory = video_inf[3] or fulltitle.split(' | ')[1]
        description = (clean_html(cast[1]) + ' \n' + clean_html(cast[0]) + ' \n'
                       + (self._html_search_regex(r'<div class="content_desc full_text clearfix" id="description">([\S\s]+?)</span>', webpage, 'description', default=None, fatal=False)
                          or self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage, 'description').split('|')[-1]))
        thumbnail = self._html_search_meta(['og:image', 'twitter:image'], webpage, 'thumbnail')
        upload_date = self._html_search_regex(r'vod/(\d{8})-', thumbnail, 'upload_date', default=None, fatal=False)
        average_rating = float_or_none(self._html_search_regex(r'<span class="star_tips">(\d+\.\d+)</span>', webpage, 'star_tips', default=None, fatal=False))
        playlist = {}
        entries = []
        for h in re.findall(r'當前資源由([\S\s]+?)展開', webpage):
            pl = re.findall(r'^(.+?)\(?\)?提供[\S\s]*<ul class="content_playlist list_scroll clearfix">\s+([\S\s]+?)\s+</ul>', h)[0]
            if pl[0] != 'bilibili':
                lt = []
                for url in re.findall(r'<a itemprop="url" href="(.+)">(.+)</a>', pl[1]):
                    if simp_episode(url[1])[0] not in playlist:
                        playlist[simp_episode(url[1])[0]] = url[0]
                        lt.append(url[0])
                entries = entries + [
                    self.url_result('https://idoltv.tv' + u, IdoltvIE)
                    for u in lt]

            elif pl[0] == 'bilibili':
                for url in re.findall(r'<a itemprop="url" href="(.+)">(.+)</a>', pl[1]):
                    idoltv = IdoltvIE()
                    idoltv._downloader = self._downloader
                    bili = idoltv._real_extract('https://idoltv.tv' + url[0])
                    if 'entries' in bili:
                        entries = entries + list(bili['entries'])
                    else:
                        entries = entries + [self.url_result(bili['webpage_url'], BiliBiliIE)]

        info_dict = {
            'id': id,
            'title': title,
            'fulltitle': fulltitle,
            'description': description,
            'thumbnail': thumbnail,
            'catagory': [catagory],
            'region': region,
            'release_year': release_year,
            'upload_date': upload_date,
            'average_rating': average_rating,
        }

        return self.playlist_result(entries, **info_dict)
