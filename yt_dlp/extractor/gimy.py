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
    sanitize_url,
    traverse_obj,
    url_or_none,
)


class GimyIE(InfoExtractor):
    IE_NAME = 'gimy.cc'
    _VALID_URL = r'(gimy:|https?://gimy\.cc/(?:index\.php/)?video/)(?P<id>\d+)-(?P<source_id>\d+)-(?P<episode_id>\d+)'
    _TESTS = [{
        'url': 'https://gimy.cc/video/59937-10-24.html',
        'info_dict': {
            'id': '59937-10-24',
            'ext': 'mp4',
            'title': '玩什麼好呢 - E285.250621',
            'description': r're:2019綜藝 玩什麼好呢-E285.250621',
            'episode': 'E285.250621',
            'thumbnail': r're:https?://',
            'upload_date': r're:20[2-9]\d[01]\d[0-3]\d',
            'categories': ['綜藝'],
            'location': '韓國',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://gimy.cc/index.php/video/59937-10-24.html',
        'info_dict': {
            'id': '59937-10-24',
            'ext': 'mp4',
            'title': '玩什麼好呢 - E285.250621',
            'description': r're:2019綜藝 玩什麼好呢-E285.250621',
            'episode': 'E285.250621',
            'thumbnail': r're:https?://',
            'upload_date': r're:20[2-9]\d[01]\d[0-3]\d',
            'categories': ['綜藝'],
            'location': '韓國',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'gimy:59937-10-24',
        'info_dict': {
            'id': '59937-10-24',
            'ext': 'mp4',
            'title': '玩什麼好呢 - E285.250621',
            'description': r're:2019綜藝 玩什麼好呢-E285.250621',
            'episode': 'E285.250621',
            'thumbnail': r're:https?://',
            'upload_date': r're:20[2-9]\d[01]\d[0-3]\d',
            'categories': ['綜藝'],
            'location': '韓國',
        },
        'params': {'skip_download': True},
    }]

    def _parse_episode(self, string):
        episode = string.replace('上', '-1').replace('下', '-2')
        part = (re.findall(r'[-_]0?(\d+)[集）]?$', episode) or re.findall(r'預告', episode)
                or [''])[0]
        ep = []
        for e in episode.split(' '):
            x = []
            if re.search(r'(19|20)?\d*\d{2}[01]\d[0-3]\d', e):
                x.append((re.findall(r'(?:19|20)?\d*(\d{2}[01]\d[0-3]\d)', e)[0][-6:], part, 'd'))
            if re.search(r'(第\d+集)|(ep?\s*\d+)|(episode\s*\d+)|（\d+）', e, re.IGNORECASE):
                x.append((float(re.findall(r'(?:第|ep?\s*|episode\s*|（)+0?(\d+)[集）]?', e, re.IGNORECASE)[0]), part, 'e'))
            elif re.search(r'^\D*\d{1,4}\D*$', e):
                x.append((float(re.findall(r'0?(\d{1,4})', e)[0]), part, 'e'))
            elif re.search(r'^\D?\d{1,4}[-+]\d{1,4}', e):
                n = re.findall(r'0?(\d{1,4})[-+]0?(\d{1,4})', e)[0]
                x.append((float(rf'{n[0]}.{n[1].zfill(4)}'), part, 'e'))
            if re.search(r'^(SD|HD|FHD|\d{3,4}P|標清|超清|高清|正片|中字|TC)', e, re.IGNORECASE):
                x.append(('RES', part, 'r'))
            if len(x) == 0:
                x.append((e, part, 'n'))
            ep = ep + x
        return sorted(ep, key=lambda x: x[2])

    def _extract_other_src(self, links, episode, current_source):
        """
        @param links            list of links [{'source': src, 'links': urls}, {'source': src, 'links': urls}, ...]
        @param episode          string
        @param current_source   name of video source of the current webpage
        return                  list
        """
        src = []
        for l in [l for l in links if l['source'] != current_source]:
            for e in self._parse_episode(episode):
                z, d = [], []
                for y in l['links']:
                    y += (l['source'],)
                    ep = self._parse_episode(y[1])
                    if y not in src and e in ep:
                        z.append(y)
                    if (e[2] == 'd' and abs((datetime.datetime.strptime(e[0], '%y%m%d')
                                             - datetime.datetime.strptime(
                                                ([x for x in ep if x[1] == e[1] and x[2] == 'd']
                                                 or [('500101', '', '')]
                                                 )[0][0], '%y%m%d')
                                             ).days) == 1):
                        d.append(y)
                if len(z) == 1:
                    src.append(z[0])
                elif len(z) == 0 and len(d) == 1:
                    src.append(d[0])
        return src

    def _extract_formats(self, video_url, video_id, episode_label, media_source):
        """
        @param video_url        string
        @param video_id         string
        @param episode_label    string
        @param media_source     string
        return                  generator   list of formats
        """
        if url_or_none(video_url):
            _skip_sources = ['jmcdn.efangcdn.com', 'm3u8.hmrvideo.com', 'hn.bfvvs.com',
                             '.youkuplaya.com', 'v6.pptvlist.com', '.fsvod1.com']
            if all(x not in video_url for x in _skip_sources):
                for f in self._extract_m3u8_formats_and_subtitles(
                        video_url, video_id, errnote=None, fatal=False)[0]:
                    f['format_id'] = self._html_search_regex(r'https?://[^/]*?\.?([\w]{4,}|[^\.]+)[^\.]*\.\w+/',
                                                             f['url'], 'format_id', default='id')
                    f['ext'] = f.get('ext') or 'mp4'
                    f['format_note'] = f'{episode_label} ({media_source})'
                    if '.bfvvs.com' in f['url'] or '.subokk.com' in f['url']:
                        f['preference'] = -2
                        ffmpeg = FFmpegPostProcessor()
                        if ffmpeg.probe_available:
                            if data := ffmpeg.get_metadata_object(f['url']):
                                f.update(traverse_obj(data.get('format'), {
                                    'duration': ('duration', {lambda x: round(float(x), 2) if x else None}),
                                }))
                                for stream in traverse_obj(data, 'streams', expected_type=list):
                                    if stream.get('codec_type') == 'video':
                                        [frames, duration] = [int_or_none(x) for x in (
                                            stream['avg_frame_rate'].split('/') if stream.get('avg_frame_rate') else [None, None])]
                                        f.update({
                                            **traverse_obj(stream, {
                                                'width': ('width', {int_or_none}),
                                                'height': ('height', {int_or_none}),
                                            }),
                                            **{k: v for k, v in parse_codecs(stream.get('codec_name')).items() if k != 'acodec'},
                                            'fps': round(frames / duration, 1) if frames and duration else None,
                                        })
                                    elif stream.get('codec_type') == 'audio':
                                        f.update({
                                            **traverse_obj(stream, {
                                                'audio_channels': ('channels', {int_or_none}),
                                                'asr': ('sample_rate', {int_or_none}),
                                            }),
                                            **{k: v for k, v in parse_codecs(stream.get('codec_name')).items() if k != 'vcodec'},
                                        })
                    yield f

    def _extract_links(self, webpage):
        links = []
        for playlist, src in re.findall(
                r'tabslist"><a href="#(playlist\d)" data-toggle="tab">([\s\S]+?)</a></li', webpage):
            html = get_element_by_id(playlist, webpage)
            urls = []
            for x in re.findall(r'href="([^"]+)".*<span[^>]*>(.+?)</span></a></li', html):
                urls.append(x)
            links.append({'source': src, 'links': urls})
        return links

    def _real_extract(self, url):
        self._downloader.params['nocheckcertificate'] = True
        vid, sid, eid = self._match_valid_url(url).group('id', 'source_id', 'episode_id')
        video_id = f'{vid}-{sid}-{eid}'
        url = f'https://gimy.cc/index.php/video/{video_id}.html'
        webpage = (self._download_webpage(url, video_id)).replace('&nbsp;', ' ')
        if 'aks-404-page' in webpage:
            raise ExtractorError(
                'Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)

        title = (self._html_search_regex(
                    r'h1 class="title"><a[^>]+>(.+)</h1>', webpage, 'title', default=None)
                 or self._html_extract_title(webpage).split(' - ')[0])
        episode = self._html_search_regex(
            r'h1 class="title"><.*</a> - (.*)</h1>', webpage, 'episode', default='')
        desc_meta = self._html_search_meta(
            ['description', 'og:description', 'twitter:description'], webpage, 'description', default=None)
        intro = self._html_search_regex(r'class="col-pd">\s*([\s\S]+)\s*</p>[\s\S]+劇情簡介',
                                        webpage, 'brief_intro', default=None)
        description = ((desc_meta[:desc_meta.index(intro[0:max(intro.find('，'), intro.find(','), 4)])] + intro) if intro
                       else desc_meta)
        categories = self._html_search_regex(
            r'類型：</span><[^>]+>(.+)</a>', webpage, 'categories', default=None)
        location = self._html_search_regex(
            r'地區：</span><[^>]+>(.+)</a>', webpage, 'location', default=None)
        upload_date = self._html_search_meta(
            'og:video:date', webpage, 'upload_date', default=None)
        thumbnail = self._html_search_meta(
            ['image', 'og:image', 'twitter:image'], webpage, 'thumbnail')

        formats = []
        # video source of current webpage
        current_src = self._search_regex(r'ctive" id="tabslist"><a[^>]+>(.+)</a></li>',
                                         webpage, 'video_src', default='0')
        video_url = self._search_regex(r"video:\s*{\s*url:\s*'(.+)',\s*type:",
                                       webpage, 'video_url', default=None)
        if url_or_none(video_url):
            if f := list(self._extract_formats(video_url, video_id, episode, current_src)):
                formats = f
        # other video sources
        for src in self._extract_other_src(self._extract_links(webpage), episode, current_src):
            self.to_screen(f'Extracting URL: https://gimy.cc{src[0]}')
            video_url = self._search_regex(r"video:\s*{\s*url:\s*'(.+)',\s*type:",
                                           self._download_webpage(f'https://gimy.cc{src[0]}', video_id),
                                           'video_url', default=None)
            if url_or_none(video_url):
                if f := list(self._extract_formats(video_url, video_id, src[1], src[2])):
                    formats += f

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'episode': episode if re.search(r'fault" href="[^"].+[上下]一集', webpage) else None,
            'thumbnail': url_or_none(sanitize_url(thumbnail)),
            'upload_date': upload_date.replace('-', '') if upload_date else None,
            'categories': [categories],
            'location': location,
            'formats': formats,
        }


class GimyLaIE(GimyIE):
    IE_NAME = 'gimy.la'
    _VALID_URL = r'(gimy:|https?://gimy\.la/play/)(?P<id>\d+)/?ep(?P<episode_id>\d+)\??sid=?(?P<source_id>\d+)'
    _TESTS = [{
        'url': 'https://gimy.la/play/59937/ep24?sid=10',
        'info_dict': {
            'id': '59937ep24sid10',
            'ext': 'mp4',
            'title': '玩什麼好呢 E285.250621',
            'description': r're:玩什麼好呢E285.250621',
            'episode': 'E285.250621',
            'thumbnail': r're:https?://',
            'categories': ['綜藝'],
            'cast': ['劉在錫'],
            'location': '韓國',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'gimy:59937ep24sid10',
        'info_dict': {
            'id': '59937ep24sid10',
            'ext': 'mp4',
            'title': '玩什麼好呢 E285.250621',
            'description': r're:玩什麼好呢E285.250621',
            'episode': 'E285.250621',
            'thumbnail': r're:https?://',
            'categories': ['綜藝'],
            'cast': ['劉在錫'],
            'location': '韓國',
        },
        'params': {'skip_download': True},
    }]

    def _extract_links(self, webpage):
        links = []
        src = re.findall(r'wiper-slide.*/i>\s*(.+?)<(?:span|/a)', webpage)
        for i, html in enumerate(re.findall(r'y-list-play size"[\s\S]+?</ul>', webpage)):
            urls = []
            for x in re.findall(r'href="(.+)">\s*(?:<span>)?([\s\S]+?)(?:</span>\s*)?</a', html):
                urls.append(x)
            links.append({'source': src[i], 'links': urls})
        return links

    def _real_extract(self, url):
        self._downloader.params['nocheckcertificate'] = True
        vid, sid, eid = self._match_valid_url(url).group('id', 'source_id', 'episode_id')
        video_id = f'{vid}ep{eid}sid{sid}'
        url = f'https://gimy.la/play/{vid}/ep{eid}?sid={sid}'
        webpage = (self._download_webpage(url, video_id)).replace('&nbsp;', ' ')
        if '親愛的：获取数据失败' in webpage:
            raise ExtractorError(
                'Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)

        title = self._html_extract_title(webpage).split(' 線上看')[0]
        episode = self._html_search_regex(
            r'hide cor4".*>\s+<span>(.*)</span>\s+<em class="play-on', webpage, 'episode', default='')
        desc_meta = self._html_search_meta(
            ['description', 'og:description', 'twitter:description'], webpage, 'description')
        intro = self._html_search_regex(
            r'card-text">([\s\S]+?)演員', webpage, 'description', default='').replace('暫無簡介', '')
        description = ((desc_meta[:desc_meta.index(intro[0:max(intro.find('，'), intro.find(','), 4)])] + intro) if intro
                       else desc_meta)
        categories = self._html_search_regex(
            r'history-set" data-name="(?:\[([^]]+)\])?[^"]*" data-mid=', webpage, 'categories', default=None)
        location = self._html_search_regex(
            r'filter/area/[^"]+" title="([^"]+)">', webpage, 'location', default=None)
        upload_date = self._html_search_meta('og:video:date', webpage, 'upload_date', default=None)
        thumbnail = self._html_search_meta(['image', 'og:image', 'twitter:image'], webpage, 'thumbnail')
        cast = re.findall(r'h/actor/[^>]+>([^<]+)</a', webpage)

        formats = []
        # video source of current webpage
        current_src = self._search_regex(r'wiper-slide on nav-dt.*/i>\s+(.*?)<(?:span|/a)',
                                         webpage, 'video_src', default='0')
        video_url = self._search_regex(r"Artplayer[\s\S]+?url:\s'(.+)',\s*type:",
                                       webpage, 'video_url', default=None)
        if url_or_none(video_url):
            if f := list(self._extract_formats(video_url, video_id, episode, current_src)):
                formats = f
        # other video sources
        for src in self._extract_other_src(self._extract_links(webpage), episode, current_src):
            self.to_screen(f'Extracting URL: {src[0]}')
            video_url = self._search_regex(r"Artplayer[\s\S]+?url:\s'(.+)',\s*type:",
                                           self._download_webpage(src[0], video_id),
                                           'video_url', default=None)
            if url_or_none(video_url):
                if f := list(self._extract_formats(video_url, video_id, src[1], src[2])):
                    formats += f

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'episode': episode if '</i>下集</a>' in webpage or int(eid) > 1 else None,
            'thumbnail': url_or_none(sanitize_url(thumbnail)),
            'upload_date': upload_date.replace('-', '') if upload_date else None,
            'categories': [categories],
            'cast': cast,
            'location': location,
            'formats': formats,
        }


class GimyDetailIE(GimyIE):
    IE_NAME = 'gimy:detail'
    _VALID_URL = r'(gimy:|https?://gimy\.(?:la|cc)/(?:index\.php/)?detail/)(?P<id>\d+)(?:/|\.html)?$'
    _TESTS = [{
        'url': 'https://gimy.la/detail/18677/',
        'info_dict': {
            'id': '18677',
            'title': '工作細胞',
            'description': r're:工作細胞劇情介紹',
            'thumbnail': r're:https?://',
            'release_year': 2018,
            'categories': ['動漫'],
            'location': '日本',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://gimy.cc/detail/18677/',
        'only_matching': True,
    }, {
        'url': 'https://gimy.cc/index.php/detail/100700.html',
        'info_dict': {
            'id': '100700',
            'title': '工作細胞第二季',
            'description': r're:工作細胞第二季劇情介紹',
            'thumbnail': r're:https?://',
            'release_year': 2021,
            'categories': ['動漫'],
            'location': '日本',
        },
        'playlist_mincount': 8,
    }, {
        'url': 'gimy:100699',
        'info_dict': {
            'id': '100699',
            'title': '工作細胞black',
            'description': r're:工作細胞black劇情介紹',
            'thumbnail': r're:https?://',
            'release_year': 2021,
            'categories': ['動漫'],
            'location': '日本',
        },
        'playlist_mincount': 13,
    }]

    def _real_extract(self, url):
        def create_playlist(links, regex):
            playlist = []
            for i, x in enumerate(links):
                for y in x['links']:
                    epsd = self._parse_episode(y[1])
                    entry = (y[0],
                             float(epsd[0][0]) if epsd[0][2] == 'd' or epsd[0][2] == 'e'
                                else int(''.join(re.findall(regex, y[0])[0])))
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
                                                             - datetime.datetime.strptime(
                                                                ([x for x in ep if x[1] == e[1] and x[2] == 'd']
                                                                 or [('500101', '', '')]
                                                                 )[0][0], '%y%m%d')
                                                             ).days) == 1):
                                        d.append(b)
                                if len(z) == 1:
                                    links[j]['links'].remove(z[0])
                                elif len(z) == 0 and len(d) == 1:
                                    links[j]['links'].remove(d[0])
            return playlist

        video_id = self._match_id(url)
        webpage = self._download_webpage(
            f'https://gimy.la/detail/{video_id}/', video_id).replace('&nbsp;', ' ')
        if '親愛的：获取数据失败' in webpage:
            webpage = self._download_webpage(
                f'https://gimy.cc/detail/{video_id}/', video_id).replace('&nbsp;', ' ')
            if 'aks-404-page' in webpage:
                raise ExtractorError(
                    'Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
            else:
                playlist = create_playlist(self._extract_links(webpage), r'-(\d+)-(\d+)\.html')
                url_prefix = 'https://gimy.cc'
        else:
            playlist = create_playlist(GimyLaIE._extract_links(self, webpage), r'ep(\d+)\?sid=(\d+)')
            url_prefix = ''

        title = (self._html_search_regex(
                    r'1 class="slide-info-title hide">(.+)</h1>', webpage, 'title', default=None)
                 or self._html_search_regex(
                    r'1 class="title">(.+)<!--<span class="score', webpage, 'title', default=None)
                 or self._html_extract_title(webpage).split(' - ')[0])
        desc_meta = self._html_search_meta(
            ['description', 'og:description', 'twitter:description'], webpage, 'description', default=None)
        intro = (self._html_search_regex(
                    r'_limit" class="text cor3">([\s\S]+?)</div>', webpage, 'brief_intro', default=None)
                 or self._html_search_regex(
                    r'class="col-pd">\s*([\s\S]+)\s*</p>[\s\S]+劇情簡介', webpage, 'brief_intro', default=None)
                 ).replace('暫無簡介', '')
        description = ((desc_meta[:desc_meta.index(intro[0:max(intro.find('，'), intro.find(','), 4)])] + intro) if intro
                       else desc_meta)
        categories = (self._html_search_regex(
                        r'f="/type/.*_blank">(.+)</a>', webpage, 'categories', default=None)
                      or self._html_search_regex(
                        r'分類：</span><[^>]+>(.+)</a>', webpage, 'categories', default=None))
        location = (self._html_search_regex(
                        r'f="/search/area/.*_blank">(.+)</a>', webpage, 'location', default=None)
                    or self._html_search_regex(
                        r'地區：</span><[^>]+>(.+)</a>', webpage, 'location', default=None))
        release_year = int_or_none(
            self._html_search_regex(
                r'f="/search/year/.*_blank">(.+)</a>', webpage, 'release_year', default=None)
            or self._html_search_regex(
                r'年份：</span><[^>]+>(\d+)</a>', webpage, 'release_year', default=None))
        thumbnail = self._html_search_meta(
            ['image', 'og:image', 'twitter:image'], webpage, 'thumbnail')

        entries = []
        if playlist:
            entries = [self.url_result(f'{url_prefix}{x[0]}')
                       for x in sorted(playlist, key=lambda x: x[1])]

        info_dict = {
            'id': str(video_id),
            'title': title,
            'description': description,
            'thumbnail': url_or_none(sanitize_url(thumbnail)),
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
        'playlist_mincount': 2,
    }]

    def _search_results(self, query):
        for page_number in itertools.count(1):
            webpage = self._download_webpage(
                f'https://gimy.cc/search/page/{page_number}/wd/' + urllib.parse.unquote_plus(query) + '.html',
                query, note=f'Downloading result page {page_number}', tries=2).replace('&nbsp;', ' ')
            if 'aks-404-page' in webpage:
                raise ExtractorError(
                    'Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
            search_results = re.findall(
                r'h3 class="title"><a href="([^"]+)">.*</a></h3>', webpage)
            if not search_results:
                return
            for result in search_results:
                yield self.url_result('https://gimy.cc' + result, GimyDetailIE)
            if f'href="/search/page/{page_number + 1}/wd/' not in webpage:
                return


class GimySearchURLIE(InfoExtractor):
    _VALID_URL = r'https?://gimy\.(?:la|cc)/search(?:/|\.html)\?wd=(?P<id>[^&]+)'
    _TESTS = [{
        'url': 'https://gimy.la/search/?wd=tokyo+mer',
        'info_dict': {
            'id': 'tokyo mer',
            'title': 'tokyo mer',
        },
        'playlist_mincount': 2,
    }, {
        'url': 'https://gimy.cc/search.html?wd=tokyo+mer',
        'info_dict': {
            'id': 'tokyo mer',
            'title': 'tokyo mer',
        },
        'playlist_mincount': 2,
    }]

    def _real_extract(self, url):
        if query := self._match_id(url):
            query = urllib.parse.unquote_plus(query)
            self.to_screen(f'You can use gimysearch to specify the maximum number of results, e.g. gimysearch20:{query}')
            return self.url_result(f'gimysearchall:{query}', GimySearchIE)
