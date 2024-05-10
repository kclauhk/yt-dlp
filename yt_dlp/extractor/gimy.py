import re
import math
import urllib.parse

from datetime import datetime
from .common import InfoExtractor
from ..postprocessor import FFmpegPostProcessor
from ..utils import (
    float_or_none,
    get_element_by_id,
    int_or_none,
    str_or_none,
    traverse_obj,
    url_or_none,
    ExtractorError,
    PlaylistEntries,
)


class GimyIE(InfoExtractor):
    _VALID_URL = r'(gimy:|https?://gimy\.cc/video/)(?P<id>\d+)-(?P<source_id>\d+)-(?P<episode_id>\d+)'
    _TESTS = [{
        'url': 'https://gimy.cc/video/225461-5-4.html',
        'info_dict': {
            'id': '225461-5-4',
            'title': '嗨！營業中第二季 - 第4',
            'description': 'md5:cbb271b7e281a4f78404be17d24cb9a4',
            'episode': '第4',
            'thumbnail': r're:^https?://.*',
            'release_year': 2023,
            'upload_date': '20240118',
            'catagory': ['綜藝'],
            'region': '台灣',
            'ext': 'mp4',
        },
        'params': {'skip_download': True}
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
            if re.search(r'^(SD|HD|FHD|\d{3,4}P|標清|超清|高清|正片|中字|TC)', x, re.IGNORECASE):
                z.append(('RES', part, 'r'))
            if len(z) == 0:
                z.append((x, part, 'n'))
            ep = ep + z
        return sorted(ep, key=lambda x: x[2])

    def _extract_links(self, webpage):
        source = {}
        for playlist, src in re.findall(r'id="tabslist"><a href="#(playlist\d)" data-toggle="tab">([\s\S]+?)</a></li>', webpage):
            source[playlist] = src
        links = []
        for playlist in source.keys():
            html = get_element_by_id(playlist, webpage)
            z = []
            for x in re.findall(r'<li.*><a.* href="([^"]+)".*<span[^>]*>(.+?)</span></a></li>', html):
                z.append(x)
            links.append({'source': source[playlist], 'links': z})
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
            _CLOUD_MAP = {
                '假日雲': '1',
                '優酷雲': '2',
                '小牛雲': '3',
                '心空雲': '4',
                '暴風雲': '5',
                '步兵雲': '6',
                '無限雲': '7',
                '索尼雲': '8',
                '閃電雲': '9',
                '飛快雲': '10',
            }
            f = self._extract_m3u8_formats_and_subtitles(video_url, video_id, errnote=None, fatal=False)[0]
            if f:
                f[0]['format_id'] = _CLOUD_MAP.get(media_source) or media_source
                f[0]['ext'] = 'mp4' if not f[0]['ext'] else f[0]['ext']
                f[0]['format_note'] = f'{episode_label} ({media_source})'
                if f[0]['url'].count('.haiwaikan.com') > 0:
                    ffmpeg = FFmpegPostProcessor()
                    if ffmpeg.probe_available:
                        if data := ffmpeg.get_metadata_object(f[0]['url']):
                            f[0].update(traverse_obj(data.get('format'), {
                                'filesize': ('size', {int_or_none}),
                                'duration': ('duration', {float_or_none}, {lambda x: round(float(x), 2)}),
                                'tbr': ('bit_rate', {float_or_none}, {lambda x: float_or_none(x, 1000)}),
                            }))
                            for stream in traverse_obj(data, 'streams', expected_type=list):
                                if stream.get('codec_type') == 'video':
                                    [frames, duration] = [int_or_none(x) for x in (
                                        stream['avg_frame_rate'].split('/') if stream.get('avg_frame_rate') else [None, None])]
                                    f[0].update(**traverse_obj(stream, {
                                        'width': ('width', {int_or_none}),
                                        'height': ('height', {int_or_none}),
                                        'vcodec': ('codec_name', {str_or_none}, {lambda x: x.replace('h264', 'avc1')}),
                                        'vbr': ('bit_rate', {float_or_none}, {lambda x: float_or_none(x, 1000)}),
                                    }), **{
                                        'fps': round(frames / duration, 1) if frames and duration else None,
                                    })
                                elif stream.get('codec_type') == 'audio':
                                    f[0].update(traverse_obj(stream, {
                                        'audio_channels': ('channels', {int_or_none}),
                                        'acodec': ('codec_name', {str_or_none}),
                                        'asr': ('sample_rate', {int_or_none}),
                                        'abr': ('bit_rate', {float_or_none}, {lambda x: float_or_none(x, 1000)}),
                                    }))
                return {'formats': [f[0]]}
            else:
                return {}
        else:
            return {}

    def _real_extract(self, url):
        vid, source_id, episode_id = self._match_valid_url(url).group('id', 'source_id', 'episode_id')
        video_id = str(vid) + '-' + str(source_id) + '-' + str(episode_id)
        url = 'https://gimy.cc/video/' + vid + '-' + source_id + '-' + episode_id + '.html'
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
        catagory = self._html_search_regex(r'類型：</span><[^>]+>(.+)</a>', webpage, 'catagory', default=None)
        region = self._html_search_regex(r'地區：</span><[^>]+>(.+)</a>', webpage, 'region', default=None)
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
                    if (e[2] == 'd' and abs((datetime.strptime(e[0], '%y%m%d')
                                             - datetime.strptime(([x for x in ep if x[1] == e[1] and x[2] == 'd']
                                                                  or [('500101', '', '')]
                                                                  )[0][0], '%y%m%d')
                                             ).days) == 1):
                        d.append(y)
                if len(z) == 1:
                    other_src.append(z[0])
                elif len(z) == 0 and len(d) == 1:
                    other_src.append(d[0])
        for x in other_src:
            self.to_screen('Extracting URL: ' 'https://gimy.cc' + x[0])
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
            'thumbnail': thumbnail,
            'release_year': release_year,
            'upload_date': upload_date.replace('-', ''),
            'catagory': [catagory],
            'region': region,
        }
        if ('上一集' in webpage or '下一集' in webpage):
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
    _VALID_URL = r'(gimy:|https?://gimy\.cc/detail/)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://gimy.cc/detail/240550.html',
        'info_dict': {
            'id': '240550',
            'title': '蠟筆小新·新次元！超能力大決戰',
            'description': 'md5:d19200a4d2a38be94ad59d021f81218c',
            'thumbnail': r're:^https?://.*',
            'release_year': 2024,
            'catagory': ['動漫'],
            'region': '日本',
        },
        'playlist_count': 2,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = (self._download_webpage('https://gimy.cc/detail/' + video_id + '.html', video_id)).replace('&nbsp;', ' ')
        if 'aks-404-page' in webpage:
            raise ExtractorError('Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
        # extract video info
        title = (self._html_search_regex(r'<h1 class="title">(.+)<!--<span class="score', webpage, 'title', default=None)
                 or self._html_extract_title(webpage).split(' - ')[0])
        desc_meta = self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage, 'description')
        description = (desc_meta[:(desc_meta.index('劇情講述'))] + '劇情講述'
                       + self._html_search_regex(r'<p class="col-pd">\s*([\s\S]+)\s*</p>[\s\S]+劇情簡介', webpage, 'description', default=''))
        catagory = self._html_search_regex(r'分類：</span><[^>]+>(.+)</a>', webpage, 'catagory', default=None)
        region = self._html_search_regex(r'地區：</span><[^>]+>(.+)</a>', webpage, 'region', default=None)
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
                                if (e[2] == 'd' and abs((datetime.strptime(e[0], '%y%m%d')
                                                         - datetime.strptime(([x for x in ep if x[1] == e[1] and x[2] == 'd']
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
            'thumbnail': thumbnail,
            'release_year': release_year,
            'catagory': [catagory],
            'region': region,
        }

        return self.playlist_result(entries, **info_dict)


class GimySearchIE(GimyIE):
    IE_NAME = GimyIE.IE_NAME + ':search'
    _VALID_URL = r'(gimysearch(?P<prefix>|[1-9][0-9]*|all):|(?P<http>http)s?://gimy\.cc/search\.html\?wd=)(?P<query>[\s\S]+)'
    _TESTS = [{
        'url': 'https://gimy.cc/search.html?wd=tokyo+mer',
        'info_dict': {
            'id': 'tokyo mer',
            'title': 'tokyo mer搜索結果',
            'description': 'tokyo mer搜索結果',
        },
        'playlist_count': 2,
    }, {
        'url': 'gimysearchall:blackpink',
        'info_dict': {
            'id': 'blackpink',
            'title': 'blackpink搜索結果',
            'description': 'blackpink搜索結果',
        },
        'playlist_count': 3,
    }]

    def _real_extract(self, url):
        prefix, http, query = self._match_valid_url(url).group('prefix', 'http', 'query')
        query = (urllib.parse.unquote_plus(query).split('&'))[0]
        webpage = self._download_webpage('https://gimy.cc/search.html?wd=' + urllib.parse.unquote_plus(query), query, tries=2).replace('&nbsp;', ' ')
        if 'aks-404-page' in webpage:
            raise ExtractorError('Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
        # extract video info
        description = self._html_search_meta('description', webpage, 'description')
        total_pages = int(self._html_search_regex(r'<span class="num">\d+/(\d+)</span></li>', webpage, 'total_pages', default='1'))

        # generate playlist
        playlist, entries = [], []
        if 'aks-404-page' not in webpage:
            for x in re.findall(r'<h3 class="title"><a href="([^"]+)">.*</a></h3>', webpage):
                playlist.append(x)

            items_per_page = len(playlist)
            match_total = total_pages * items_per_page
            result_end = min(match_total if prefix == 'all' or http else (int_or_none(prefix) or 1), self.get_param('playlistend') or match_total)
            if total_pages > 1:
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
                    webpage = self._download_webpage('https://gimy.cc/search/page/' + str(i) + '/wd/' + urllib.parse.unquote_plus(query) + '.html', query,
                                                     'Fetching result ' + str((i - 1) * items_per_page + 1) + '-' + str(min(match_total, i * items_per_page)),
                                                     tries=2).replace('&nbsp;', ' ')
                    if 'aks-404-page' in webpage:
                        raise ExtractorError('Unable to download webpage: HTTP Error 404: Not Found (caused by <HTTPError 404: Not Found>)', expected=True)
                    for x in re.findall(r'<h3 class="title"><a href="([^"]+)">.*</a></h3>', webpage):
                        playlist.append(x)

            entries = [self.url_result('https://gimy.cc' + x, GimyDetailIE)
                       for x in playlist[:result_end]]

        info_dict = {
            'id': str(query),
            'title': description,
            'description': description,
        }

        return self.playlist_result(entries, **info_dict)
