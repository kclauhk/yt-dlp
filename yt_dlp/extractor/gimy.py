import itertools
import json
import re
import time
import urllib.parse

from .common import InfoExtractor, SearchInfoExtractor
from .commonbrowser import BrowserIE
from ..utils import (
    ExtractorError,
    UnsupportedError,
    clean_html,
    int_or_none,
    join_nonempty,
    sanitize_url,
    str_or_none,
    traverse_obj,
    update_url,
    url_basename,
    url_or_none,
)


class GimyIE(BrowserIE, InfoExtractor):
    IE_NAME = 'gimy:ep'
    _VALID_URL = r'''(?x)
                (
                    gimy(?P<domain>(?:plus|01|tv|ai|tube)?):|
                    (?P<base_url>https?://gimy[^/]*\.[^/]+)/
                        (?P<path>[epw][^/]*)/
                )
                (?P<id>\d+-\d+-\d+)
                (?:/|\.html)?$
                '''
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
        'url': 'https://gimyplus.com/ep/4891-1-2.html',
        'info_dict': {
            'id': '4891-1-2',
            'ext': 'mp4',
            'title': '天空之城',
            'description': r're:古老帝國拉比達是一座漂浮在空中的巨大的機器島，',
            'episode': '第2集',
            'thumbnail': r're:https?://',
            'categories': ['動漫'],
            'cast': ['田中真弓', '橫澤啓子', '初井言榮', '寺田農', '常田富士男'],
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://gimytube.com/watch/455427-3-1.html',
        'info_dict': {
            'id': '455427-3-1',
            'ext': 'mp4',
            'title': '玩具總動員5',
            'description': r're:本部續作中，胡迪、巴斯光年、翠斯等“元老級”玩具將',
            'thumbnail': r're:https?://',
            'categories': ['動畫電影'],
            'cast': 'count:9',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://gimyai.tw/play/444339-2-11.html',
        'info_dict': {
            'id': '444339-2-11',
            'ext': 'mp4',
            'title': 'COURT!',
            'description': r're:《COURT!》由3個不同單元故事組成，描繪基於不同觀點角度、',
            'episode': '第11集',
            'thumbnail': r're:https?://',
            'categories': ['港劇'],
            'cast': 'count:20',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'gimyplus:256836-2-5',
        'info_dict': {
            'id': '256836-2-5',
            'ext': 'mp4',
            'title': '歡樂頌5',
            'description': r're:22樓五個姑娘彼此相伴的日子還在繼續，',
            'episode': '第5集',
            'thumbnail': r're:https?://',
            'categories': ['陸劇'],
            'cast': 'count:9',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'gimyai:4891-2-1',
        'info_dict': {
            'id': '4891-2-1',
            'ext': 'mp4',
            'title': '天空之城',
            'description': r're:古老帝國拉比達是一座漂浮在空中的巨大的機器島，',
            'episode': '第01集',
            'thumbnail': r're:https?://',
            'categories': ['動漫'],
            'cast': ['田中真弓', '橫澤啓子', '初井言榮', '寺田農', '常田富士男'],
        },
        'params': {'skip_download': True},
    }]

    _BASE_URL_MAP = {
        'plus': ('https://gimyplus.com', 'ep'),
        'tube': ('https://gimytube.com', 'watch'),
        'tv': ('https://gimytv.ai', 'ep'),
        '01': ('https://gimy01.tv', 'eps'),
        'ai': ('https://gimyai.tw', 'play'),
    }
    _BASE_URL = 'https://gimyai.tw'

    def _match_url(self, url):
        domain, base_url, path, video_id = self._match_valid_url(url).group(
            'domain', 'base_url', 'path', 'id')
        if base_url:
            self._BASE_URL = base_url
        elif domain:
            self._BASE_URL, path = self._BASE_URL_MAP[domain]
        else:
            path = traverse_obj(self._BASE_URL_MAP, (
                lambda _, v: v[0] == self._BASE_URL, 1), get_all=False)
        return video_id, path

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
        source = (re.findall(r'playlist-block__title"[^>]*>\s*(.+?)\s*</h2>', webpage)
                  or re.findall(r'class="(?:source|route)[^s].+?>\s*(.+?)\s*<\/', webpage))
        for idx, html in enumerate(re.findall(
                r'class="(?:eps episodes|playlist|episodes)-(?:route|grid).+>\s*([\s\S]+?)\s*<\/div>',
                webpage)):
            links = []
            for url, ep in re.findall(r'href="([^"]+)">\s*(.*?)\s*<\/a', html):
                links.append({'ep': ep, 'url': f'{self._BASE_URL}{url}'})
            result.append({'source': clean_html(source[idx]), 'links': links})
        return result

    def _extract_video_src(self, playlists, video_id, given_episode, given_url):
        """
        Extract other sources of the video

        :param playlists: [{'source': xxx, 'links': [{'ep': xxx, 'url': url}, {...}, ...]}, {...}, ...]
        :type playlists: list of dicts.
        :param video_id: video id
        :type video_id: str.
        :param given_episode: episode of the given webpage
        :type given_episode: str.
        :param given_url: the given URL
        :type given_url: str.
        :returns:  list of dicts -- links [{'ep': xxx, 'url': url, 'source': xxx}, {...}, ...]
        """
        def find_link(episode, playlist):
            for link in playlist['links']:
                link['source'] = playlist['source']
                if link not in result:
                    ep_link = self._parse_episode(link['ep'])
                    for e in episode:
                        if e in ep_link and link['url'] not in urls:
                            result.append(link)
                            urls.append(link['url'])
                            return ep_link
            return []

        episode = self._parse_episode(given_episode)
        urls = [given_url]
        result = []
        for i, playlist in enumerate(playlists):
            ep_link = find_link(episode, playlist)
            if len(ep_link) > 1 and ep_link != episode:
                for ep in [e for e in ep_link if e not in episode]:
                    episode.append(ep)
                    for pl in playlists[:i]:
                        find_link([ep], pl)
        return result

    def _extract_player_data(self, webpage, video_id):
        return self._search_json(r'javascript">var player_\w+?=', webpage,
                                 'player_data', video_id, default=None)

    def _extract_formats(self, player_data, video_id, source_name, episode):
        """
        :return: generator -- formats
        """
        def get_parser_url(url):
            types = {
                # key: ['path', 'path', 'filename', 'additional query parameters', 'v.gimy.bot api']
                'url': ['u', 'u', 'parse.php', '&jctype=etcjc', 'jx'],
                'JD-': ['dp', 'd', 'parse.php', '', 'jd'],    # 4K/2K畫質線路
                'JSY': ['i', 'i', 'parse.php', '&verify=1', ''],
                'NSY': ['n', 'n', 'parse.php', '&jctype=NSYS', ''],  # 藍光線路
                'qsv': ['n', 'n', 'parse.php', '', 'qs'],  # 藍光線路
            }
            if url[:3] in types:
                parse_type = types[url[:3]]
            else:
                parse_type = types['url']
            # https://play.gimy.bot/[jx|jd|qs]/api.php?url={url}
            # https://player.gimy.bot/u/parse.php?url={url}&jctype=etcjc&next=//gimyplus.com/ep/454135-3-2.html
            # https://player.gimy.bot/d/parse.php?url={url}&_t=1781844164145
            # https://player.gimy.bot/i/parse.php?verify=1&url={url}&_t=1778152814109
            # https://player.gimy.bot/n/parse.php?url={url}&jctype=NSYS&next=gimyplus.com/ep/256836-12-4.html
            # eg:
            # https://play.gimy.bot/jx/api.php?url=https%3A%2F%2Fwww.iqiyi.com%2Fv_vqtro5otuc.html
            # https://play.gimy.bot/jd/api.php?url=JD-e97db5acb55f07ca1b59a221bae4a7b70
            # https://play.gimy.bot/qs/api.php?url=qsvip-vDEsBQ2XchQheJUkvEGD4L07GSIf3gaU-WK6I05Bi...
            return [
                f'https://play.gimy.bot/{parse_type[4]}/api.php?url={url}',
                f'https://v.gimy.bot/{parse_type[4]}/api.php?url={url}',
                f'https://player.gimy.bot/{parse_type[0]}/{parse_type[2]}?url={url}{parse_type[3]}',
                f'https://play.gimy01.tv/{parse_type[1]}/{parse_type[2]}?url={url}{parse_type[3]}',
            ]

        if not player_data:
            return {}
        format_id = player_data.get('from').strip('m3u8')
        if video_url := traverse_obj(player_data, ('url', {str_or_none})):
            origin = self._BASE_URL
            parser_url = None
            if not url_or_none(video_url) or '.m3u8' not in video_url:
                media_url = None
                for url in get_parser_url(video_url):
                    if player_data := self._download_json(
                            f'{url}&_t={int(time.time() * 1000)}', video_id,
                            note='Downloading player data', fatal=False):
                        if media_url := (None if player_data.get('code') != 200
                                         else traverse_obj(player_data, ('url', {url_or_none}))):
                            if media_url != video_url:
                                origin = f'https://{urllib.parse.urlparse(url).netloc}'
                                parser_url = url
                                break
                video_url = media_url
            if url_or_none(video_url):
                skipped_sources = ['.html', 'vodcnd04.oag7h.com', '.ryplay4.com',
                                   '.yaaabc.com', '.bxgbnet.com', '.daayee.com',
                                   '.hhiklm.com', 'v6.qrssuv.com', '.qsstvw.com']
                if all(x not in video_url for x in skipped_sources):
                    if 'm3u8' in video_url or player_data.get('type') == 'hls':
                        formats, _ = self._extract_m3u8_formats_and_subtitles(
                            video_url, video_id, errnote=None, fatal=False, headers={
                                'origin': origin,
                                'referer': f'{origin}/',
                            })
                    else:
                        formats = [{
                            'url': video_url,
                            'ext': 'mp4',
                        }]
                    for f in formats:
                        if parser_url:
                            f['url'] = parser_url
                            '''
                            # not used, for demonstrating 'preprocessor' usage only
                            f['downloader_options'] = {
                                'preprocessor': {
                                    'key': 'Gimy',
                                    'args': {},
                                },
                            }
                            '''
                        f['format_id'] = (format_id or self._html_search_regex(
                            r'https?://[^/]*?\.?([\w]{4,}|[^\.]+)[^\.]*\.\w+/',
                            video_url, 'format_id', default='id')).lower()
                        f['ext'] = f['ext'] or 'mp4'
                        f['format_note'] = join_nonempty(episode, source_name, delim=' @ ')
                        f.setdefault('http_headers', {})['origin'] = origin
                        f['http_headers']['referer'] = f'{origin}/'
                        yield f

    def _is_complete(webpage):
        return ('劇迷' in webpage and '</html>' in webpage
                and ('role="contentinfo"' in webpage
                     or '<title>404 not found</title>' in webpage))

    _browser_config = {
        'headless': False,
        'arguments': {
            '--window-size': '480,560',
        },
        'evaluate': _is_complete,
    }

    def _is_not_found(self, webpage):
        if ('<title>404 not found</title>' in webpage
                or '<title>跳轉提示</title>' in webpage):
            raise ExtractorError(
                'Unable to download webpage: HTTP Error 404: Not Found '
                '(caused by <HTTPError 404: Not Found>)', expected=True)

    def _before_download(self, info, subtitle, test):
        """ Process info dict before download """
        video_id = info.get('id')
        if '/parse.php?' in info.get('url') or '/api.php?' in info.get('url'):
            try:
                player_data = self._download_json(
                    f"{info['url']}&_t={int(time.time() * 1000)}",
                    video_id, note='Obtaining manifest URL')
                self.write_debug(join_nonempty(
                    video_id, f"Parse result: {player_data.get('msg')}", delim=': '))
                if player_data.get('code') == 200:
                    if url := traverse_obj(player_data, ('url', {url_or_none})):
                        if 'www.bilibili.com/' in info['url']:
                            info['http_headers']['origin'] = 'https://www.bilibili.com'
                            info['http_headers']['referer'] = 'https://www.bilibili.com/'
                        info['url'] = url
                        return info
                # cannot obtain manifest URL
                raise ExtractorError(player_data.get('msg'), expected=True)
            except BaseException as err:
                msg = join_nonempty(
                    video_id, 'Unable to obtain manifest URL', err, delim=': ')
                if test:
                    self.to_screen(msg)
                else:
                    raise ExtractorError(f'[{self.IE_NAME}] {msg}') from err
        return info

    def _real_extract(self, url):
        self._downloader.params['nocheckcertificate'] = True
        video_id, path = self._match_url(url)
        if not url_or_none(url):
            url = f'{self._BASE_URL}/{path}/{video_id}.html'
        if webpage := self._download_webpage(url, video_id):
            self._is_not_found(webpage)

        basename = url_basename(url)
        episode = self._html_search_regex(
            rf'\D" href="/.+/{basename}">\s*(.*?)\s*<', webpage, 'episode', default='')
        is_series = len(re.findall(r'href=".+"[^>]*>.*[上下]一集.*</a>', webpage)) > 0
        player_data = self._extract_player_data(webpage, video_id)
        if title := traverse_obj(player_data, ('vod_data', 'vod_name', {str_or_none})):
            pass
        elif page_title := (self._html_extract_title(webpage, default=None)
                            or self._og_search_title(webpage, default=None)
                            or self._html_search_meta('twitter:title', webpage, default=None)):
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
        thumbnail = self._html_search_meta(
            ['og:image', 'twitter:image'], webpage, 'thumbnail URL', default=None)
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
            if url_basename(src['url']) != basename:
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
    _VALID_URL = r'''(?x)
                (
                    gimy(?P<domain>(?:plus|01|tv|ai|tube)?):|
                    (?P<base_url>https?://gimy[^/]*\.[^/]+)/
                        (?P<path>[vdt][^/]*)/
                )
                (?P<id>\d+)
                (?:/|\.html)?$
                '''
    _TESTS = [{
        'url': 'https://gimytv.ai/vod/10889.html',
        'info_dict': {
            'id': '10889',
            'title': '工作細胞',
            'description': r're:清水茜「はたらく細胞」の',
            'thumbnail': r're:https?://',
            'categories': ['動漫'],
            'cast': ['花澤香菜', '前野智昭', '井上喜久子', '小野大輔', '長繩麻理亞'],
            'release_year': 2018,
            'view_count': int,
        },
        'playlist_count': 14,
    }, {
        'url': 'https://gimyai.tw/detail/10889.html',
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
        'url': 'gimyplus:480330',
        'info_dict': {
            'id': '480330',
            'title': '殺手媽咪',
            'description': r're:《殺手媽咪》改編自同名人氣網路漫畫，由孔曉振、鄭準元、李相二主演，',
            'thumbnail': r're:https?://',
            'categories': ['韓劇'],
            'cast': 'count:4',
            'release_year': 2026,
            'view_count': int,
        },
        'playlist_mincount': 1,
    }, {
        'url': 'gimy01:278636',
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

    _BASE_URL_MAP = {
        'plus': ('https://gimyplus.com', 'vod'),
        'tube': ('https://gimytube.com', 'title'),
        'tv': ('https://gimytv.ai', 'vod'),
        '01': ('https://gimy01.tv', 'vod'),
        'ai': ('https://gimyai.tw', 'detail'),
    }

    def _real_extract(self, url):
        def create_playlist(lists, regex):
            ep = []
            result = []
            for i, playlist in enumerate(lists):
                for link in playlist['links'][:]:
                    ep_link = self._parse_episode(link['ep'])
                    entry = (link['url'],
                             (float(ep_link[0][0]) if ep_link[0][2] == 'd' or ep_link[0][2] == 'e'
                              else int(''.join(re.findall(regex, link['url'])[0]))))
                    for e in ep_link:
                        if e not in ep:
                            ep.append(e)
                            if entry not in result:
                                result.append(entry)
                        else:
                            lists[i]['links'].remove(link)
            return result

        self._downloader.params['nocheckcertificate'] = True
        video_id, path = self._match_url(url)
        if not url_or_none(url):
            url = f'{self._BASE_URL}/{path}/{video_id}.html'
        if webpage := self._download_webpage(url, video_id):
            self._is_not_found(webpage)

        json_ld = re.findall(r'application/ld\+json">(.*)</script>', webpage)
        title = (traverse_obj(
            json_ld, (..., {str}, {json.loads}, 'name', {str_or_none}), get_all=False)
            or self._html_search_regex(
                r'<h1>(.+)</h1>', webpage, 'title',
                default=self._html_extract_title(webpage).split('線上看')[0]))
        if description := self._html_search_regex(
                r'劇情介紹[\s\S]+?<div[^>]*>([\s\S]+?)</div>', webpage, 'description',
                default=traverse_obj(json_ld, (..., {str}, {json.loads}, 'description',
                                               {str_or_none}), get_all=False)):
            pass
        elif description := self._html_search_meta(
                ['description', 'og:description', 'twitter:description'],
                webpage, default=None):
            description = description.split('線上看,')[-1].strip()
        thumbnail = self._html_search_meta(
            ['og:image', 'twitter:image'], webpage, 'thumbnail URL', default=None)
        cast, categories, release_year = [], [], None
        if actors := self._html_search_regex(r'(?:主演：|演員:)(.+?)</(?:p|div)>',
                                             webpage, 'actors', default=None):
            cast = actors.split('、')
        if categories := self._html_search_regex(
                r'類別[:：]</span><[^>]+>\s*(.+)\s*</.+?>', webpage, 'categories', default=None):
            categories, release_year = categories.split(' · ')
            categories = categories.split(',')
        elif categories := re.findall(
                r'class=".*sep[\s\S]+?">\s*(.+?)\s*</a>\s*<span', webpage):
            categories = categories[-1].split(',')
        if not release_year:
            release_year = self._html_search_regex(
                r'年份[:：]</[^>]+>\s*(.+?)\s*<.+?>', webpage, 'categories', default=None)
        location = self._html_search_regex(
            r'地區[:：]</.+?>\s*(.*?)\s*</.+?>', webpage, 'location', default=None)
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
                r'class="(?:search-item__title|poster)".* href="(.+)"', webpage)
            if not search_results:
                break
            for result in search_results:
                yield self.url_result(self._BASE_URL + result, GimyVodIE)
            if f'/{keywords}----------{page_number + 1}---.html"' not in webpage:
                break
        self._close_browser()


class GimyBotIE(GimyIE):
    IE_NAME = 'gimy:bot'
    _VALID_URL = r'gimybot:(?P<url>.+)'

    def _real_extract(self, url):
        self._downloader.params['nocheckcertificate'] = True
        url = self._match_valid_url(url).group('url')

        supported_sites = ['.bilibili.com', '.iqiyi.com', '.mgtv.com',
                           '.qq.com', '.youku.com']
        if not url_or_none(url) or all(x not in url for x in supported_sites):
            raise UnsupportedError(url)
        else:
            url_parsed = urllib.parse.urlparse(url)
            if 'bilibili.com' in url_parsed.hostname:
                url = update_url(url, query=('theme=moive'))
        video_id = (url_basename(url_parsed.path)
                    or re.sub(r'(?:/|\.\w{,4})$', '', url_parsed.path).split('/')[-1])
        source = url_parsed.hostname.split('.')[-2]
        formats = list(self._extract_formats({
            'from': source,
            'url': url,
        }, video_id, '', ''))

        return {
            'id': video_id,
            'title': f'{source.capitalize()} video',
            'formats': formats,
        }
