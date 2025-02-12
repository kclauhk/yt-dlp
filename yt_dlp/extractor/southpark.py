import codecs
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    float_or_none,
    int_or_none,
    join_nonempty,
    merge_dicts,
    parse_duration,
    str_or_none,
    traverse_obj,
    unified_strdate,
    url_or_none,
)


class SouthParkIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?southpark(?:\.cc|studios)\.com/((?:video-)?clips|(?:full-)?episodes|collections)/(?P<id>.+?)(\?|#|$)'
    _TESTS = [{
        'url': 'https://southpark.cc.com/video-clips/d7wr06/south-park-you-all-agreed-to-counseling',
        'info_dict': {
            'id': '31929ad5-8269-11eb-8774-70df2f866ace',
            'ext': 'mp4',
            'title': 'You All Agreed to Counseling',
            'description': 'Kenny, Cartman, Stan, and Kyle visit Mr. Mackey and ask for his help getting Mrs. Nelson to come back. Mr. Mackey reveals the only way to get things back to normal is to get the teachers vaccinated.',
            'thumbnail': 'https://images.paramount.tech/uri/mgid:arc:imageassetref:shared.southpark.global:c65bada8-b837-4c1a-82e4-fba7935c7c42',
            'timestamp': 1615352400,
            'upload_date': '20210310',
            'release_date': '20210310',
            'duration': 134.552,
            'tags': 'count:24',
            'season': 'Season 24',
            'season_number': 24,
            'episode': 'Episode 2',
            'episode_number': 2,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://southpark.cc.com/collections/7758/fan-favorites/1',
        'only_matching': True,
    }, {
        'url': 'https://www.southparkstudios.com/episodes/h4o269/south-park-stunning-and-brave-season-19-ep-1',
        'only_matching': True,
    }]

    def _entries(self, video_data, video_id):
        chapters, formats, subtitles = None, [], {}
        if service_url := codecs.decode(video_data.get('videoServiceUrl', ''), 'unicode-escape'):
            mica_json = self._download_json(service_url.split('?')[0] + '?clientPlatform=desktop', video_id)
            if source := traverse_obj(mica_json, ('stitchedstream', 'source', {url_or_none})):
                if determine_ext(source) == 'm3u8':
                    formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                        source, video_id, 'mp4', fatal=False, m3u8_id='hls')
                else:
                    formats.append({'url': source})
                chapter_data = traverse_obj(mica_json, ('content', 0, 'chapters'), default=[])
                if len(chapter_data) > 1:
                    chapters = traverse_obj(chapter_data, (..., {
                        'start_time': ({lambda v: parse_duration(v['contentoffset'])}),
                        'end_time': ({lambda v: parse_duration(v['contentoffset']) + parse_duration(v['duration'])}),
                    }))
        return merge_dicts(traverse_obj(video_data, {
            'id': ('id', {str}),
            'title': ('title', {str}),
            'description': (('fullDescription', 'description'), {str_or_none}),
            'thumbnail': ('images', 0, 'url',
                          {lambda v: url_or_none(codecs.decode(v, 'unicode-escape')).split('?')[0]}),
            'timestamp': ('publishDate', 'timestamp', {int_or_none}),
            'upload_date': ('publishDate', 'dateString', {unified_strdate}),
            'release_date': ('airDate', 'dateString', {unified_strdate}),
            'season_number': ('seasonNumber', {int_or_none}),
            'episode_number': ('episodeAiringOrder', {int_or_none}),
            'tags': ('keywords', {lambda v: re.split(r',\s*', v)}),
            'genres': ('genres'),
            'duration': ('duration', 'milliseconds', {lambda v: float_or_none(v, 1000)}),
        }, get_all=False), {
            'id': video_id,
            'chapters': chapters,
            'formats': formats,
            'subtitles': subtitles,
        })

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        page_data = self._search_json(r'window\.__DATA__\s*=\s*', webpage, 'Page Data', video_id,
                                      end_pattern=r';\n')
        video_data = traverse_obj(
            page_data, ('children', ..., 'handleTVEAuthRedirection',
                        (('videoPlaylist', 'videos'), ('videoDetail', {lambda v: [v]}))),
            default=[], get_all=False)

        if len(video_data) == 1 and video_data[0] is not None:
            return self._entries(video_data[0], video_id)
        elif len(video_data) > 1:
            return self.playlist_result(
                (self._entries(video, video_id) for video in video_data),
                **traverse_obj(page_data, ('children', ..., 'handleTVEAuthRedirection', 'videoPlaylist', {
                    'id': ('id', {str}),
                    'title': ('seoInformation', 'title', {str}),
                    'description': ('seoInformation', 'description', {str_or_none}),
                }), get_all=False))
        raise ExtractorError('Unable to extract video data')


class SouthParkEsIE(SouthParkIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'southpark.cc.com:español'
    _VALID_URL = r'https?://(?:www\.)?(?P<url>southpark\.cc\.com/es/episodios/(?P<id>.+?)(\?|#|$))'
    _LANG = 'es'
    _TESTS = [{
        'url': 'http://southpark.cc.com/es/episodios/s01e01-cartman-consigue-una-sonda-anal#source=351c1323-0b96-402d-a8b9-40d01b2e9bde&position=1&sort=!airdate',
        'info_dict': {
            'title': 'Cartman Consigue Una Sonda Anal',
            'description': 'Cartman Consigue Una Sonda Anal',
        },
        'playlist_count': 4,
        'skip': 'Geo-restricted',
    }]


class SouthParkDeIE(SouthParkIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'southpark.de'
    _VALID_URL = r'https?://(?:www\.)?(?P<url>southpark\.de/(?:(en/(videoclip|collections|episodes|video-clips))|(videoclip|collections|folgen))/(?P<id>(?P<unique_id>.+?)/.+?)(?:\?|#|$))'
    _GEO_COUNTRIES = ['DE', 'AT', 'CH', 'LI']
    _TESTS = [{
        'url': 'https://www.southpark.de/videoclip/rsribv/south-park-rueckzug-zum-gummibonbon-wald',
        'only_matching': True,
    }, {
        'url': 'https://www.southpark.de/folgen/jiru42/south-park-verkabelung-staffel-23-ep-9',
        'only_matching': True,
    }, {
        'url': 'https://www.southpark.de/collections/zzno5a/south-park-good-eats/7q26gp',
        'only_matching': True,
    }, {
        # clip
        'url': 'https://www.southpark.de/en/video-clips/ct46op/south-park-tooth-fairy-cartman',
        'info_dict': {
            'id': 'e99d45ea-ed00-11e0-aca6-0026b9414f30',
            'ext': 'mp4',
            'title': 'Tooth Fairy Cartman',
            'description': 'md5:11656c34e92f2ab9491e01de43200baa',
            'thumbnail': 'https://images.paramount.tech/uri/mgid:arc:imageassetref:shared.southpark.gsa.en:5e4fe2b3-ed07-49ec-9c10-320cb97b7d9a',
            'timestamp': 954990360,
            'upload_date': '20000406',
            'release_date': '20000406',
            'duration': 93.26,
            'tags': 'count:16',
            'season': 'Season 4',
            'season_number': 4,
            'episode': 'Episode 1',
            'episode_number': 1,
        },
    }, {
        # episode
        'url': 'https://www.southpark.de/en/episodes/yy0vjs/south-park-the-pandemic-special-season-24-ep-1',
        'info_dict': {
            'id': '230a4f02-f583-11ea-834d-70df2f866ace',
            'ext': 'mp4',
            'title': 'The Pandemic Special',
            'description': 'md5:ae0d875eff169dcbed16b21531857ac1',
            'thumbnail': 'https://images.paramount.tech/uri/mgid:arc:imageassetref:shared.southpark.gsa.en:31f62b92-5658-4a86-9d47-86b21b4a2abb',
            'timestamp': 1601932260,
            'upload_date': '20201005',
            'release_date': '20201005',
            'duration': 2724.0,
            'genres': ['Comedy'],
            'season': 'Season 24',
            'season_number': 24,
            'episode': 'Episode 1',
            'episode_number': 1,
        },
    }, {
        # clip
        'url': 'https://www.southpark.de/videoclip/ct46op/south-park-zahnfee-cartman',
        'info_dict': {
            'id': 'e99d45ea-ed00-11e0-aca6-0026b9414f30',
            'ext': 'mp4',
            'title': 'Zahnfee Cartman',
            'description': 'md5:b917eec991d388811d911fd1377671ac',
            'thumbnail': 'https://images.paramount.tech/uri/mgid:arc:imageassetref:shared.southpark.gsa.de:5e4fe2b3-ed07-49ec-9c10-320cb97b7d9a',
            'timestamp': 954990360,
            'upload_date': '20000406',
            'release_date': '20000406',
            'duration': 93.26,
            'tags': 'count:16',
            'season': 'Season 4',
            'season_number': 4,
            'episode': 'Episode 1',
            'episode_number': 1,
        },
    }, {
        # episode
        'url': 'https://www.southpark.de/folgen/scexjh/south-park-ein-fettwanst-in-aethiopien-staffel-1-ep-8',
        'info_dict': {
            'id': '5fe739ee-ecfd-11e0-aca6-0026b9414f30',
            'ext': 'mp4',
            'title': 'Ein Fettwanst in Äthiopien',
            'description': 'md5:f7fd28383b451bf6fc94f10581fc7648',
            'thumbnail': 'https://images.paramount.tech/uri/mgid:arc:imageassetref:shared.southpark.gsa.de:bc418f83-7342-11ea-a59c-0a7527021758',
            'timestamp': 879915600,
            'upload_date': '19971119',
            'release_date': '19971119',
            'duration': 1319.0,
            'chapters': 'count:4',
            'genres': ['Comedy'],
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 8',
            'episode_number': 8,
        },
    }]


class SouthParkLatIE(SouthParkIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'southpark.lat'
    _VALID_URL = r'https?://(?:www\.)?southpark\.lat/(?:en/)?(?:video-?clips?|collections|episod(?:e|io)s)/(?P<id>[^/?#&]+)'
    _GEO_COUNTRIES = [
        'AR', 'BO', 'CL', 'CO', 'CR', 'DO', 'EC', 'GT', 'HN',
        'MX', 'NI', 'PA', 'PY', 'PE', 'UY', 'VE',
    ]
    _TESTS = [{
        'url': 'https://www.southpark.lat/en/collections/29ve08/south-park-heating-up/lydbrc',
        'only_matching': True,
    }, {
        # clip
        'url': 'https://www.southpark.lat/en/video-clips/ct46op/south-park-tooth-fairy-cartman',
        'info_dict': {
            'id': 'e99d45ea-ed00-11e0-aca6-0026b9414f30',
            'ext': 'mp4',
            'title': 'Tooth Fairy Cartman',
            'description': 'md5:11656c34e92f2ab9491e01de43200baa',
            'thumbnail': 'https://images.paramount.tech/uri/mgid:arc:imageassetref:shared.southpark.latam.en-us:5e4fe2b3-ed07-49ec-9c10-320cb97b7d9a',
            'timestamp': 954990360,
            'upload_date': '20000406',
            'release_date': '20000406',
            'duration': 93.26,
            'tags': 'count:16',
            'season': 'Season 4',
            'season_number': 4,
            'episode': 'Episode 1',
            'episode_number': 1,
        },
        'params': {
            'format': 'best/bestvideo',
            'skip_download': 'ffmpeg required',
        },
    }, {
        # episode
        'url': 'https://www.southpark.lat/episodios/9h0qbg/south-park-orgia-gatuna-temporada-3-ep-7',
        'info_dict': {
            'id': '600d273a-ecfd-11e0-aca6-0026b9414f30',
            'ext': 'mp4',
            'title': 'Orgía Gatuna ',
            'description': 'md5:73c6648413f5977026abb792a25c65d5',
            'thumbnail': 'https://images.paramount.tech/uri/mgid:arc:imageassetref:shared.southpark.latam:ae85e511-741e-11ea-a59c-0a7527021758',
            'timestamp': 931924800,
            'upload_date': '19990714',
            'release_date': '19990714',
            'duration': 1319.0,
            'chapters': 'count:4',
            'genres': ['Comedy'],
            'season': 'Season 3',
            'season_number': 3,
            'episode': 'Episode 7',
            'episode_number': 7,
        },
        'params': {
            'format': 'best/bestvideo',
            'skip_download': 'ffmpeg required',
        },
    }]


class SouthParkNlIE(SouthParkIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'southpark.nl'
    _VALID_URL = r'https?://(?:www\.)?(?P<url>southpark\.nl/(?:clips|(?:full-)?episodes|collections)/(?P<id>.+?)(\?|#|$))'
    _TESTS = [{
        'url': 'http://www.southpark.nl/full-episodes/s18e06-freemium-isnt-free',
        'info_dict': {
            'id': '123',
            'title': 'Freemium Isn\'t Free',
            'description': 'Stan is addicted to the new Terrance and Phillip mobile game.',
        },
        'playlist_mincount': 3,
    }]


class SouthParkDkIE(SouthParkIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'southparkstudios.dk'
    _VALID_URL = r'https?://(?:www\.)?(?P<url>southparkstudios\.(?:dk|nu)/(?:(?:video-)?clips|(?:full-)?episodes|collections)/(?P<id>.+?)(\?|#|$))'
    _GEO_COUNTRIES = ['DK', 'NO', 'SE', 'FI']  # DE, AT, CH, LI also work
    _TESTS = [{
        'url': 'http://www.southparkstudios.dk/full-episodes/s18e07-grounded-vindaloop',
        'info_dict': {
            'title': 'Grounded Vindaloop',
            'description': 'Butters is convinced he\'s living in a virtual reality.',
        },
        'playlist_mincount': 3,
        'skip': 'Redirect to .nu homepage',
    }, {
        'url': 'https://www.southparkstudios.nu/episodes/y3uvvc/south-park-grounded-vindaloop-season-18-ep-7',
        'info_dict': {
            'id': 'f60690a7-21a7-4ee7-8834-d7099a8707ab',
            'ext': 'mp4',
            'title': 'Grounded Vindaloop',
            'description': 'Butters is convinced he\'s living in a virtual reality.',
            'thumbnail': 'https://images.paramount.tech/uri/mgid:arc:imageassetref:shared.southpark.nordics:9ba7cb34-77f4-11ea-a59c-0a7527021758',
            'timestamp': 1415847600,
            'upload_date': '20141113',
            'release_date': '20141112',
            'duration': 1319.0,
            'chapters': 'count:5',
            'genres': ['Comedy'],
            'season': 'Season 18',
            'season_number': 18,
            'episode': 'Episode 7',
            'episode_number': 7,
        },
        'params': {
            'format': 'best/bestvideo',
            'skip_download': 'ffmpeg required',
        },
    }, {
        # Redirects to above
        'url': 'http://www.southparkstudios.nu/full-episodes/s18e07-grounded-vindaloop',
        'only_matching': True,
    }, {
        'url': 'https://www.southparkstudios.nu/video-clips/k42mrf/south-park-kick-the-baby',
        'info_dict': {
            'id': 'a68c2884-ed00-11e0-aca6-0026b9414f30',
            'ext': 'mp4',
            'title': 'Kick the Baby',
            'description': 'Cartman gets probed by aliens.',
            'thumbnail': 'https://images.paramount.tech/uri/mgid:arc:imageassetref:shared.southpark.nordics:1f55927d-d2a5-44e9-855c-43bd59cabfce',
            'timestamp': 871527600,
            'upload_date': '19970814',
            'release_date': '19970814',
            'duration': 165.416,
            'tags': 'count:13',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 1',
            'episode_number': 1,
        },
        'params': {
            'format': 'best/bestvideo',
            'skip_download': 'ffmpeg required',
        },
    }, {
        'url': 'http://www.southparkstudios.dk/collections/2476/superhero-showdown/1',
        'only_matching': True,
    }, {
        'url': 'http://www.southparkstudios.nu/collections/2476/superhero-showdown/1',
        'only_matching': True,
    }]


class SouthParkSeasonsIE(InfoExtractor):
    IE_NAME = 'SouthPark:Seasons'
    _VALID_URL = r'(?P<domain>https?://(?:www\.)?southpark(?:\.cc|studios)\.com)/seasons/(?P<series>[^/]+)/?(?P<id>.+?)?(\?|#|$)'
    _TESTS = [{
        'url': 'https://www.southparkstudios.com/seasons/south-park/lrnlos/season-25',
        'info_dict': {
            'id': 'f7f6dc67-7d50-11ec-a4f1-70df2f866ace',
            'title': 'South Park - Season 25',
        },
        'playlist_mincount': 6,
    }]

    def _real_extract(self, url):
        video_id, series, domain = self._match_valid_url(url).group('id', 'series', 'domain')
        webpage = self._download_webpage(url, video_id)
        page_data = self._search_json(r'window\.__DATA__\s*=\s*', webpage, 'Page Data', video_id,
                                      end_pattern=r';\n')
        if mgids := traverse_obj(page_data, (
                'children', lambda _, v: v['type'] == 'MainContainer', 'children', lambda _, v: v['type'] == 'LineList',
                lambda _, v: v['type'] == 'video-guide', 'items', 0, 'meta', {
                    'season_mgid': ('seasonMgid', {str}),
                    'series_mgid': ('seriesMgid', {str}),
                }), get_all=False):
            if mgid := mgids.get('season_mgid') if video_id else mgids.get('series_mgid'):
                api_url = domain + '/api/context/' + urllib.parse.quote_plus(mgid) + '/episode/0/10000'
                episodes = self._download_json(api_url, video_id)
                if items := episodes.get('items'):
                    return self.playlist_result((
                        self.url_result(domain + item['url'], **traverse_obj(item, {
                            'id': ('id', {str}),
                            'title': ('meta', 'subHeader', {str}),
                            'description': ('meta', 'description', {str_or_none}),
                            'thumbnail': ('media', 'image', 'url', {url_or_none}),
                            'release_date': ('meta', 'date', {lambda v: v.split('/')},
                                             {lambda v: v[2] + v[0] + v[1]}),
                            'season_number': ('meta', 'header', 'title', 'text', {lambda v: v.split(' • ')[0]},
                                              {lambda v: int(v.strip('S')) if re.match(r'^S\d+$', v) else None}),
                            'episode_number': ('meta', 'header', 'title', 'text', {lambda v: v.split(' • ')[-1]},
                                               {lambda v: int(v.strip('E')) if re.match(r'^E\d+$', v) else None}),
                            'duration': ('media', 'duration', {parse_duration}),
                        })) for item in items),
                        playlist_id=mgid.split(':')[-1],
                        playlist_title=join_nonempty(series.replace('-', ' ').title(),
                                                     (video_id or '').split('/')[-1].replace('-', ' ').title(), delim=' - '),
                    )
        raise ExtractorError('Unable to extract ' + ('season' if video_id else 'series') + ' data')
