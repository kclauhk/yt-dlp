import datetime
import itertools
import re
import urllib.parse

from .common import InfoExtractor, SearchInfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    sanitize_url,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class GimyIE(InfoExtractor):
    IE_NAME = 'gimy:ep'
    _VALID_URL = r'(gimy:|https?://gimytv\.ai/ep/)(?P<id>\d+)-(?P<source_id>\d+)-(?P<episode_id>\d+)(?:/|\.html)?$'
    _TESTS = [{
        'url': 'https://gimytv.ai/ep/141543-7-100.html',
        'info_dict': {
            'id': '141543-7-100',
            'ext': 'mp4',
            'title': '我獨自生活',
            'description': r're:《我獨自生活》是由韓國MBC電視臺新年播放的特輯',
            'episode': '第20260123期',
            'thumbnail': r're:https?://',
            'categories': ['綜藝'],
            'cast': ['盧洪哲', 'Defconn', '金泰元', '金光奎'],
            'release_year': 2013,
        },
        'params': {'skip_download': True},
    }]
    _BASE_URL = 'https://gimytv.ai'

    def _parse_episode(self, string):
        episode = string.replace('上', '-1').replace('下', '-2')
        episode = re.sub(r'完結$', '', episode)
        part = (re.findall(r'[-_]0?(\d+)[集）]?$', episode)
                or re.findall(r'預告', episode)
                or ['']
                )[0]
        result = []
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
            result = result + x
        return sorted(result, key=lambda x: x[2])

    def _extract_playlists(self, webpage):
        result = []
        for source, html in re.findall(
                r'class="gico .+0(?:px)?;">\s*([^(?:</)]+?)\s*</(?:span>|div> </li>)\s*<ul [^>]+ id="con(?:mobi)?_playlist_\d+">\s*([\s\S]+?)\s*</ul',
                webpage):
            links = []
            for url, ep in re.findall(r'href="([^"]+)">\s*([^(?:</)]+)\s*<\/a', html):
                links.append({'ep': ep, 'url': url})
            result.append({'source': source, 'links': links})
        return result

    def _extract_other_src(self, playlists, given_episode, given_source):
        """
        Extract other sources of the video

        :param playlists: [{'source': xxx, 'links': [{'ep': xxx, 'url': url}, {...}, ...]}, {...}, ...]
        :type playlists: list of dicts.
        :param given_episode: episode of the given webpage
        :type given_episode: str.
        :param given_source:  name of the video source of the given webpage
        :type given_source: str.
        :returns:  list of dicts -- links [{'ep': xxx, 'url': url, 'source': xxx}, {...}, ...]
        """
        episode = self._parse_episode(given_episode)
        result = []
        for playlist in [x for x in playlists if x['source'] != given_source]:
            for link in playlist['links']:
                ep_link = self._parse_episode(link['ep'])
                for e in episode:
                    z, d = [], []
                    link['source'] = playlist['source']
                    if link not in result and e in ep_link:
                        z.append(link)
                    if (e[2] == 'd'
                        and abs((datetime.datetime.strptime(e[0], '%y%m%d')
                                 - datetime.datetime.strptime(
                                    ([x for x in ep_link
                                      if x[1] == e[1] and x[2] == 'd']
                                     or [('500101', '', '')]
                                     )[0][0], '%y%m%d')
                                 ).days) == 1):
                        d.append(link)
                    if len(z) == 1:
                        result.append(z[0])
                    elif len(z) == 0 and len(d) == 1:
                        result.append(d[0])
                    if (len(z) == 1 or len(d) == 1) and len(ep_link) > 1:
                        for e in ep_link:
                            if e not in episode:
                                episode.append(e)
        return result

    def _extract_formats(self, media_url, video_id, episode, source):
        """
        :return: generator -- formats
        """
        if url_or_none(media_url):
            skipped_sources = ['.html', '.qsstvw.com', '.hhiklm.com', '.zuidazym3u8.com']
            if all(x not in media_url for x in skipped_sources):
                for f in self._extract_m3u8_formats_and_subtitles(
                        media_url, video_id, errnote=None, fatal=False)[0]:
                    f['format_id'] = self._html_search_regex(
                        r'https?://[^/]*?\.?([\w]{4,}|[^\.]+)[^\.]*\.\w+/',
                        f['url'], 'format_id', default='id')
                    f['ext'] = f.get('ext') or 'mp4'
                    f['format_note'] = f'{episode} ({source})'
                    yield f

    def _real_extract(self, url):
        self._downloader.params['nocheckcertificate'] = True
        vid, sid, eid = self._match_valid_url(url).group('id', 'source_id', 'episode_id')
        video_id = f'{vid}-{sid}-{eid}'
        url = f'{self._BASE_URL}/ep/{video_id}.html'
        webpage = (self._download_webpage(url, video_id)).replace('&nbsp;', ' ')
        if '<title>404 not found</title>' in webpage:
            raise ExtractorError(
                'Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)

        if page_title := re.search(
                rf'1data-id="{vid}" data-name="([^"]+)" data-playname="([^"]+)"', webpage):
            title = page_title.group(1)
            episode = page_title.group(2)
        elif page_title := self._html_search_regex(
                r'1h1 [^>]+>\s*<a [^>]+>\s*(.+?)\s*</a', webpage,
                'title', default=None):
            page_title = page_title.split(' ')
            title = page_title[0]
            episode = page_title[-1]
        else:
            title = self._html_extract_title(webpage).split('線上看')[0]
            episode = self._html_search_regex(
                r'<li>.+class="active" href=".+">(.+)</a></li>', webpage,
                'episode', default='')
        is_series = len(re.findall(r'href="" [^>]+>[上下]一集</a>', webpage)) < 2
        description = self._html_search_regex(
            r'span class="detail-intro[^>]+>(.+?)</sp', webpage, 'description',
            default=None)
        if categories := self._html_search_regex(
                r'類別：</span>\s*<[^>]+>\s*(.+?)\s*</a', webpage, 'categories',
                default=[]):
            categories = categories.split(',')
        release_year = int_or_none(self._html_search_regex(
            r'年份：</span>\s*<sp[^>]+>\s*(.+?)\s*</sp', webpage, 'release_year',
            default=None))
        thumbnail = self._html_search_meta('og:image', webpage, 'thumbnail')
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
            r'播放線路:\s*(.+)\s*</span', webpage, 'video_src', default='0')
        if media_url := traverse_obj(player_data, ('url', {url_or_none})):
            if f := list(self._extract_formats(media_url, video_id, episode, current_src)):
                formats = f
        # other video sources
        for src in self._extract_other_src(self._extract_playlists(webpage),
                                           episode, current_src):
            url = f'{self._BASE_URL}{src["url"]}'
            self.to_screen(f'Extracting URL: {url}')
            if player_data := self._search_json(
                    r'javascript">var player_data=', self._download_webpage(url, video_id),
                    '', video_id, default=None):
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


