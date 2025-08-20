import re
import urllib.parse

from .mtv import MTVServicesBaseIE
from ..utils import (
    ExtractorError,
    join_nonempty,
    parse_duration,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class SouthParkIE(MTVServicesBaseIE):
    IE_NAME = 'southpark.cc.com'
    _VALID_URL = r'https?://(?:www\.)?southpark(?:\.cc|studios)\.com/(?:video-clips|episodes|collections)/(?P<id>[^?#]+)'
    _TESTS = [{
        'url': 'https://southpark.cc.com/video-clips/d7wr06/south-park-you-all-agreed-to-counseling',
        'info_dict': {
            'id': '31929ad5-8269-11eb-8774-70df2f866ace',
            'ext': 'mp4',
            'display_id': 'd7wr06/south-park-you-all-agreed-to-counseling',
            'title': 'You All Agreed to Counseling',
            'description': 'md5:01f78fb306c7042f3f05f3c78edfc212',
            'duration': 134.552,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'South Park',
            'season': 'Season 24',
            'season_number': 24,
            'episode': 'Episode 2',
            'episode_number': 2,
            'timestamp': 1615352400,
            'upload_date': '20210310',
            'release_timestamp': 1615352400,
            'release_date': '20210310',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://southpark.cc.com/episodes/940f8z/south-park-cartman-gets-an-anal-probe-season-1-ep-1',
        'info_dict': {
            'id': '5fb8887e-ecfd-11e0-aca6-0026b9414f30',
            'ext': 'mp4',
            'display_id': '940f8z/south-park-cartman-gets-an-anal-probe-season-1-ep-1',
            'title': 'Cartman Gets An Anal Probe',
            'description': 'md5:964e1968c468545752feef102b140300',
            'channel': 'Comedy Central',
            'duration': 1319.0,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'South Park',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 871527600,
            'upload_date': '19970814',
            'release_timestamp': 871444800,
            'release_date': '19970813',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://southpark.cc.com/collections/dejukt/south-park-best-of-mr-mackey/tphx9j',
        'only_matching': True,
    }, {
        'url': 'https://www.southparkstudios.com/episodes/h4o269/south-park-stunning-and-brave-season-19-ep-1',
        'only_matching': True,
    }]


class SouthParkEsIE(MTVServicesBaseIE):
    IE_NAME = 'southpark.cc.com:español'
    _VALID_URL = r'https?://(?:www\.)?southpark\.cc\.com/es/episodios/(?P<id>[^?#]+)'
    _GEO_COUNTRIES = ['ES']
    _GEO_BYPASS = True
    _TESTS = [{
        'url': 'https://southpark.cc.com/es/episodios/er4a32/south-park-aumento-de-peso-4000-temporada-1-ep-2',
        'info_dict': {
            'id': '5fb94f0c-ecfd-11e0-aca6-0026b9414f30',
            'ext': 'mp4',
            'display_id': 'er4a32/south-park-aumento-de-peso-4000-temporada-1-ep-2',
            'title': 'Aumento de peso 4000',
            'description': 'md5:a939b4819ea74c245a0cde180de418c0',
            'channel': 'Comedy Central',
            'duration': 1320.0,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'South Park',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 2',
            'episode_number': 2,
            'timestamp': 872078400,
            'upload_date': '19970820',
            'release_timestamp': 872078400,
            'release_date': '19970820',
        },
        'params': {'skip_download': 'm3u8'},
    }]


class SouthParkDeIE(MTVServicesBaseIE):
    IE_NAME = 'southpark.de'
    _VALID_URL = r'https?://(?:www\.)?southpark\.de/(?:en/)?(?:videoclip|collections|episodes|video-clips|folgen)/(?P<id>[^?#]+)'
    _GEO_COUNTRIES = ['DE']
    _GEO_BYPASS = True
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
            'ext': 'mp4',
            'id': 'e99d45ea-ed00-11e0-aca6-0026b9414f30',
            'display_id': 'ct46op/south-park-tooth-fairy-cartman',
            'title': 'Tooth Fairy Cartman',
            'description': 'Cartman steals Butters\' tooth and gets four dollars for it.',
            'duration': 93.26,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'South Park',
            'season': 'Season 4',
            'season_number': 4,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 954990360,
            'upload_date': '20000406',
            'release_timestamp': 954990360,
            'release_date': '20000406',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # episode
        'url': 'https://www.southpark.de/en/episodes/yy0vjs/south-park-the-pandemic-special-season-24-ep-1',
        'info_dict': {
            'ext': 'mp4',
            'id': '230a4f02-f583-11ea-834d-70df2f866ace',
            'display_id': 'yy0vjs/south-park-the-pandemic-special-season-24-ep-1',
            'title': 'The Pandemic Special',
            'description': 'md5:ae0d875eff169dcbed16b21531857ac1',
            'channel': 'Comedy Central',
            'duration': 2724.0,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'South Park',
            'season': 'Season 24',
            'season_number': 24,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 1601932260,
            'upload_date': '20201005',
            'release_timestamp': 1601932270,
            'release_date': '20201005',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # clip
        'url': 'https://www.southpark.de/videoclip/ct46op/south-park-zahnfee-cartman',
        'info_dict': {
            'ext': 'mp4',
            'id': 'e99d45ea-ed00-11e0-aca6-0026b9414f30',
            'display_id': 'ct46op/south-park-zahnfee-cartman',
            'title': 'Zahnfee Cartman',
            'description': 'md5:b917eec991d388811d911fd1377671ac',
            'duration': 93.26,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'South Park',
            'season': 'Season 4',
            'season_number': 4,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 954990360,
            'upload_date': '20000406',
            'release_timestamp': 954990360,
            'release_date': '20000406',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # episode
        'url': 'https://www.southpark.de/folgen/4r4367/south-park-katerstimmung-staffel-12-ep-3',
        'info_dict': {
            'ext': 'mp4',
            'id': '68c79aa4-ecfd-11e0-aca6-0026b9414f30',
            'display_id': '4r4367/south-park-katerstimmung-staffel-12-ep-3',
            'title': 'Katerstimmung',
            'description': 'md5:94e0e2cd568ffa635e0725518bb4b180',
            'channel': 'Comedy Central',
            'duration': 1320.0,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'South Park',
            'season': 'Season 12',
            'season_number': 12,
            'episode': 'Episode 3',
            'episode_number': 3,
            'timestamp': 1206504000,
            'upload_date': '20080326',
            'release_timestamp': 1206504000,
            'release_date': '20080326',
        },
        'params': {'skip_download': 'm3u8'},
    }]


class SouthParkLatIE(MTVServicesBaseIE):
    IE_NAME = 'southpark.lat'
    _VALID_URL = r'https?://(?:www\.)?southpark\.lat/(?:en/)?(?:video-?clips?|collections|episod(?:e|io)s)/(?P<id>[^?#]+)'
    _GEO_COUNTRIES = ['MX']
    _GEO_BYPASS = True
    _TESTS = [{
        'url': 'https://www.southpark.lat/en/video-clips/ct46op/south-park-tooth-fairy-cartman',
        'info_dict': {
            'ext': 'mp4',
            'id': 'e99d45ea-ed00-11e0-aca6-0026b9414f30',
            'display_id': 'ct46op/south-park-tooth-fairy-cartman',
            'title': 'Tooth Fairy Cartman',
            'description': 'Cartman steals Butters\' tooth and gets four dollars for it.',
            'duration': 93.26,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'South Park',
            'season': 'Season 4',
            'season_number': 4,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 954990360,
            'upload_date': '20000406',
            'release_timestamp': 954990360,
            'release_date': '20000406',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.southpark.lat/episodios/9h0qbg/south-park-orgia-gatuna-temporada-3-ep-7',
        'info_dict': {
            'ext': 'mp4',
            'id': '600d273a-ecfd-11e0-aca6-0026b9414f30',
            'display_id': '9h0qbg/south-park-orgia-gatuna-temporada-3-ep-7',
            'title': 'Orgía Gatuna ',
            'description': 'md5:73c6648413f5977026abb792a25c65d5',
            'channel': 'Comedy Central',
            'duration': 1320.0,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'South Park',
            'season': 'Season 3',
            'season_number': 3,
            'episode': 'Episode 7',
            'episode_number': 7,
            'timestamp': 931924800,
            'upload_date': '19990714',
            'release_timestamp': 931924800,
            'release_date': '19990714',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.southpark.lat/en/collections/29ve08/south-park-heating-up/lydbrc',
        'only_matching': True,
    }]


class SouthParkDkIE(MTVServicesBaseIE):
    IE_NAME = 'southparkstudios.nu'
    _VALID_URL = r'https?://(?:www\.)?southparkstudios\.nu/(?:video-clips|episodes|collections)/(?P<id>[^?#]+)'
    _GEO_COUNTRIES = ['DK']
    _GEO_BYPASS = True
    _TESTS = [{
        'url': 'https://www.southparkstudios.nu/episodes/y3uvvc/south-park-grounded-vindaloop-season-18-ep-7',
        'info_dict': {
            'ext': 'mp4',
            'id': 'f60690a7-21a7-4ee7-8834-d7099a8707ab',
            'display_id': 'y3uvvc/south-park-grounded-vindaloop-season-18-ep-7',
            'title': 'Grounded Vindaloop',
            'description': 'Butters is convinced he\'s living in a virtual reality.',
            'channel': 'Comedy Central',
            'duration': 1319.0,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'South Park',
            'season': 'Season 18',
            'season_number': 18,
            'episode': 'Episode 7',
            'episode_number': 7,
            'timestamp': 1415847600,
            'upload_date': '20141113',
            'release_timestamp': 1415768400,
            'release_date': '20141112',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.southparkstudios.nu/collections/8dk7kr/south-park-best-of-south-park/sd5ean',
        'only_matching': True,
    }, {
        'url': 'https://www.southparkstudios.nu/video-clips/k42mrf/south-park-kick-the-baby',
        'only_matching': True,
    }]


class SouthParkComBrIE(MTVServicesBaseIE):
    IE_NAME = 'southparkstudios.com.br'
    _VALID_URL = r'https?://(?:www\.)?southparkstudios\.com\.br/(?:en/)?(?:video-clips|episodios|collections|episodes)/(?P<id>[^?#]+)'
    _GEO_COUNTRIES = ['BR']
    _GEO_BYPASS = True
    _TESTS = [{
        'url': 'https://www.southparkstudios.com.br/video-clips/3vifo0/south-park-welcome-to-mar-a-lago7',
        'info_dict': {
            'ext': 'mp4',
            'id': 'ccc3e952-7352-11f0-b405-16fff45bc035',
            'display_id': '3vifo0/south-park-welcome-to-mar-a-lago7',
            'title': 'Welcome to Mar-a-Lago',
            'description': 'The President welcomes Mr. Mackey to Mar-a-Lago, a magical place where anything can happen.',
            'duration': 139.223,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'South Park',
            'season': 'Season 27',
            'season_number': 27,
            'episode': 'Episode 2',
            'episode_number': 2,
            'timestamp': 1754546400,
            'upload_date': '20250807',
            'release_timestamp': 1754546400,
            'release_date': '20250807',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.southparkstudios.com.br/episodios/940f8z/south-park-cartman-ganha-uma-sonda-anal-temporada-1-ep-1',
        'only_matching': True,
    }, {
        'url': 'https://www.southparkstudios.com.br/collections/8dk7kr/south-park-best-of-south-park/sd5ean',
        'only_matching': True,
    }, {
        'url': 'https://www.southparkstudios.com.br/en/episodes/5v0oap/south-park-south-park-the-25th-anniversary-concert-ep-1',
        'only_matching': True,
    }]


class SouthParkCoUkIE(MTVServicesBaseIE):
    IE_NAME = 'southparkstudios.co.uk'
    _VALID_URL = r'https?://(?:www\.)?southparkstudios\.co\.uk/(?:video-clips|collections|episodes)/(?P<id>[^?#]+)'
    _GEO_COUNTRIES = ['UK']
    _GEO_BYPASS = True
    _TESTS = [{
        'url': 'https://www.southparkstudios.co.uk/video-clips/8kabfr/south-park-respectclydesauthority',
        'info_dict': {
            'ext': 'mp4',
            'id': 'f6d9af23-734e-11f0-b405-16fff45bc035',
            'display_id': '8kabfr/south-park-respectclydesauthority',
            'title': '#RespectClydesAuthority',
            'description': 'After learning about Clyde\'s Podcast, Cartman needs to see it for himself.',
            'duration': 45.045,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'South Park',
            'season': 'Season 27',
            'season_number': 27,
            'episode': 'Episode 2',
            'episode_number': 2,
            'timestamp': 1754546400,
            'upload_date': '20250807',
            'release_timestamp': 1754546400,
            'release_date': '20250807',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.southparkstudios.co.uk/episodes/e1yoxn/south-park-imaginationland-season-11-ep-10',
        'only_matching': True,
    }, {
        'url': 'https://www.southparkstudios.co.uk/collections/8dk7kr/south-park-best-of-south-park/sd5ean',
        'only_matching': True,
    }]


class SouthParkSeasonsIE(SouthParkIE):
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
