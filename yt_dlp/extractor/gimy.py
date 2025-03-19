import datetime
import itertools
import re
import urllib.parse

from .common import InfoExtractor, SearchInfoExtractor
from ..postprocessor import FFmpegPostProcessor
from ..utils import (
    ExtractorError,
    get_element_by_id,
    int_or_none,
    parse_codecs,
    traverse_obj,
    url_or_none,
)


class GimyIE(InfoExtractor):
    IE_NAME = 'gimy'
    _VALID_URL = r'(gimy:|https?://gimy\.(?:cc|la)/(?:index\.php/)?(?:play|video)/)(?P<id>\d+)-(?P<source_id>\d+)-(?P<episode_id>\d+)'
    _TESTS = [{
        'url': 'https://gimy.la/play/225461-8-14.html',
        'info_dict': {
            'id': '225461-8-14',
            'title': '嗨！營業中第二季 - 第14集',
            'description': 'md5:6f04e797f28fe4841d22137ceb75deef',
            'episode': '第14集',
            'thumbnail': r're:^https?://.*',
            'release_year': 2023,
            'upload_date': '20240721',
            'categories': ['綜藝'],
            'location': '台灣',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://gimy.cc/video/225461-8-15.html',
        'info_dict': {
            'id': '225461-8-15',
            'title': '嗨！營業中第二季 - 第15集',
            'description': 'md5:581099db8fb87748a209c0921a1ed707',
            'episode': '第15集',
            'thumbnail': r're:^https?://.*',
            'release_year': 2023,
            'upload_date': '20240721',
            'categories': ['綜藝'],
            'location': '台灣',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://gimy.cc/index.php/video/243190-2-1.html',
        'info_dict': {
            'id': '243190-2-1',
            'title': '巴黎深淵 - HD',
            'description': 'md5:ae346c34e54a329392340fdbe91b90f6',
            'thumbnail': r're:^https?://.*',
            'release_year': 2024,
            'upload_date': '20240615',
            'categories': ['劇情片'],
            'location': '法國',
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
            if re.search(r'^(SD|HD|FHD|\d{3,4}P|標清|超清|高清|正片|中字|TC)', x, re.IGNORECASE):
                z.append(('RES', part, 'r'))
            if len(z) == 0:
                z.append((x, part, 'n'))
            ep = ep + z
        return sorted(ep, key=lambda x: x[2])

    def _extract_links(self, webpage):
        links = []
        for playlist, src in re.findall(r'id="tabslist"><a href="#(playlist\d)" data-toggle="tab">([\s\S]+?)</a></li>', webpage):
            html = get_element_by_id(playlist, webpage)
            urls = []
            for x in re.findall(r'<li.*><a.* href="([^"]+)".*<span[^>]*>(.+?)</span></a></li>', html):
                urls.append(x)
            links.append({'source': src, 'links': urls})
        return links

    def _extract_formats(self, video_id, episode_label, media_source, video_url):
        """
        @param video_id         string
        @param episode_label    string
        @param media_source     string
        @param video_url        string
        return {}               dict    info_dict / formats of a video
        """
        if url_or_none(video_url):
            _skip_sources = ['.fsvod1.com', 'hnzy.bfvvs.com', '.youkuplaya.com', 'v6.pptvlist.com']
            if all(x not in video_url for x in _skip_sources):
                if f := self._extract_m3u8_formats_and_subtitles(video_url, video_id, errnote=None, fatal=False)[0]:
                    f[0]['format_id'] = self._html_search_regex(r'https?://[^/]*?\.?([\w]+)\.\w+/', f[0]['url'], 'format_id', default='id')
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
        url = 'https://gimy.cc/index.php/video/' + vid + '-' + source_id + '-' + episode_id + '.html'
        webpage = (self._download_webpage(url, video_id)).replace('&nbsp;', ' ')
        if 'aks-404-page' in webpage:
            raise ExtractorError('Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
        # extract video info
        title = (self._html_search_regex(r'<h1 class="title"><a[^>]+>(.+)</h1>', webpage, 'title', default=None)
                 or self._html_extract_title(webpage).split(' - ')[0])
        episode = self._html_search_regex(r'<h1 class="title"><.*</a> - (.*)</h1>', webpage, 'episode', default=None)
        epsd = self._parse_episode(episode)
        desc_meta = self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage, 'description')
        description = (desc_meta[:(desc_meta.index('主要劇情'))] + '主要劇情'
                       + self._html_search_regex(r'<p class="col-pd">\s*([\s\S]+)\s*</p>[\s\S]+劇情簡介', webpage, 'description', default=''))
        categories = self._html_search_regex(r'類型：</span><[^>]+>(.+)</a>', webpage, 'categories', default=None)
        location = self._html_search_regex(r'地區：</span><[^>]+>(.+)</a>', webpage, 'location', default=None)
        release_year = int_or_none(self._html_search_regex(r'年份：</span><[^>]+>(\d+)</a>', webpage, 'release_year', default=None))
        upload_date = self._html_search_meta('og:video:date', webpage, 'upload_date')
        thumbnail = self._html_search_meta(['image', 'og:image', 'twitter:image'], webpage, 'thumbnail')

        # extract video
        other_src, formats, entries = [], [], None      # other_src: [(webpage_url, episode_label, source_name), ...]
        # video source of current webpage
        video_src = self._search_regex(r'<li class="active" id="tabslist"><a[^>]+>(.+)</a></li>', webpage, 'video_src', default='0')
        video_url = self._search_regex(r"video:\s*{\s*url:\s*'(.+)',\s*type:", webpage, 'video_url', default=None)
        if url_or_none(video_url):
            fmt = self._extract_formats(video_id, episode, video_src, video_url)
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
            self.to_screen('Extracting URL: https://gimy.cc' + x[0])
            page = (self._download_webpage('https://gimy.cc' + x[0], video_id)).replace('&nbsp;', ' ')
            video_url = self._search_regex(r"video:\s*{\s*url:\s*'(.+)',\s*type:", page, 'video_url', default=None)
            if url_or_none(video_url):
                fmt = self._extract_formats(video_id, x[1], x[2], video_url)
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
            'description': description,
            'episode': None,
            'thumbnail': url_or_none(thumbnail),
            'release_year': release_year,
            'upload_date': upload_date.replace('-', ''),
            'categories': [categories],
            'location': location,
        }
        if re.search(r'href="[^"].+上一集', webpage) or re.search(r'href="[^"].+下一集', webpage):
            info_dict['episode'] = episode

        if formats:
            info_dict['formats'] = formats
            return info_dict
        elif entries:
            return self.playlist_result(entries, **info_dict)
        else:
            self.raise_no_formats('Video unavailable', video_id=video_id, expected=True)


class GimyDetailIE(GimyIE):
    IE_NAME = GimyIE.IE_NAME + ':detail'
    _VALID_URL = r'(gimy:|https?://gimy\.(?:la|cc)/(?:index\.php/)?detail/)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://gimy.cc/detail/18677.html',
        'info_dict': {
            'id': '18677',
            'title': '工作細胞',
            'description': 'md5:b811926fe6d1cb47e021dce1c2b1cc8f',
            'thumbnail': r're:^https?://.*',
            'release_year': 2018,
            'categories': ['動漫'],
            'location': '日本',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://gimy.cc/index.php/detail/100700.html',
        'info_dict': {
            'id': '100700',
            'title': '工作細胞第二季',
            'description': 'md5:41c066b3ccaf4a80d1628a848631112a',
            'thumbnail': r're:^https?://.*',
            'release_year': 2021,
            'categories': ['動漫'],
            'location': '日本',
        },
        'playlist_mincount': 8,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = (self._download_webpage('https://gimy.cc/index.php/detail/' + video_id + '.html', video_id)).replace('&nbsp;', ' ')
        if 'aks-404-page' in webpage:
            raise ExtractorError('Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
        # extract video info
        title = (self._html_search_regex(r'<h1 class="title">(.+)<!--<span class="score', webpage, 'title', default=None)
                 or self._html_extract_title(webpage).split(' - ')[0])
        desc_meta = self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage, 'description')
        description = (desc_meta[:(desc_meta.index('劇情講述'))] + '劇情講述'
                       + self._html_search_regex(r'<p class="col-pd">\s*([\s\S]+)\s*</p>[\s\S]+劇情簡介', webpage, 'description', default=''))
        categories = self._html_search_regex(r'分類：</span><[^>]+>(.+)</a>', webpage, 'categories', default=None)
        location = self._html_search_regex(r'地區：</span><[^>]+>(.+)</a>', webpage, 'location', default=None)
        release_year = int_or_none(self._html_search_regex(r'年份：</span><[^>]+>(\d+)</a>', webpage, 'release_year', default=None))
        thumbnail = self._html_search_meta(['image', 'og:image', 'twitter:image'], webpage, 'thumbnail')

        # generate playlist
        playlist, entries = [], []
        links = self._extract_links(webpage)
        for i, x in enumerate(links):
            for y in x['links']:
                epsd = self._parse_episode(y[1])
                entry = (y[0], float(epsd[0][0]) if epsd[0][2] == 'd' or epsd[0][2] == 'e' else int(''.join(re.findall(r'-(\d+)-(\d+)\.html', y[0])[0])))
                if entry not in playlist:
                    playlist.append(entry)
                for j, a in enumerate(links):
                    if j > i:
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
            entries = entries + [self.url_result('https://gimy.cc' + x[0], GimyIE) for x in sorted(playlist, key=lambda x: x[1])]

        info_dict = {
            'id': str(video_id),
            'title': title,
            'description': description,
            'thumbnail': url_or_none(thumbnail),
            'release_year': release_year,
            'categories': [categories],
            'location': location,
        }

        return self.playlist_result(entries, **info_dict)


class GimySearchIE(SearchInfoExtractor):
    IE_NAME = GimyIE.IE_NAME + ':search'
    IE_DESC = 'gimy Search'
    _SEARCH_KEY = 'gimysearch'
    _TESTS = [{
        'url': 'gimysearchall:blackpink',
        'info_dict': {
            'id': 'blackpink',
            'title': 'blackpink',
        },
        'playlist_count': 3,
    }]

    def _search_results(self, query):
        for page_number in itertools.count(1):
            webpage = self._download_webpage(f'https://gimy.cc/search/page/{page_number}/wd/' + urllib.parse.unquote_plus(query) + '.html',
                                             query, note=f'Downloading result page {page_number}', tries=2).replace('&nbsp;', ' ')
            if 'aks-404-page' in webpage:
                raise ExtractorError('Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
            search_results = re.findall(r'<h3 class="title"><a href="([^"]+)">.*</a></h3>', webpage)
            if not search_results:
                return
            for result in search_results:
                yield self.url_result('https://gimy.cc' + result, GimyDetailIE)
            if f'href="/search/page/{page_number + 1}/wd/' not in webpage:
                return


class GimySearchURLIE(InfoExtractor):
    _VALID_URL = r'https?://gimy\.(?:la|cc)/search\.html\?wd=(?P<id>[^&]+)'
    _TESTS = [{
        'url': 'https://gimy.cc/search.html?wd=tokyo+mer',
        'info_dict': {
            'id': 'tokyo mer',
            'title': 'tokyo mer',
        },
        'playlist_count': 5,
    }]

    def _real_extract(self, url):
        if query := self._match_id(url):
            query = urllib.parse.unquote_plus(query)
            self.to_screen(f'You can use gimysearch to specify the maximum number of results, e.g. gimysearch20:{query}')
            return self.url_result(f'gimysearchall:{query}', GimySearchIE)
