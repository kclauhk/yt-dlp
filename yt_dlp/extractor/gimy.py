import itertools
import json
import re
import time
import urllib.parse

try:
    import nodriver as nd
    from nodriver import (
        loop,
        start,
    )
    nd_available = True
except ImportError:
    nd_available = False

from .common import InfoExtractor, SearchInfoExtractor
from ..networking.exceptions import (
    HTTPError,
    TransportError,
)
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    sanitize_url,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class GimyIE(InfoExtractor):
    IE_NAME = 'gimy:ep'
    _VALID_URL = r'(gimy:|(?P<base_url>https?://gimy[^/]*\.[^/]+)/[ep][^/]*/)(?P<id>\d+-\d+-\d+)(?:/|\.html)?$'
    _TESTS = [{
        'url': 'https://gimytv.ai/ep/141543-7-100.html',
        'info_dict': {
            'id': '141543-7-100',
            'ext': 'mp4',
            'title': '我獨自生活',
            'description': r're:《我獨自生活》是由韓國MBC電視臺新年播放的特輯',
            'episode': '第595期',
            'thumbnail': r're:https?://',
            'categories': ['綜藝'],
            'cast': ['盧洪哲', 'Defconn', '金泰元', '金光奎'],
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://gimy01.tv/eps/164378-2-1.html',
        'info_dict': {
            'id': '164378-2-1',
            'ext': 'mp4',
            'title': '穿著Prada的惡魔',
            'description': r're:初涉社會的安德麗婭•桑切絲（安妮•海瑟薇飾）',
            'thumbnail': r're:https?://',
            'categories': ['愛情片'],
            'cast': 'count:7',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'gimy:256836-6-3',
        'info_dict': {
            'id': '256836-6-3',
            'ext': 'mp4',
            'title': '歡樂頌5',
            'description': r're:22樓五個姑娘彼此相伴的日子還在繼續，',
            'episode': '第03集',
            'thumbnail': r're:https?://',
            'categories': ['陸劇'],
            'cast': 'count:9',
        },
        'params': {'skip_download': True},
    }]

    _BASE_URL = 'https://gimy01.tv'

    def _parse_episode(self, string):
        episode = re.sub(r'完結$', '', string.strip())
        brackets = [('', ''), ('\\(', '\\)'), ('（', '）')]
        numbering = [range(1, 11), '一二三四五六七八九十', 'ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ',
                     '①②③④⑤⑥⑦⑧⑨⑩', '⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽']
        part = ''
        for i, bkt in enumerate(brackets):
            for j, numbers in enumerate(numbering):
                if not (i == 0 and j == 0):
                    for k, v in zip(list(numbers), range(1, 11), strict=False):
                        if re.search(rf'{bkt[0]}{k}{bkt[1]}$', episode):
                            part = v
                            episode = re.sub(rf'{bkt[0]}{k}{bkt[1]}$', '', episode)
        if re.search(r'上$', episode):
            part = 1
        elif re.search(r'下$', episode):
            part = 2
        else:
            part = ((re.findall(r'[-_]0?(\d+)[集）]?$', episode)
                     or re.findall(r'預告', episode)
                     or ['']
                     )[0]
                    or part)
        result = []
        for e in episode.split(' '):
            x = []
            if re.search(r'(19|20)?\d*\d{2}-[01]?\d-[0-3]?\d', e):
                d = re.findall(r'(?:19|20)?\d*(\d{2}[01]\d[0-3]\d)',
                               e.replace('-', ''))[0][-6:]
                x.append((d, '' if d.endswith(part) else part, 'd'))
            elif re.search(r'(19|20)?\d*\d{2}[01]\d[0-3]\d', e):
                x.append((re.findall(r'(?:19|20)?\d*(\d{2}[01]\d[0-3]\d)', e)[0][-6:],
                          part, 'd'))
            if re.search(r'(第\d+集)|(ep?\s*\d+)|(episode\s*\d+)|（\d+）', e, re.IGNORECASE):
                x.append((float(re.findall(r'(?:第|ep?\s*|episode\s*|（)+0?(\d+)[集）]?', e,
                                           re.IGNORECASE)[0]),
                          part, 'e'))
            elif re.search(r'^\D*\d{1,4}\D*$', e):
                x.append((float(re.findall(r'0?(\d{1,4})', e)[0]), part, 'e'))
            elif re.search(r'^\D?\d{1,4}[-+]\d{1,4}', e):
                if not re.search(r'(19|20)?\d*\d{2}-[01]?\d-[0-3]?\d', e):
                    n = re.findall(r'0?(\d{1,4})[-+]0?(\d{1,4})', e)[0]
                    x.append((float(rf'{n[0]}.{n[1].zfill(4)}'), part, 'e'))
            if re.search(r'^(SD|HD|FHD|\d{3,4}P|標清|超清|高清|正片|中字|TC)', e, re.IGNORECASE):
                x.append(('RES', part, 'r'))
            if len(x) == 0:
                x.append((e, part, 'n'))
            result = result + x
        return sorted(result, key=lambda x: x[2])

    def _extract_playlist(self, webpage):
        result = []
        source = (re.findall(r'an? class="(?:source|route).+?>\s*(.+?)\s*<\/s?p?an?>', webpage)
                  or re.findall(r'playlist-block__title">\s*(.+?)\s*</h2>', webpage))
        for idx, html in enumerate(re.findall(
                r'class="(?:eps episodes|playlist|episodes)-(?:route|grid).+>\s*([\s\S]+?)\s*<\/div>',
                webpage)):
            links = []
            for url, ep in re.findall(r'href="([^"]+)">\s*(.*?)\s*<\/a', html):
                links.append({'ep': ep, 'url': f'{self._BASE_URL}{url}'})
            result.append({'source': clean_html(source[idx]), 'links': links})
        return result

    def _extract_video_src(self, playlist, video_id, given_episode, given_url):
        """
        Extract other sources of the video

        :param playlist: [{'source': xxx, 'links': [{'ep': xxx, 'url': url}, {...}, ...]}, {...}, ...]
        :type playlist: list of dicts.
        :param video_id: video id
        :type video_id: str.
        :param given_episode: episode of the given webpage
        :type given_episode: str.
        :param given_url: the given URL
        :type given_url: str.
        :returns:  list of dicts -- links [{'ep': xxx, 'url': url, 'source': xxx}, {...}, ...]
        """
        episode = self._parse_episode(given_episode)
        urls = [given_url]
        result = []
        for pl in playlist:
            for item in pl['links']:
                item['source'] = pl['source']
                if item not in result:
                    ep_item = self._parse_episode(item['ep'])
                    for e in episode:
                        if e in ep_item and item['url'] not in urls:
                            result.append(item)
                            urls.append(item['url'])
                            if len(ep_item) > 1:
                                for ep in [ep for ep in ep_item if ep not in episode]:
                                    episode.append(ep)
        return result

    def _extract_player_data(self, webpage, video_id):
        return self._search_json(r'javascript">var player_\w+?=', webpage,
                                 'player_data', video_id, default=None)

    def _extract_formats(self, player_data, video_id, source_name, episode):
        """
        :return: generator -- formats
        """
        def parser_urls(media_url):
            parse_type = ['u', 'u'] if media_url[-5:] == '.html' else {
                'JD-': ['dp', 'd'],
                'JSY': ['i', 'i'],
            }[media_url[:3]]
            verify = '&verify=1' if parse_type[0] == 'i' else ''
            # https://player.gimy.bot/{dp or u}/parse.php?url={media_url}&_t=1778152814109
            # https://player.gimy.bot/i/parse.php?verify=1&url={media_url}&_t=1778152814109
            return [
                f'https://player.gimy.bot/{parse_type[0]}/parse.php?url={media_url}{verify}',
                f'https://play.gimy01.tv/{parse_type[1]}/parse.php?url={media_url}{verify}',
            ]

        if not player_data:
            return None
        format_id = player_data.get('from')
        if vdo_url := traverse_obj(player_data, ('url', {str_or_none})):
            origin = self._BASE_URL
            parser_url = None
            if not url_or_none(vdo_url) or vdo_url[-5:] == '.html':
                for url in parser_urls(vdo_url):
                    player_data = self._download_json(
                        f'{url}&_t={int(time.time() * 1000)}',
                        video_id, note='Downloading player data')
                    if player_data.get('code') == 200:
                        if vdo_url := traverse_obj(player_data, ('url', {url_or_none})):
                            origin = 'https://player.gimy.bot'
                            parser_url = url
                            break
            if url_or_none(vdo_url):
                skipped_sources = ['.html', 'vodcnd04.oag7h.com', '.ppqrrs.com', '.ryplay4.com',
                                   '.wsyzym3u8.com', '.yaaabc.com', '.zuidazym3u8.com', '.bxgbnet.com',
                                   '.daayee.com', '.hhiklm.com', 'v6.qrssuv.com', '.qsstvw.com']
                if all(x not in vdo_url for x in skipped_sources):
                    headers = {
                        'origin': origin,
                        'referer': f'{origin}/',
                    }
                    for f in self._extract_m3u8_formats_and_subtitles(
                            vdo_url, video_id, errnote=None, fatal=False, headers=headers)[0]:
                        if parser_url:
                            f['url'] = parser_url
                            f['downloader_options'] = {
                                'preprocessor': {
                                    'key': self.ie_key(),
                                    'args': {},
                                },
                            }
                        f['format_id'] = (format_id or self._html_search_regex(
                            r'https?://[^/]*?\.?([\w]{4,}|[^\.]+)[^\.]*\.\w+/',
                            vdo_url, 'format_id', default='id')).lower()
                        f['ext'] = f['ext'] or 'mp4'
                        f['format_note'] = f'{episode} ({source_name})'
                        f.setdefault('http_headers', {})['origin'] = origin
                        yield f

    _nd_required = False
    if nd_available:
        _browser = None
        _loop = loop()

        def _nd_get_config(self, url):
            browser_executable_path = (
                self._configuration_arg('browser_path', casesense=True, default=[None])[0]
                # backwards-compat
                or self._configuration_arg(
                    'browser_path', [None], ie_key='gimy', casesense=True)[0]
            )
            return nd.core.config.Config(
                headless=False,
                browser_executable_path=browser_executable_path,
                browser_args=['--window-size=480,560', f'--app={url}', '--incognito'],
            )

        def _is_complete(html):
            return (('<title>404 not found</title>' in html
                     or ' class="video-' in html)
                    and '</html>' in html)

        def _nd_download_webpage(
                self, url, video_id, note=None, tries=3, timeout=0,
                is_complete=_is_complete):
            async def download_webpage(url):
                if not self._browser or self._browser.stopped:
                    self.to_screen('Launching browser due to Cloudflare anti-bot challenge. '
                                   'Do not close the browser window.')
                    try:
                        self._browser = await start(config=self._nd_get_config(url))
                    except Exception as e:
                        raise ExtractorError(f'Failed to start browser: {e}') from e

                if note is None:
                    self.report_download_webpage(video_id)
                elif note is not False:
                    if video_id is None:
                        self.to_screen(str(note))
                    else:
                        self.to_screen(f'{video_id}: {note}')

                try_count = 0
                while True:
                    try:
                        webpage = await self._browser.get(f'{url}?_={time.time()}')
                        content = await webpage.get_content()
                        loop_count = 0
                        while loop_count < (1 + (not try_count)) * 5:
                            if error := self._search_regex(
                                    r'var loadTimeDataRaw\s*=\s*{.+"errorCode"\s*:\s*"(.+?)",',
                                    content, 'http_error', default=None):
                                raise ExtractorError('Unable to download webpage: '
                                                     f'Connection Error: {error}', expected=True)
                            elif not is_complete(content):
                                await self._browser.wait(3)
                                content = await webpage.get_content()
                                loop_count += 1
                            else:
                                break
                        if '(function(){window._cf_chl_opt' in content:
                            raise TransportError('Security verification failed')
                        else:
                            self._is_404_not_found(content)
                            return content.replace('&nbsp;', ' ')
                    except TransportError as e:
                        try_count += 1
                        if try_count >= tries:
                            raise ExtractorError(e)
                        self._sleep(timeout, video_id)
                        self.to_screen(f'{video_id}: {e}. Retrying ({try_count}/{tries - 1})...')
            return self._loop.run_until_complete(download_webpage(url))

    def _download_webpage(
            self, url, video_id, note=None, errnote=None,
            fatal=True, tries=1, timeout=0, *args, **kwargs):
        try:
            if self._nd_required:
                webpage = self._nd_download_webpage(
                    url, video_id, note, tries, timeout)
            else:
                webpage = super()._download_webpage(
                    url, video_id, note, errnote, fatal,
                    tries, timeout, *args, **kwargs)
            self._is_404_not_found(webpage)
            return webpage.replace('&nbsp;', ' ')
        except ExtractorError as e:
            if not isinstance(e.cause, HTTPError) or e.cause.status != 403:
                raise
            res = e.cause.response
            if (res.get_header('cf-mitigated') == 'challenge'
                    and res.get_header('server') == 'cloudflare'):
                if nd_available:
                    self._nd_required = True
                    return self._nd_download_webpage(url, video_id, note, 3, timeout)
                else:
                    raise ExtractorError(
                        'Got HTTP Error 403 caused by Cloudflare anti-bot challenge; '
                        'try again after install Chrome and nodriver '
                        '(https://github.com/UltrafunkAmsterdam/nodriver); '
                        'to install nodriver, use "pip install nodriver==0.47.0"', expected=True)

    def _is_404_not_found(self, webpage):
        if '<title>404 not found</title>' in webpage:
            raise ExtractorError(
                'Unable to download webpage: HTTP Error 404: Not Found '
                '(caused by <HTTPError 404: Not Found>)', expected=True)

    def _match_url(self, url):
        base_url, video_id = self._match_valid_url(url).group('base_url', 'id')
        if base_url:
            self._BASE_URL = base_url
        return video_id

    def _real_extract(self, url):
        self._downloader.params['nocheckcertificate'] = True
        video_id = self._match_url(url)
        if not url_or_none(url):
            url = f'{self._BASE_URL}/eps/{video_id}.html'
        webpage = self._download_webpage(url, video_id)

        parsed_url = urllib.parse.urlsplit(url)
        episode = self._html_search_regex(
            rf'\D" href="{parsed_url.path}">\s*(.*?)\s*<', webpage, 'episode', default='')
        is_series = len(re.findall(r'href=".+"[^>]*>.*[上下]一集.*</a>', webpage)) > 0
        player_data = self._extract_player_data(webpage, video_id)
        if title := traverse_obj(player_data, ('vod_data', 'vod_name', {str_or_none})):
            pass
        else:
            page_title = (self._html_extract_title(webpage)
                          or self._og_search_title(webpage)
                          or self._html_search_meta('twitter:title', webpage))
            parsed_title = page_title.split(' - ')
            title = re.sub(rf'\s*{episode}$', '', parsed_title[0])
        # description
        json_ld = re.findall(r'application/ld\+json">(.*)</script>', webpage)
        if description := self._html_search_regex(
                r'劇情介紹[\s\S]+?<div>([\s\S]+?)</div>', webpage, 'description',
                default=traverse_obj(json_ld, (..., {str}, {json.loads}, 'description',
                                               {str_or_none}), get_all=False)):
            pass
        elif description := self._html_search_meta(
                ['description', 'og:description', 'twitter:description'],
                webpage, default=None):
            description = description.split('線上看,')[-1].strip()
        if categories := self._html_search_regex(
                r'類別[：:]<.+?">\s*(.+?)\s*</a', webpage, 'categories', default=None):
            categories = categories.split(',')
        thumbnail = self._og_search_thumbnail(webpage)
        cast, formats = [], []
        # cast
        if vod_actor := traverse_obj(
                player_data, ('vod_data', 'vod_actor', {str_or_none})):
            cast = vod_actor.split(',')
        # video source of current webpage
        current_src = self._html_search_regex(
            r'[\s-]active".+switch.+?>\s*(.+)\s*</a', webpage, 'VideoSrc', default='0')
        if f := list(self._extract_formats(player_data, video_id, current_src, episode)):
            formats = f
        # video sources
        for src in self._extract_video_src(self._extract_playlist(webpage),
                                           video_id, episode, url):
            if src['url'] != url:
                page = self._download_webpage(
                    src['url'], video_id, f'Extracting "{src["source"]}": {src["url"]}')
                if player_data_alt := self._extract_player_data(page, video_id):
                    if f := list(self._extract_formats(player_data_alt, video_id,
                                                       src['source'], src['ep'])):
                        formats += f

        return {k: v for k, v in {
            'id': video_id,
            'title': title,
            'description': description,
            'episode': episode if is_series else None,
            'thumbnail': url_or_none(sanitize_url(thumbnail)),
            'cast': cast,
            'categories': categories,
            'formats': formats,
        }.items() if v}


class GimyVodIE(GimyIE):
    IE_NAME = 'gimy:vod'
    _VALID_URL = r'(gimy:|(?P<base_url>https?://gimy[^/]*\.[^/]+)/v[^/]*/)(?P<id>\d+)(?:/|\.html)?$'
    _TESTS = [{
        'url': 'https://gimytv.ai/vod/10889.html',
        'info_dict': {
            'id': '10889',
            'title': '工作細胞',
            'description': r're:清水茜「はたらく細胞」の',
            'thumbnail': r're:https?://',
            'categories': ['動漫'],
            'cast': ['花澤香菜', '前野智昭', '井上喜久子', '小野大輔', '長繩麻理亞'],
            'view_count': int,
        },
        'playlist_count': 14,
    }, {
        'url': 'https://gimy01.tv/vod/10889.html',
        'info_dict': {
            'id': '10889',
            'title': '工作細胞',
            'description': r're:清水茜「はたらく細胞」の',
            'thumbnail': r're:https?://',
            'categories': ['動漫'],
            'cast': ['花澤香菜', '前野智昭', '井上喜久子', '小野大輔', '長繩麻理亞'],
            'location': '日本',
            'release_year': 2018,
            'view_count': int,
        },
        'playlist_count': 14,
    }, {
        'url': 'gimy:278636',
        'info_dict': {
            'id': '278636',
            'title': '九龍城寨之圍城',
            'description': r're:上世紀八十年代，惡名昭著的“三不管”地帶九龍城寨中黑幫盤踞，',
            'thumbnail': r're:https?://',
            'categories': ['動作片'],
            'cast': 'count:13',
            'location': '中國香港,中國大陸',
            'release_year': 2024,
            'view_count': int,
        },
        'playlist_mincount': 1,
    }]

    def _real_extract(self, url):
        def create_playlist(lists, regex):
            ep = []
            result = []
            for i, playlist in enumerate(lists):
                for item in playlist['links'][:]:
                    ep_item = self._parse_episode(item['ep'])
                    entry = (item['url'],
                             (float(ep_item[0][0]) if ep_item[0][2] == 'd' or ep_item[0][2] == 'e'
                              else int(''.join(re.findall(regex, item['url'])[0]))))
                    for e in ep_item:
                        if e not in ep:
                            ep.append(e)
                            if entry not in result:
                                result.append(entry)
                        else:
                            lists[i]['links'].remove(item)
            return result

        self._downloader.params['nocheckcertificate'] = True
        video_id = self._match_url(url)
        if not url_or_none(url):
            url = f'{self._BASE_URL}/vod/{video_id}.html'
        webpage = self._download_webpage(url, video_id)
        if self._browser:
            self._browser.stop()

        json_ld = re.findall(r'application/ld\+json">(.*)</script>', webpage)
        title = (traverse_obj(
            json_ld, (..., {str}, {json.loads}, 'name', {str_or_none}), get_all=False)
            or self._html_search_regex(
                r'<h1>(.+)</h1>', webpage, 'title',
                default=self._html_extract_title(webpage).split('線上看')[0]))
        if description := self._html_search_regex(
                r'劇情介紹[\s\S]+?<div>([\s\S]+?)</div>', webpage, 'description',
                default=traverse_obj(json_ld, (..., {str}, {json.loads}, 'description',
                                               {str_or_none}), get_all=False)):
            pass
        elif description := self._html_search_meta(
                ['description', 'og:description', 'twitter:description'],
                webpage, default=None):
            description = description.split('線上看,')[-1].strip()
        cast, categories, release_year = [], [], None
        if actors := self._html_search_regex(r'(?:主演：|演員:)(.+?)</(?:p|div)>',
                                             webpage, 'actors', default=None):
            cast = actors.split('、')
        if categories := self._html_search_regex(
                r'類別：</span><b>\s*(.+)\s*</.+?>', webpage, 'categories', default=None):
            categories, release_year = categories.split(' · ')
            categories = categories.split(',')
        elif categories := re.findall(
                r'breadcrumb__sep[\s\S]+?">\s*(.+?)\s*</a>\s*<span', webpage):
            categories = categories[-1].split(',')
        location = self._html_search_regex(
            r'地區：</.+?>\s*(.*?)\s*</.+?>', webpage, 'location', default=None)
        thumbnail = self._html_search_meta(['og:image', 'twitter:image'],
                                           webpage, 'thumbnail URL', default=None)
        view_count = int_or_none(self._html_search_regex(
            r'人氣[:：]</.+?>\s*(\d*?)\s*</.+?>', webpage, 'view_count', default=None))

        entries = []
        if playlist := create_playlist(self._extract_playlist(webpage),
                                       r'-(\d+)-(\d+)\.html'):
            entries = [self.url_result(x[0])
                       for x in sorted(playlist, key=lambda x: x[1])]

        info_dict = {k: v for k, v in {
            'id': str(video_id),
            'title': title,
            'description': description,
            'thumbnail': url_or_none(sanitize_url(thumbnail)),
            'categories': categories,
            'cast': cast,
            'location': location,
            'release_year': int_or_none(release_year),
            'view_count': view_count,
        }.items() if v}

        return self.playlist_result(entries, **info_dict)


class GimySearchIE(SearchInfoExtractor, GimyIE):
    IE_NAME = 'gimy:search'
    IE_DESC = 'gimy Search'
    _SEARCH_KEY = 'gimysearch'
    _TESTS = [{
        'url': 'gimysearchall:王座',
        'info_dict': {
            'id': '王座',
            'title': '王座',
        },
        'playlist_mincount': 25,
    }]

    def _search_results(self, query):
        self._downloader.params['nocheckcertificate'] = True
        keywords = urllib.parse.quote_plus(query)
        for page_number in itertools.count(1):
            webpage = self._download_webpage(
                f'{self._BASE_URL}/search/{keywords}----------{page_number}---.html',
                query, note=f'Downloading result page {page_number}')
            search_results = re.findall(
                r'a class="poster" href="(.+)"', webpage)
            if not search_results:
                return
            for result in search_results:
                yield self.url_result(self._BASE_URL + result, GimyVodIE)
            if f'href="/search/{keywords}----------{page_number + 1}---.html' not in webpage:
                if self._browser:
                    self._browser.stop()
                return
