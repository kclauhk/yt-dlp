import datetime
import itertools
import re
import urllib.parse

from .common import InfoExtractor, SearchInfoExtractor
from ..postprocessor import FFmpegPostProcessor
from ..utils import (
    ExtractorError,
    clean_html,
    float_or_none,
    int_or_none,
    parse_codecs,
    str_or_none,
    traverse_obj,
    url_or_none,
)

# isort: off
from .bilibili import BiliBiliIE
from .odnoklassniki import OdnoklassnikiIE
from .youtube import YoutubeIE
from .youtube.pot._director import initialize_pot_director


class IdoltvIE(InfoExtractor):
    IE_NAME = 'IDOLTV'
    _VALID_URL = r'(idoltv:|https?://idoltv\.tv/play/)(?P<id>\d+)-(?P<source_id>\d+)-(?P<episode_id>\d+)'
    _TESTS = [{
        'url': 'https://idoltv.tv/play/552-2-60.html',
        'info_dict': {
            'id': '552-2-60',
            'title': 'Running Man | E596.220327',
            'description': 'md5:ba3b0b06b5991bfb9c6b118c724b5f41',
            'episode': 'E596.220327',
            'thumbnail': r're:https?://.*',
            'release_year': 2010,
            'average_rating': float,
            'categories': ['韓綜'],
            'tags': ['2010', '韓國', '搞笑', '遊戲', '真人秀'],
            'cast': ['劉在錫', '池錫辰', '金鍾國', 'HaHa', '宋智孝', '李光洙', '全昭旻', '梁世燦'],
            'ext': 'mp4',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _parse_episode(self, string):
        episode = string.replace('上', '-1').replace('下', '-2')
        part = (re.findall(r'[-_]0?(\d+)[集）]?$', episode) or re.findall(r'預告', episode) or [''])[0]
        ep = []
        for x in episode.split(' '):
            z = []
            if re.search(r'(19|20)?\d{6}', x):
                z.append((re.findall(r'(?:19|20)?(\d{6})', x)[0][-6:], part, 'd'))
            if re.search(r'(第\d+集)|(ep?\s*\d+)|(episode\s*\d+)|（\d+）', x, re.IGNORECASE):
                z.append((float(re.findall(r'(?:第|ep?\s*|episode\s*|（)+0?(\d+)[集）]?', x, re.IGNORECASE)[0]), part, 'e'))
            elif re.search(r'^\D*\d{1,4}\D*$', x):
                z.append((float(re.findall(r'0?(\d{1,4})', x)[0]), part, 'e'))
            elif re.search(r'^\D?\d{1,4}[-+]\d{1,4}', x):
                n = re.findall(r'0?(\d{1,4})[-+]0?(\d{1,4})', x)[0]
                z.append((float(rf'{n[0]}.{n[1].zfill(4)}'), part, 'e'))
            if re.search(r'^(SD|HD|FHD|\d{3,4}P|標清|超清|高清|正片|中字)', x, re.IGNORECASE):
                z.append(('RES', part, 'r'))
            if len(z) == 0:
                z.append((x, part, 'n'))
            ep = ep + z
        return sorted(ep, key=lambda x: x[2])

    def _extract_links(self, webpage):
        links = []
        for src, html in re.findall(r'當前資源由(.+?)\(?\)?提供([\s\S]+?)展開', webpage):
            z = []
            for x in re.findall(r'<li.*><a.* href="(.+)">(.+?)</a></li>', html):
                z.append(x)
            links.append({'source': src, 'links': z})
        return links

    def _extract_formats(self, video_id, episode_label, media_source, player_data):
        """
        @param video_id         string
        @param episode_label    string
        @param media_source     string
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
                try:
                    return bili._real_extract(player_data['url'])
                except ExtractorError as e:
                    bili.to_screen(e)
        elif player_data['from'] == 'okru':
            self.to_screen('Extracting embedded URL: https://ok.ru/videoembed/' + player_data['url'])
            okru = OdnoklassnikiIE()
            okru._downloader = self._downloader
            try:
                return okru._real_extract('https://ok.ru/videoembed/' + player_data['url'])
            except ExtractorError as e:
                okru.to_screen(e)
        elif player_data['from'] == 'youtube' and len(player_data['url']) == 11:
            self.to_screen('Extracting embedded URL: https://www.youtube.com/watch?v=' + player_data['url'])
            youtube = YoutubeIE()
            youtube._downloader = self._downloader
            youtube._pot_director = initialize_pot_director(youtube)
            try:
                return youtube._real_extract('https://www.youtube.com/watch?v=' + player_data['url'])
            except ExtractorError as e:
                youtube.to_screen(e)
        elif url_or_none(player_data['url']):
            _skip_sources = ['v8.tlkqc.com', '.fsvod1.com', 'hnzy.bfvvs.com', 'hnzy3.hnzyww.com', 'cdn6.shzbgyl.com', 'cdn7.hbhaoyi.com']
            if all(x not in player_data['url'] for x in _skip_sources):
                if f := self._extract_m3u8_formats_and_subtitles(player_data['url'], video_id, errnote=None, fatal=False)[0]:
                    f[0]['format_id'] = self._html_search_regex(r'https?://[^/]*?\.?([\w]+)\.\w+/',
                                                                f[0]['url'], 'format_id', default='id')
                    f[0]['ext'] = f[0].get('ext') or 'mp4'
                    f[0]['format_note'] = f'{episode_label} ({media_source})'
                    if '.bfvvs.com' in f[0]['url'] or '.subokk.com' in f[0]['url']:
                        f[0]['preference'] = -2
                        ffmpeg = FFmpegPostProcessor()
                        if ffmpeg.probe_available:
                            if data := ffmpeg.get_metadata_object(f[0]['url']):
                                f[0].update(traverse_obj(data.get('format'), {
                                    'duration': ('duration', {lambda x: round(float(x), 2) if x else None}),
                                }))
                                for stream in traverse_obj(data, 'streams', expected_type=list):
                                    if stream.get('codec_type') == 'video':
                                        [frames, duration] = [int_or_none(x) for x in (
                                            stream['avg_frame_rate'].split('/') if stream.get('avg_frame_rate') else [None, None])]
                                        f[0].update({
                                            **traverse_obj(stream, {
                                                'width': ('width', {int_or_none}),
                                                'height': ('height', {int_or_none}),
                                            }),
                                            **{k: v for k, v in parse_codecs(stream.get('codec_name')).items() if k != 'acodec'},
                                            'fps': round(frames / duration, 1) if frames and duration else None,
                                        })
                                    elif stream.get('codec_type') == 'audio':
                                        f[0].update({
                                            **traverse_obj(stream, {
                                                'audio_channels': ('channels', {int_or_none}),
                                                'asr': ('sample_rate', {int_or_none}),
                                            }),
                                            **{k: v for k, v in parse_codecs(stream.get('codec_name')).items() if k != 'vcodec'},
                                        })
                    return {'formats': [f[0]]}
            return {}

    def _real_extract(self, url):
        self._downloader.params['nocheckcertificate'] = True
        vid, source_id, episode_id = self._match_valid_url(url).group('id', 'source_id', 'episode_id')
        video_id = str(vid) + '-' + str(source_id) + '-' + str(episode_id)
        url = 'https://idoltv.tv/play/' + vid + '-' + source_id + '-' + episode_id + '.html'
        webpage = (self._download_webpage(url, video_id)).replace('&nbsp;', ' ')
        if webpage.count('<h1>404</h1>'):
            raise ExtractorError('Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
        # extract video info
        fulltitle = (self._html_extract_title(webpage)
                     or self._html_search_meta(['og:title', 'twitter:title'], webpage, 'title'))
        categories = fulltitle.split(' | ')[1]
        video_inf = re.findall(r'<h2 class="title margin_0">(.+)</h2>[\s\S]*<p class="nstem data ms_p margin_0">\s*(<span class[\s\S]+</span></span>)?\s*(<a href=.+</a>)[\s\S]*<div class="panel play_content.+>\s*<p>([\s\S]+)</p>\s*</div>[\s\S]*播放地址', webpage)[0]
        title = (video_inf[0]
                 or fulltitle.split(' | ')[0])
        episode = (title.split(' | ')[1]
                   or title.split(' ')[-1])
        epsd = self._parse_episode(episode)
        average_rating = float_or_none(clean_html(video_inf[1]))
        tags = clean_html(video_inf[2]).split(' ')
        description = (clean_html(video_inf[3])
                       or (self._html_search_meta(['description', 'og:description', 'twitter:description'],
                                                  webpage, 'description').split('|')[-1]))
        cast = re.split(r'\s+', self._html_search_regex(r'<p>主演：(.*)</p>', webpage, 'cast', default=''))
        thumbnail = self._html_search_meta(['og:image', 'twitter:image'], webpage, 'thumbnail')

        # extract video
        other_src, formats, entries = [], [], None      # other_src: [(webpage_url, episode_label, source_name), ...]
        # video source of current webpage
        video_src = self._search_regex(r'<li class="tab-play conch-01" title="(.+)"><a href=.*>',
                                       webpage, 'video_src', default='0')
        # player_data = self._parse_json(next(iter(re.findall(r'<script.*>var player_data=({.+})</script>', webpage)), None), video_id, fatal=False)
        for player_url in re.findall(r'video:\s*{\s*url:\s*\'([^\']+)\',', webpage):
            player_data = {
                'url': player_url,
                'from': video_src.lower(),
            }
            fmt = self._extract_formats(video_id, episode, video_src, player_data)
            if fmt:
                if 'entries' in fmt:
                    entries = fmt['entries']
                elif 'formats' in fmt:
                    for f in fmt['formats']:
                        if f not in formats:
                            formats.append(f)
        # other video sources
        links = self._extract_links(webpage)
        for x in [l for l in links if l['source'] != video_src]:
            for e in epsd:
                z, d = [], []
                for y in x['links']:
                    y += (x['source'],)
                    ep = self._parse_episode(y[1])
                    if y not in other_src and e in ep:
                        z.append(y)
                    if (e[2] == 'd' and abs((datetime.datetime.strptime(e[0], '%y%m%d')
                                             - datetime.datetime.strptime(([x for x in ep if x[1] == e[1] and x[2] == 'd']
                                                                           or [('500101', '', '')]
                                                                           )[0][0], '%y%m%d')
                                             ).days) == 1):
                        d.append(y)
                if len(z) == 1:
                    other_src.append(z[0])
                elif len(z) == 0 and len(d) == 1:
                    other_src.append(d[0])
        for x in other_src:
            self.to_screen('Extracting URL: https://idoltv.tv' + x[0])
            page = (self._download_webpage('https://idoltv.tv' + x[0], video_id)).replace('&nbsp;', ' ')
            # data = self._parse_json(next(iter(re.findall(r'<script.*>var player_data=({.*})</script>', page)), None), video_id, fatal=False)
            for player_url in re.findall(r'video:\s*{\s*url:\s*\'([^\']+)\',', page):
                data = {
                    'url': player_url,
                    'from': x[2].lower(),
                }
                fmt = self._extract_formats(video_id, x[1], x[2], data)
                # add Bilibili playlist if video not yet found
                if fmt:
                    if 'entries' in fmt and not formats:
                        entries = fmt['entries']
                    elif 'formats' in fmt:
                        for f in fmt['formats']:
                            if f not in formats:
                                formats.append(f)

        info_dict = {
            'id': video_id,
            'title': title,
            'fulltitle': fulltitle,
            'description': description,
            'episode': None,
            'thumbnail': url_or_none(thumbnail),
            'release_year': int_or_none(tags[0]),
            'average_rating': average_rating,
            'categories': [categories],
            'tags': tags,
            'cast': cast,
            '_format_sort_fields': (  # source_preference is lower for throttled/potentially damaged formats
                'res', 'fps', 'hdr:12', 'vbr', 'vcodec', 'channels', 'abr', 'acodec', 'lang', 'proto'),
        }
        # if (player_data['link_next'] or player_data['link_pre']):
        if re.search(r'href="[^"].+上集', webpage) or re.search(r'href="[^"].+下集', webpage):
            info_dict['episode'] = str_or_none(episode)

        if formats:
            info_dict['formats'] = formats
            return info_dict
        elif entries:
            return self.playlist_result(entries, **info_dict)
        else:
            self.raise_no_formats('Video unavailable', video_id=video_id, expected=True)


class IdoltvVodIE(IdoltvIE):
    IE_NAME = IdoltvIE.IE_NAME + ':vod'
    _VALID_URL = r'(idoltv:|https?://idoltv\.tv/vod/)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://idoltv.tv/vod/5811.html',
        'info_dict': {
            'id': '5811',
            'title': '第八感',
            'description': 'md5:212901f0cccd21ff938a8d5d67ce0241',
            'thumbnail': r're:https?://.*',
            'release_year': 2023,
            'average_rating': float,
            'categories': ['韓國網劇'],
            'location': '韓國',
            'cast': ['임지섭', '오준택'],
        },
        'playlist_count': 10,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = (self._download_webpage('https://idoltv.tv/vod/' + video_id + '.html', video_id)).replace('&nbsp;', ' ')
        if webpage.count('<h1>404</h1>'):
            raise ExtractorError('Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
        # extract video info
        fulltitle = (self._html_extract_title(webpage)
                     or self._html_search_meta(['og:title', 'twitter:title'], webpage, 'title'))
        video_inf = re.findall(r'<h2 class="title[\s\S]*itemprop="name">(.+)</span>[\s\S]*id="year">.*>(\d+)</a>[\s\S]*id="area">.*>(.+)</a>[\s\S]*id="class">.*>(.+)</a>', webpage)[0]
        title = (video_inf[0]
                 or fulltitle.split(' | ')[0])
        release_year = int_or_none(video_inf[1])
        region = video_inf[2]
        categories = (video_inf[3]
                      or fulltitle.split(' | ')[1])
        cast = re.findall(r'id="actor">(.+)</li>[\s\S]*id="director">(.+?)</li>', webpage)[0]
        description = (clean_html(cast[1]) + ' \n' + clean_html(cast[0]) + ' \n'
                       + (self._html_search_regex(r'<div class="content_desc full_text clearfix" id="description">([\s\S]+?)</span>',
                                                  webpage, 'description', default=None)
                          or self._html_search_meta(['description', 'og:description', 'twitter:description'],
                                                    webpage, 'description').split('|')[-1]))
        thumbnail = self._html_search_meta(['og:image', 'twitter:image'], webpage, 'thumbnail')
        average_rating = float_or_none(self._html_search_regex(r'<span class="star_tips">(\d+\.\d+)</span>',
                                                               webpage, 'star_tips', default=None))
        # generate playlist
        playlist, entries = [], []
        links = self._extract_links(webpage)
        for i, x in enumerate(links):
            if x['source'] == 'bilibili':
                for y in x['links']:
                    idoltv = IdoltvIE()
                    idoltv._downloader = self._downloader
                    bili = idoltv._real_extract('https://idoltv.tv' + y[0])
                    if 'entries' in bili:
                        entries = entries + list(bili['entries'])
                    else:
                        entries = [*entries, self.url_result(bili['webpage_url'], BiliBiliIE)]
            else:
                for y in x['links']:
                    epsd = self._parse_episode(y[1])
                    entry = (y[0], (float(epsd[0][0]) if epsd[0][2] == 'd' or epsd[0][2] == 'e'
                                    else int(''.join(re.findall(r'-(\d+)-(\d+)\.html', y[0])[0]))))
                    if entry not in playlist:
                        playlist.append(entry)
                    for j, a in enumerate(links):
                        if a['source'] != 'bilibili' and j > i:
                            for e in epsd:
                                z, d = [], []
                                for b in a['links']:
                                    ep = self._parse_episode(b[1])
                                    if e in ep:
                                        z.append(b)
                                    if (e[2] == 'd' and abs((datetime.datetime.strptime(e[0], '%y%m%d')
                                                             - datetime.datetime.strptime(([x for x in ep if x[1] == e[1] and x[2] == 'd']
                                                                                           or [('500101', '', '')]
                                                                                           )[0][0], '%y%m%d')
                                                             ).days) == 1):
                                        d.append(b)
                                if len(z) == 1:
                                    links[j]['links'].remove(z[0])
                                elif len(z) == 0 and len(d) == 1:
                                    links[j]['links'].remove(d[0])
        if playlist:
            entries = entries + [self.url_result('https://idoltv.tv' + x[0], IdoltvIE)
                                 for x in sorted(playlist, key=lambda x: x[1])]

        info_dict = {
            'id': str(video_id),
            'title': title,
            'fulltitle': fulltitle,
            'description': description,
            'thumbnail': url_or_none(thumbnail),
            'release_year': release_year,
            'average_rating': average_rating,
            'categories': [categories],
            'location': region,
            'cast': re.split(r'\s+', clean_html(cast[0]).replace('主演：', '')),
        }

        return self.playlist_result(entries, **info_dict)


class IdoltvSearchIE(SearchInfoExtractor):
    IE_NAME = IdoltvIE.IE_NAME + ':search'
    IE_DESC = 'IDOLTV Search'
    _SEARCH_KEY = 'idoltvsearch'
    _TESTS = [{
        'url': 'idoltvsearchall:2021',
        'info_dict': {
            'id': '2021',
            'title': '2021',
        },
        'playlist_count': 8,
    }]

    def _search_results(self, query):
        match_total = None
        for page_number in itertools.count(1):
            webpage = self._download_webpage(f'https://idoltv.tv/vodsearch/page/{page_number}/wd/' + urllib.parse.unquote_plus(query) + '.html',
                                             query, note=f'Downloading result page {page_number}', tries=2).replace('&nbsp;', ' ')
            if '<h1>404</h1>' in webpage:
                raise ExtractorError('Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
            match_total = (match_total
                           or int_or_none(self._html_search_regex(r'\$\(.\.mac_total.\)\.html\(.(\d+).\);',
                                                                  webpage, 'mac_total', default=None)))
            if match_total == 0:
                return
            search_results = re.findall(r'<div class="searchlist_titbox">([\s\S]+?)查看詳情', webpage)
            if not search_results:
                return
            for result in search_results:
                if path := self._search_regex(r'class="vodlist_title"><a href="(.+)" title="',
                                              result, 'link', default=None):
                    yield self.url_result('https://idoltv.tv' + path, IdoltvVodIE)
            if f'href="/vodsearch/page/{page_number + 1}/wd/' not in webpage:
                return


class IdoltvSearchURLIE(InfoExtractor):
    _VALID_URL = r'https?://idoltv\.tv/vodsearch\.html\?wd=(?P<id>[^&]+)'
    _TESTS = [{
        'url': 'https://idoltv.tv/vodsearch.html?wd=19&submit=',
        'info_dict': {
            'id': '19',
            'title': '19',
        },
        'playlist_count': 11,
    }]

    def _real_extract(self, url):
        if query := self._match_id(url):
            query = urllib.parse.unquote_plus(query)
            self.to_screen(f'You can use idoltvsearch to specify the maximum number of results, e.g. idoltvsearch20:{query}')
            return self.url_result(f'idoltvsearchall:{query}', IdoltvSearchIE)
