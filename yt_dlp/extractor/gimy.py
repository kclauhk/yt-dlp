import asyncio
import itertools
import re
import urllib.parse

try:
    import nodriver
    from nodriver import cdp, loop, start
    nodriver_available = True
except ImportError:
    nodriver_available = False

from .common import InfoExtractor, SearchInfoExtractor
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
    _VALID_URL = r'(gimy:|(?P<base_url>https?://gimy\w+\.\w+)/ep/)(?P<id>\d+-\d+-\d+)(?:/|\.html)?$'
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
            'release_year': 2013,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'gimy:423662-7-3',
        'info_dict': {
            'id': '423662-7-3',
            'ext': 'mp4',
            'title': '臥底洪小姐',
            'description': r're:《臥底洪小姐》票房女王回歸！由朴信惠、高庚杓主演的',
            'episode': '第3集',
            'thumbnail': r're:https?://',
            'categories': ['韓劇'],
            'cast': 'count:4',
            'release_year': 2026,
        },
        'params': {'skip_download': True},
    }]

    _BASE_URL = 'https://gimymax.com'

    def _match_url(self, url):
        base_url, video_id = self._match_valid_url(url).group('base_url', 'id')
        if base_url:
            self._BASE_URL = base_url
        return video_id

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
                x.append((re.findall(r'(?:19|20)?\d*(\d{2}[01]\d[0-3]\d)',
                                     e.replace('-', ''))[0][-6:],
                          '' if f'-{part}' in e or f'-0{part}' in e else part, 'd'))
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

    def _extract_playlists(self, webpage):
        result = []
        for source, html in re.findall(
                r'class="gico [\s\S]+?">\s*([^(?:</)]+?)\s*</(?:span>|div>\s*</li>)\s*<ul [^>]+ id="con(?:mobi)?_playlist_\d+">\s*([\s\S]+?)\s*</ul',
                webpage):
            links = []
            for url, ep in re.findall(r'href="([^"]+)">\s*(.*?)\s*<\/a', html):
                links.append({'ep': ep, 'url': f'{self._BASE_URL}{url}'})
            result.append({'source': clean_html(source), 'links': links})
        return result

    def _extract_other_src(self, playlists, video_id, given_episode, given_source):
        """
        Extract other sources of the video

        :param playlists: [{'source': xxx, 'links': [{'ep': xxx, 'url': url}, {...}, ...]}, {...}, ...]
        :type playlists: list of dicts.
        :param video_id: video id
        :type video_id: str.
        :param given_episode: episode of the given webpage
        :type given_episode: str.
        :param given_source:  name of the video source of the given webpage
        :type given_source: str.
        :returns:  list of dicts -- links [{'ep': xxx, 'url': url, 'source': xxx}, {...}, ...]
        """
        episode = self._parse_episode(given_episode)
        urls = [f'/ep/{video_id}.html']
        result = []
        for playlist in playlists:
            for item in playlist['links']:
                item['source'] = playlist['source']
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

    def _extract_formats(self, media_url, video_id, episode, source):
        """
        :return: generator -- formats
        """
        if url_or_none(media_url):
            skipped_sources = ['.html', '.ppqrrs.com', '.yaaabc.com', '.wsyzym3u8.com', '.qsstvw.com',
                               '.hhiklm.com', '.zuidazym3u8.com', 'v6.daayee.com', 'v6.qrssuv.com']
            if all(x not in media_url for x in skipped_sources):
                for f in self._extract_m3u8_formats_and_subtitles(
                        media_url, video_id, errnote=None, fatal=False)[0]:
                    f['format_id'] = self._html_search_regex(
                        r'https?://[^/]*?\.?([\w]{4,}|[^\.]+)[^\.]*\.\w+/',
                        f['url'], 'format_id', default='id')
                    f['ext'] = f.get('ext') or 'mp4'
                    f['format_note'] = f'{episode} ({source})'
                    yield f

    if nodriver_available:
        def _get_nodriver_config(self):
            browser_executable_path = (
                self._configuration_arg('browser_path', casesense=True, default=[None])[0]
                # backwards-compat
                or self._configuration_arg('browser_path', [None], ie_key='gimy', casesense=True)[0]
            )
            return nodriver.core.config.Config(
                headless=False,
                browser_executable_path=browser_executable_path,
                browser_args=['--window-size=480,560', '--app=http://localhost'],
            )

        _browser = None
        _loop = loop()

        def _download_webpage(self, url, video_id, note=None):
            async def launch_browser(url):
                while not self._browser or self._browser.stopped:
                    self.to_screen('Launching browser due to Cloudflare anti-bot challenge. '
                                   'Do not close the browser window. '
                                   'You may required to answer the challenge.')
                    try:
                        self._browser = await start(config=self._get_nodriver_config())
                    except Exception as e:
                        raise ExtractorError(f'Failed to start browser: {e}') from e
                    await self._browser.connection.send(cdp.storage.clear_cookies())
                self.to_screen(f'{video_id}: Extracting URL: {url}')
                webpage = await self._browser.get(url)
                content = await webpage.get_content()
                i = 0
                while (i < 20
                       and ('</body></html>' not in content
                            or ('<title>404 not found</title>' not in content
                                and ' class="details-' not in content))):
                    await asyncio.sleep(3)
                    content = await webpage.get_content()
                    i += 1
                return content.replace('&nbsp;', ' ')

            if note is None:
                self.report_download_webpage(video_id)
            elif note is not False:
                if video_id is None:
                    self.to_screen(str(note))
                else:
                    self.to_screen(f'{video_id}: {note}')
            return self._loop.run_until_complete(launch_browser(url))

    def _real_extract(self, url):
        self._downloader.params['nocheckcertificate'] = True
        video_id = self._match_url(url)
        vid = video_id.split('-')[0]
        url = f'{self._BASE_URL}/ep/{video_id}.html'
        webpage = self._download_webpage(url, video_id, note=False)
        if '<title>404 not found</title>' in webpage:
            raise ExtractorError(
                'Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)

        if page_title := re.search(
                rf'data-id="{vid}" data-name="([^"]+)" data-playname="([^"]+)"', webpage):
            title = page_title.group(1)
            episode = page_title.group(2)
        elif page_title := self._html_search_regex(
                r'h1 [^>]+>\s*<a [^>]+>\s*([\s\S]+?)\s*</a', webpage,
                'title', default=None):
            page_title = page_title.split(' ')
            title = page_title[0]
            episode = page_title[-1]
        else:
            title = self._html_extract_title(webpage).split('線上看')[0]
            episode = self._html_search_regex(
                r'<li>.+class="active" href=".+">\s*(.+?)\s*</a></li>', webpage,
                'episode', default='')
        is_series = len(re.findall(r'href="" [^>]+>[上下]一集</a>', webpage)) < 2
        if description := self._html_search_regex(
                r'span class="detail-intro[^>]+>\s*([\s\S]*?)\s*</sp', webpage,
                'description', default=None):
            pass
        elif description := self._html_search_meta('description', webpage, default=None):
            description = description.split('線上看，')[-1].strip()
        if categories := self._html_search_regex(
                r'類別：</span>\s*<[^>]+>\s*(.+?)\s*</a', webpage, 'categories',
                default=None):
            categories = categories.split(',')
        release_year = int_or_none(self._html_search_regex(
            r'年份：</span>\s*<sp[^>]+>\s*(\d*?)\s*</sp', webpage, 'release_year',
            default=None))
        thumbnail = self._og_search_thumbnail(webpage)
        cast = []
        if player_data := self._search_json(
                r'javascript">var player_data=', webpage, 'player_data',
                video_id, default=None):
            if vod_actor := traverse_obj(
                    player_data, ('vod_data', 'vod_actor', {str_or_none})):
                cast = vod_actor.split(',')

        formats = []
        # video source of current webpage
        current_src = self._html_search_regex(
            r'播放線路:\s*(.+?)\s*</span', webpage, 'video_src', default='0')
        if media_url := traverse_obj(player_data, ('url', {url_or_none})):
            if f := list(self._extract_formats(media_url, video_id, episode, current_src)):
                formats = f
        # other video sources
        for src in self._extract_other_src(self._extract_playlists(webpage),
                                           video_id, episode, current_src):
            if src['url'] != url:
                page = self._download_webpage(src['url'], video_id, note=False)
                if player_data := self._search_json(
                        r'javascript">var player_data=', page, '', video_id, default=None):
                    if media_url := traverse_obj(player_data, ('url', {url_or_none})):
                        if f := list(self._extract_formats(media_url, video_id,
                                                           src['ep'], src['source'])):
                            formats += f

        return {k: v for k, v in {
            'id': video_id,
            'title': title,
            'description': description,
            'episode': episode if is_series else None,
            'thumbnail': url_or_none(sanitize_url(thumbnail)),
            'cast': cast,
            'categories': categories,
            'release_year': release_year,
            'formats': formats,
        }.items() if v}


class GimyVodIE(GimyIE):
    IE_NAME = 'gimy:vod'
    _VALID_URL = r'(gimy:|(?P<base_url>https?://gimy\w+\.\w+)/v(?:od)?/)(?P<id>\d+)(?:/|\.html)?$'
    _TESTS = [{
        'url': 'https://gimytv.ai/v/10889.html',
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
        'url': 'gimy:424008',
        'info_dict': {
            'id': '424008',
            'title': '尋秦記電影版',
            'description': r're:來自21世紀的項少龍（古天樂 飾）曾意外穿越，',
            'thumbnail': r're:https?://',
            'categories': ['動作片'],
            'cast': 'count:22',
            'location': '香港',
            'release_year': 2026,
            'view_count': int,
        },
        'playlist_count': 2,
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
        webpage = self._download_webpage(
            f'{self._BASE_URL}/vod/{video_id}.html', video_id, note=False)
        self._browser.stop()
        if '<title>404 not found</title>' in webpage:
            raise ExtractorError(
                'Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)

        title = self._html_search_regex(
            r'h1 class="text-overflow">\s*([\s\S]+?)\s*<font style="font-size:0.6em";></font></h1>',
            webpage, 'title', default=self._html_extract_title(webpage).split('線上看')[0])
        if description := self._html_search_regex(
                r'span class="details-content-all">\s*([\s\S]*?)\s*</sp', webpage,
                'description', default=None):
            pass
        elif description := self._html_search_meta(
                ['description', 'og:description', 'twitter:description'],
                webpage, default=None):
            description = description.split('線上看。')[-1].strip()
        cast = []
        if vod_actor := self._search_regex(r'主演：\s*([^\n]+?)\s*</li>',
                                           webpage, 'actors', default=None):
            cast = re.findall(r'target="_blank">\s*([^(?!</a)]+?)\s*</a>', vod_actor)
        if categories := self._html_search_regex(
                r'類別：<a [^>]*>(.+?)</a>', webpage, 'categories', default=None):
            categories = categories.split(',')
        location = self._html_search_regex(
            r'國家/地區：</span>\s*(.*?)\s*</li>', webpage, 'location', default=None)
        release_year = int_or_none(self._html_search_regex(
            r'年代：</span>\s*(\d*?)\s*</li>', webpage, 'release_year', default=None))
        thumbnail = self._html_search_meta(['og:image', 'twitter:image'],
                                           webpage, 'thumbnail URL')
        view_count = int_or_none(self._html_search_regex(
            r'人氣：</span>\s*(\d*?)\s*</li>', webpage, 'view_count', default=None))

        entries = []
        if playlist := create_playlist(self._extract_playlists(webpage),
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
            'release_year': release_year,
            'view_count': view_count,
        }.items() if v}

        return self.playlist_result(entries, **info_dict)


class GimySearchIE(SearchInfoExtractor, GimyIE):
    IE_NAME = 'gimy:search'
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
        self._downloader.params['nocheckcertificate'] = True
        keywords = urllib.parse.quote_plus(query)
        for page_number in itertools.count(1):
            webpage = self._download_webpage(
                f'{self._BASE_URL}/search/-------------.html?wd={keywords}', query,
                note=f'Downloading result page {page_number}')
            if '<title>404 not found</title>' in webpage:
                raise ExtractorError(
                    'Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
            search_results = re.findall(
                r'col-xs-12"><a href="([^"]+)" title="[^"]+">.+?<\/a>', webpage)
            if not search_results:
                return
            for result in search_results:
                yield self.url_result(self._BASE_URL + result, GimyVodIE)
            if f'href="/search/{keywords}----------{page_number + 1}---.html' not in webpage:
                return
