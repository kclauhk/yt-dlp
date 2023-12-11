import re
import math
import urllib.parse

from datetime import datetime
from .common import InfoExtractor
from ..utils import (
    clean_html,
    float_or_none,
    int_or_none,
    url_or_none,
    ExtractorError,
    PlaylistEntries,
)
from .bilibili import BiliBiliIE
from .odnoklassniki import OdnoklassnikiIE
from .youtube import YoutubeIE


class IdoltvIE(InfoExtractor):
    IE_NAME = 'IDOLTV'
    _VALID_URL = r'(idoltv:|https?://idoltv\.tv/play/)(?P<id>\d+)-(?P<source_id>\d+)-(?P<episode_id>\d+)'
    _TESTS = [{
        'url': 'https://idoltv.tv/play/5943-3-2.html',
        'info_dict': {
            'id': '5943-3-2',
            'title': '\u6478\u5fc3\u7b2c\u516d\u611f | \u7b2c2\u96c6',
            'fulltitle': '\u6478\u5fc3\u7b2c\u516d\u611f | \u7b2c2\u96c6',
            'description': '\u5c0e\u6f14\uff1a\u91d1\u932b\u5141 \u5d14\u5bf6\u5141 \n\u4e3b\u6f14\uff1a\u97d3\u5fd7\u65fc \u674e\u6c11\u57fa \u91d1\u4fca\u52c9 \u5468\u654f\u4eac \n\u8b1b\u8ff0\u4e00\u6bb5\u9109\u6751\u7684\u611b\u60c5\u6545\u4e8b\u3002\u5949\u85dd\u596e\uff08\u97d3\u5fd7\u65fc \u98fe\uff09\u662f\u4e00\u4f4d\u64c1\u6709\u8b80\u5fc3\u8853\u7684\u7378\u91ab\uff0c\u67d0\u5929\uff0c\u88ab\u4e0b\u653e\u5230\u9109\u6751\u7684\u71b1\u8840\u5211\u8b66\u6587\u5f35\u70c8\uff08\u674e\u6c11\u57fa \u98fe\uff09\u7121\u610f\u9593\u767c\u73fe\u5979\u7684\u9019\u9805\u8d85\u80fd\u529b\u3002\u5728\u9019\u500b\u6e05\u6de8\u7684\u6751\u838a\u88e1\uff0c\u5169\u4eba\u806f\u624b\u89e3\u6c7a\u8457\u5c45\u6c11\u5011\u7684\u5404\u7a2e\u554f\u984c\uff0c\u537b\u610f\u5916\u6372\u5165\u4e00\u5834\u9023\u7e8c\u6bba\u4eba\u4e8b\u4ef6\u3002\u4e00\u6bb5\u641e\u7b11\u7684\u806f\u624b\u641c\u67e5\u6545\u4e8b\u5c31\u6b64\u5c55\u958b\uff01',
            'episode': '\u7b2c2\u96c6',
            'episode_number': 2,
            'thumbnail': 'https://idoltv.tv/upload/vod/20230813-1/1da9f9ee7fc5a9797496699f782359ce.jpg',
            'catagory': ['\u97d3\u5287'],
            'tags': ['2023', '\u97d3\u570b', '\u5947\u5e7b', '\u559c\u5287', '\u611b\u60c5', '\u8b66\u5bdf'],
            'release_year': 2023,
            'average_rating': 10.0,
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
                z.append((float(r'%s.%s' % (n[0], n[1].zfill(4))), part, 'e'))
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
        # print(links)
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
            try:
                return youtube._real_extract('https://www.youtube.com/watch?v=' + player_data['url'])
            except ExtractorError as e:
                youtube.to_screen(e)
        elif url_or_none(player_data['url']):
            f = self._extract_m3u8_formats_and_subtitles(player_data['url'], video_id, errnote=None, fatal=False)[0]
            if f:
                f[0]['format_id'] = media_source.replace('雲播', 'yunbo')
                f[0]['ext'] = ('mp4' if not f[0]['ext'] else f[0]['ext'])
                f[0]['format_note'] = '%s (%s)' % (episode_label, media_source)
                # ‘雲播15’ provides lesser info but usually higher resolution and faster download
                if f[0]['url'].count('.haiwaikan.com') > 0:
                    f[0]['preference'] = 1
                return {'formats': [f[0]]}
            else:
                return {}
        else:
            return {}

    def _real_extract(self, url):
        vid, source_id, episode_id = self._match_valid_url(url).group('id', 'source_id', 'episode_id')
        video_id = str(vid) + '-' + str(source_id) + '-' + str(episode_id)
        url = 'https://idoltv.tv/play/' + vid + '-' + source_id + '-' + episode_id + '.html'
        webpage = (self._download_webpage(url, video_id)).replace('&nbsp;', ' ')
        if webpage.count('<h1>404</h1>'):
            raise ExtractorError('Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
        # extract video info
        fulltitle = self._html_extract_title(webpage) or self._html_search_meta(['og:title', 'twitter:title'], webpage, 'title')
        catagory = fulltitle.split(' | ')[1]
        video_inf = re.findall(r'<h2 class="title margin_0">(.+)</h2>[\s\S]*<p class="nstem data ms_p margin_0">\s*(<span class[\s\S]+</span></span>)?\s*(<a href=.+</a>)[\s\S]*<div class="panel play_content.+>\s*<p>([\s\S]+)</p>\s*</div>[\s\S]*播放地址', webpage)[0]
        title = video_inf[0] or fulltitle.split(' | ')[0]
        episode = title.split(' | ')[1] or title.split(' ')[-1]
        epsd = self._parse_episode(episode)
        # print('    episode: ' + episode + "\n       epsd: " + str(epsd))
        average_rating = float_or_none(clean_html(video_inf[1]))
        tags = clean_html(video_inf[2]).split(' ')
        description = clean_html(video_inf[3]) or (self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage, 'description').split('|')[-1])
        thumbnail = self._html_search_meta(['og:image', 'twitter:image'], webpage, 'thumbnail')

        # extract video
        other_src, formats, entries = [], [], None      # other_src: [(webpage_url, episode_label, source_name), ...]
        # video source of current webpage
        video_src = (re.findall(r'<li class="tab-play conch-01" title="(.+)"><a href=.*>', webpage) or [''])[0]
        player_data = [self._parse_json(j, video_id, fatal=False) for j in re.findall(r'<script.*>var player_data=({.+})</script>', webpage)][0]
        if player_data['url']:
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
                    if e[2] == 'd' and abs((datetime.strptime(e[0], '%y%m%d') - datetime.strptime(([x for x in ep if x[1] == e[1] and x[2] == 'd'] or [('500101', '', '')])[0][0], '%y%m%d')).days) == 1:
                        d.append(y)
                if len(z) == 1:
                    other_src.append(z[0])
                elif len(z) == 0 and len(d) == 1:
                    other_src.append(d[0])
        # print("other_src: " + str(other_src))
        for x in other_src:
            self.to_screen('Extracting URL: ' 'https://idoltv.tv' + x[0])
            page = (self._download_webpage('https://idoltv.tv' + x[0], video_id)).replace('&nbsp;', ' ')
            data = [self._parse_json(j, video_id, fatal=False) for j in re.findall(r'<script.*>var player_data=({.*})</script>', page)][0]
            if data['url']:
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
            'episode_number': None,
            'thumbnail': thumbnail,
            'catagory': [catagory],
            'tags': tags,
            'release_year': int_or_none(tags[0]),
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
    IE_NAME = IdoltvIE.IE_NAME + ':vod'
    _VALID_URL = r'(idoltv:|https?://idoltv\.tv/vod/)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://idoltv.tv/vod/5310.html',
        'info_dict': {
            'id': '5310',
            'title': '\u5947\u8e5f2022',
            'fulltitle': '\u5947\u8e5f2022 \u7dda\u4e0a\u770b | \u97d3\u570b\u7db2\u5287 | IDOLTV\u7dda\u4e0a\u770b',
            'description': '\u5c0e\u6f14\uff1a\u672a\u77e5 \n\u4e3b\u6f14\uff1a\u59dc\u65fb\u5152 \u59dc\u6faf\u7199 \u91d1\u8f1d\u6620 \n\u8a72\u7247\u8b1b\u8ff0\u4ee5\u5947\u8de1\u822c\u7684\u611b\u60c5\u529b\u91cf\u514b\u670d\u8a66\u7149\u53bb\u6210\u9577\u7684\u5e74\u8f15\u4eba\u5011\u7684\u6545\u4e8b\u3002\u8591\u6faf\u7199\u98fe\u6f14\u624d\u80fd\u79ae\u8c8c\u5916\u8c8c\u5168\u90fd\u517c\u5099\u7684\u570b\u969b\u660e\u661fKRIS\uff0c\u8591\u654f\u5152\u98fe\u6f14\u5f9e\u611b\u8c46\u5fd7\u9858\u751f\u8b8a\u6210\u73fe\u5728\u5728\u97d3\u570b3\u4ee3\u611b\u8c46\u4f01\u5283\u516c\u53f8\u5236\u4f5c\u9805\u76ee\u7684\u674e\u7d20\u6797\u3002',
            'thumbnail': 'https://idoltv.tv/upload/vod/20220501-1/b71e209f55e4147437432a3b614ec98a.jpg',
            'catagory': ['\u97d3\u570b\u7db2\u5287'],
            'region': '\u97d3\u570b',
            'release_year': 2022,
            'average_rating': 10.0,
        },
        'playlist_count': 14,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = (self._download_webpage('https://idoltv.tv/vod/' + video_id + '.html', video_id)).replace('&nbsp;', ' ')
        if webpage.count('<h1>404</h1>'):
            raise ExtractorError('Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
        # extract video info
        fulltitle = self._html_extract_title(webpage) or self._html_search_meta(['og:title', 'twitter:title'], webpage, 'title')
        video_inf = re.findall(r'<h2 class="title[\s\S]*itemprop="name">(.+)</span>[\s\S]*id="year">.*>(\d+)</a>[\s\S]*id="area">.*>(.+)</a>[\s\S]*id="class">.*>(.+)</a>', webpage)[0]
        title = video_inf[0] or fulltitle.split(' | ')[0]
        release_year = int_or_none(video_inf[1])
        region = video_inf[2]
        catagory = video_inf[3] or fulltitle.split(' | ')[1]
        cast = re.findall(r'id="actor">(.+)</li>[\s\S]*id="director">(.+?)</li>', webpage)[0]
        description = (clean_html(cast[1]) + ' \n' + clean_html(cast[0]) + ' \n'
                       + (self._html_search_regex(r'<div class="content_desc full_text clearfix" id="description">([\s\S]+?)</span>', webpage, 'description', default=None, fatal=False)
                          or self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage, 'description').split('|')[-1]))
        thumbnail = self._html_search_meta(['og:image', 'twitter:image'], webpage, 'thumbnail')
        average_rating = float_or_none(self._html_search_regex(r'<span class="star_tips">(\d+\.\d+)</span>', webpage, 'star_tips', default=None, fatal=False))

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
                        entries = entries + [self.url_result(bili['webpage_url'], BiliBiliIE)]
            else:
                for y in x['links']:
                    epsd = self._parse_episode(y[1])
                    entry = (y[0], float(epsd[0][0]) if epsd[0][2] == 'd' or epsd[0][2] == 'e' else int(''.join(re.findall(r'-(\d+)-(\d+)\.html', y[0])[0])))
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
                                    if e[2] == 'd' and abs((datetime.strptime(e[0], '%y%m%d') - datetime.strptime(([x for x in ep if x[1] == e[1] and x[2] == 'd'] or [('500101', '', '')])[0][0], '%y%m%d')).days) == 1:
                                        d.append(b)
                                if len(z) == 1:
                                    links[j]['links'].remove(z[0])
                                    # print('remove ' + str(z[0]))
                                elif len(z) == 0 and len(d) == 1:
                                    links[j]['links'].remove(d[0])
                                    # print('remove ' + str(d[0]))
        if playlist:
            entries = entries + [self.url_result('https://idoltv.tv' + x[0], IdoltvIE) for x in sorted(playlist, key=lambda x: x[1])]

        info_dict = {
            'id': str(video_id),
            'title': title,
            'fulltitle': fulltitle,
            'description': description,
            'thumbnail': thumbnail,
            'catagory': [catagory],
            'region': region,
            'release_year': release_year,
            'average_rating': average_rating,
        }

        return self.playlist_result(entries, **info_dict)


class IdoltvSearchIE(IdoltvVodIE):
    IE_NAME = IdoltvIE.IE_NAME + ':search'
    _VALID_URL = r'(idoltvsearch(?P<prefix>|[1-9][0-9]*|all):|(?P<http>http)s?://idoltv\.tv/vodsearch\.html\?wd=)(?P<query>[\s\S]+)'
    _TESTS = [{
        'url': 'https://idoltv.tv/vodsearch.html?wd=2022&submit=',
        'info_dict': {
            'id': '2022',
            'title': '\u641c\u5c0b2022',
            'description': '2022\u641c\u5c0b\u7d50\u679c,IDOLTV\u7dda\u4e0a\u770b',
            'release_year': None,
        },
        'playlist_count': 2,
    }, {
        'url': 'idoltvsearchall:2022',
        'info_dict': {
            'id': '2022',
            'title': '\u641c\u5c0b2022',
            'description': '2022\u641c\u5c0b\u7d50\u679c,IDOLTV\u7dda\u4e0a\u770b',
            'release_year': None,
        },
        'playlist_count': 2,
    }]

    def _real_extract(self, url):
        prefix, http, query = self._match_valid_url(url).group('prefix', 'http', 'query')
        query = (urllib.parse.unquote_plus(query).split('&'))[0]
        webpage = self._download_webpage('https://idoltv.tv/vodsearch.html?wd=' + urllib.parse.unquote_plus(query), query, tries=2).replace('&nbsp;', ' ')
        if webpage.count('<h1>404</h1>'):
            raise ExtractorError('Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
        # extract video info
        title = self._html_extract_title(webpage).split(' | ')[0]
        description = self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage, 'description')
        match_total = int(self._html_search_regex(r'\$\(.\.mac_total.\)\.html\(.(\d+).\);', webpage, 'mac_total'))
        self.to_screen(f'{query}: {match_total} result(s) found')

        # generate playlist
        playlist, entries = [], []
        if match_total > 0:
            for x in re.findall(r'<div class="searchlist_titbox">([\s\S]+?)查看詳情', webpage):
                playlist.append(re.findall(r'class="vodlist_title"><a href="(.+)" title="', x)[0])

            items_per_page = len(playlist)
            result_end = min(match_total if prefix == 'all' or http else (int_or_none(prefix) or 1), self.get_param('playlistend') or match_total)
            if result_end > items_per_page:
                # determine page range according to prefix, --playlist-end & --playlist-items
                if self.get_param('playlist_items'):
                    items_end = 0
                    for x in tuple(PlaylistEntries.parse_playlist_items(self.get_param('playlist_items'))):
                        if type(x) is slice:
                            items_end = max(x.stop, items_end) if x.stop else result_end
                        elif type(x) is int:
                            items_end = max(x, items_end) if x > 0 else result_end
                    result_end = items_end
                for i in range(2, math.ceil(result_end / items_per_page) + 1):
                    webpage = self._download_webpage('https://idoltv.tv/vodsearch/page/' + str(i) + '/wd/' + urllib.parse.unquote_plus(query) + '.html', query,
                                                     'Fetching result ' + str((i - 1) * items_per_page + 1) + '-' + str(min(match_total, i * items_per_page)),
                                                     tries=2).replace('&nbsp;', ' ')
                    if webpage.count('<h1>404</h1>'):
                        raise ExtractorError('Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
                    for x in re.findall(r'<div class="searchlist_titbox">([\s\S]+?)查看詳情', webpage):
                        playlist.append(re.findall(r'class="vodlist_title"><a href="(.+)" title="', x)[0])

            entries = [self.url_result('https://idoltv.tv' + x, IdoltvVodIE)
                       for x in playlist[:result_end]]

        info_dict = {
            'id': str(query),
            'title': title,
            'description': description,
        }

        return self.playlist_result(entries, **info_dict)