class GimyDetailIE(GimyIE):
    IE_NAME = 'gimy:v'
    _VALID_URL = r'(gimy:|https?://gimytv\.ai/v/)(?P<id>\d+)(?:/|\.html)?$'
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
        'playlist_mincount': 14,
    }]

    def _real_extract(self, url):
        def create_playlist(lists, regex):
            result = []
            for i, x in enumerate(lists):
                for y in x['links']:
                    epsd = self._parse_episode(y['ep'])
                    entry = (y['url'],
                             float(epsd[0][0]) if epsd[0][2] == 'd' or epsd[0][2] == 'e'
                                else int(''.join(re.findall(regex, y['url'])[0])))
                    if entry not in result:
                        result.append(entry)
                    for j, a in enumerate(lists):
                        if j > i:
                            for e in epsd:
                                z, d = [], []
                                for b in a['links']:
                                    ep = self._parse_episode(b['ep'])
                                    if e in ep:
                                        z.append(b)
                                    if (e[2] == 'd'
                                        and abs((datetime.datetime.strptime(e[0], '%y%m%d')
                                                 - datetime.datetime.strptime(
                                                    ([x for x in ep
                                                      if x[1] == e[1] and x[2] == 'd']
                                                     or [('500101', '', '')]
                                                     )[0][0], '%y%m%d')
                                                 ).days) == 1):
                                        d.append(b)
                                if len(z) == 1:
                                    lists[j]['links'].remove(z[0])
                                elif len(z) == 0 and len(d) == 1:
                                    lists[j]['links'].remove(d[0])
            return result

        video_id = self._match_id(url)
        webpage = self._download_webpage(
            f'{self._BASE_URL}/v/{video_id}.html', video_id).replace('&nbsp;', ' ')
        if '<title>404 not found</title>' in webpage:
            raise ExtractorError(
                'Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)

        title = self._html_search_regex(
            r'h1 class="text-overflow">\s*(.+)\s*<font style="font-size:0.6em";></font></h1>',
            webpage, 'title', default=self._html_extract_title(webpage).split('線上看')[0])
        description = self._html_search_regex(
            r'span class="details-content-all">\s*(.*)\s*</sp', webpage,
            'description', default=None)
        cast = []
        if vod_actor := self._search_regex(r'主演：\s*([^\n]+)\s*</li>',
                                           webpage, 'actors', default=None):
            cast = re.findall(r'target="_blank">\s*([^(?!</a)]+)\s*</a>', vod_actor)
        if categories := self._html_search_regex(
                r'類別：<a [^>]*>(.+)</a>', webpage, 'categories', default=None):
            categories = categories.split(',')
        location = self._html_search_regex(
            r'國家/地區：</span>\s*(.*)\s*</li>', webpage, 'location', default=None)
        release_year = int_or_none(self._html_search_regex(
            r'年代：</span>\s*(\d*)\s*</li>', webpage, 'release_year', default=None))
        thumbnail = self._html_search_meta(['og:image', 'twitter:image'], webpage, 'thumbnail')
        view_count = int_or_none(self._html_search_regex(
            r'人氣：</span>\s*(\d*)\s*</li>', webpage, 'view_count', default=None))

        entries = []
        if playlist := create_playlist(self._extract_playlists(webpage),
                                       r'-(\d+)-(\d+)\.html'):
            entries = [self.url_result(f'{self._BASE_URL}{x[0]}')
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
