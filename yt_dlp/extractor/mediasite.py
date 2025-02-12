import itertools
import json
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    float_or_none,
    join_nonempty,
    mimetype2ext,
    smuggle_url,
    str_or_none,
    try_call,
    try_get,
    unified_strdate,
    unsmuggle_url,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj

_ID_RE = r'(?:[0-9a-f]{32,34}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12,14})'


class MediasiteIE(InfoExtractor):
    _VALID_URL = rf'''(?xi)https?://[^/]+/Mediasite/(?:Play
                                                       |Showcase/[^/#?]+/Presentation
                                                       |Channel/[^/#?]+/watch
                                                    )/(?P<id>{_ID_RE})(?P<query>\?[^#]+|)'''
    _EMBED_REGEX = [rf'(?xi)<iframe\b[^>]+\bsrc=(["\'])(?P<url>(?:(?:https?:)?//[^/]+)?/Mediasite/Play/{_ID_RE}(?:\?.*?)?)\1']
    _TESTS = [
        {
            'url': 'https://hitsmediaweb.h-its.org/mediasite/Play/2db6c271681e4f199af3c60d1f82869b1d',
            'info_dict': {
                'id': '2db6c271681e4f199af3c60d1f82869b1d',
                'ext': 'mp4',
                'title': 'Lecture: Tuesday, September 20, 2016 - Sir Andrew Wiles',
                'description': 'Sir Andrew Wiles: “Equations in arithmetic”\\n\\nI will describe some of the interactions between modern number theory and the problem of solving equations in rational numbers or integers\\u0027.',
                'thumbnail': r're:^https?://.*\.jpg(?:\?.*)?$',
                'cast': ['Sir Andrew J. Miles, Silver Plaque of the IMU, 1998 | Abel Prize, 2016'],
                'duration': 2978.0,
                'timestamp': 1474268400.0,
                'upload_date': '20160919',
            },
            'skip': 'HTTP Error 500: Service Fault',
        },
        {
            'url': 'http://mediasite.uib.no/Mediasite/Play/90bb363295d945d6b548c867d01181361d?catalog=a452b7df-9ae1-46b7-a3ba-aceeb285f3eb',
            'info_dict': {
                'id': '90bb363295d945d6b548c867d01181361d',
                'ext': 'mp4',
                'upload_date': '20150429',
                'title': '5) IT-forum 2015-Dag 1  - Dungbeetle -  How and why Rain created a tiny bug tracker for Unity',
                'timestamp': 1430311380.0,
            },
            'skip': 'no longer exist',
        },
        {
            'url': 'https://collegerama.tudelft.nl/Mediasite/Play/585a43626e544bdd97aeb71a0ec907a01d',
            'md5': '481fda1c11f67588c0d9d8fbdced4e39',
            'info_dict': {
                'id': '585a43626e544bdd97aeb71a0ec907a01d',
                'ext': 'mp4',
                'title': 'Een nieuwe wereld: waarden, bewustzijn en techniek van de mensheid 2.0.',
                'description': '',
                'thumbnail': r're:^https?://.*\.jpg(?:\?.*)?$',
                'cast': ['H. Wijffels'],
                'duration': 7713.088,
                'timestamp': 1413309600,
                'upload_date': '20141014',
            },
            'params': {
                # format 'video1-1.1' HTTP Error 400: Bad Request
                'skip_download': True,
            },
        },
        {
            'url': 'https://collegerama.tudelft.nl/Mediasite/Play/86a9ea9f53e149079fbdb4202b521ed21d?catalog=fd32fd35-6c99-466c-89d4-cd3c431bc8a4',
            'md5': 'ef1fdded95bdf19b12c5999949419c92',
            'info_dict': {
                'id': '86a9ea9f53e149079fbdb4202b521ed21d',
                'ext': 'wmv',
                'title': '64ste Vakantiecursus: Afvalwater',
                'description': 'md5:7fd774865cc69d972f542b157c328305',
                'thumbnail': r're:^https?://.*\.jpg(?:\?.*?)?$',
                'cast': ['D.J. van den Berg', 'L.C. Rietveld', 'D. van Halem', 'N.C. van de Giesen', 'J.Q.J.C. Verberk'],
                'duration': 10853,
                'timestamp': 1326446400,
                'upload_date': '20120113',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'http://digitalops.sandia.gov/Mediasite/Play/24aace4429fc450fb5b38cdbf424a66e1d',
            'md5': '9422edc9b9a60151727e4b6d8bef393d',
            'info_dict': {
                'id': '24aace4429fc450fb5b38cdbf424a66e1d',
                'ext': 'mp4',
                'title': 'Xyce Software Training - Section 1 - Apr. 2012',
                'description': r're:(?s)SAND Number: SAND 2013-7800.{200,}',
                'thumbnail': r're:^https?://.*\.jpg(?:\?.*)?$',
                'cast': ['01400 Computation, Computers \\u0026 Math'],
                'duration': 7794,
                'timestamp': 1333983600,
                'upload_date': '20120409',
            },
            'params': {
                # format 'video1-1.0' HTTP Error 400: Bad Request
                'skip_download': True,
            },
        },
        {
            'url': 'https://events7.mediasite.com/Mediasite/Play/a7812390a2d44739ae857527e05776091d',
            'info_dict': {
                'id': 'a7812390a2d44739ae857527e05776091d',
                'ext': 'mp4',
                'title': 'Practical Prevention, Detection and Responses to the New Threat Landscape',
                'description': r're:^The bad guys aren’t standing still, and neither is Okta',
                'thumbnail': r're:^https?://.*\.jpg(?:\?.*)?$',
                'cast': ['Franklin Rosado', 'Alex Bovee'],
                'duration': 2415.487,
                'timestamp': 1472567400,
                'upload_date': '20160830',
            },
        },
        {
            'url': 'https://collegerama.tudelft.nl/Mediasite/Showcase/livebroadcast/Presentation/ada7020854f743c49fbb45c9ec7dbb351d',
            'info_dict': {
                'id': 'ada7020854f743c49fbb45c9ec7dbb351d',
                'ext': 'mp4',
                'title': 'Nachtelijk weer: een koud kunstje?',
                'description': '',
                'thumbnail': r're:^https?://.*\.jpg(?:\?.*)?$',
                'timestamp': 1542981600,
                'duration': 4000.879,
                'cast': ['B.J.H. van de Wiel'],
                'upload_date': '20181123',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'https://uconnhealth.mediasite.com/Mediasite/Channel/medical_grand_rounds/watch/1eeff651adc74b2fb17089ada14b61041d',
            'info_dict': {
                'id': '1eeff651adc74b2fb17089ada14b61041d',
                'ext': 'mp4',
                'title': 'Adrenal Adenomas Ruining the Renals  12/12/2024 ',
                'description': '',
                'thumbnail': r're:^https?://.*\.jpg(?:\?.*)?$',
                'cast': ['Matthew Widlus MD, Internal Medicine Resident, PGY-3 Department of Medicine  UConn Health'],
                'duration': 3243.0,
                'timestamp': 1733990400,
                'upload_date': '20241212',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'https://mediasite.ntnu.no/Mediasite/Showcase/default/Presentation/7d8b913259334b688986e970fae6fcb31d',
            'only_matching': True,
        },
        {
            # dashed id
            'url': 'https://hitsmediaweb.h-its.org/mediasite/Play/2db6c271-681e-4f19-9af3-c60d1f82869b1d',
            'only_matching': True,
        },
    ]

    # look in Mediasite.Core.js (Mediasite.ContentStreamType[*])
    _STREAM_TYPES = {
        0: 'video1',  # the main video
        2: 'slide',
        3: 'presentation',
        4: 'video2',  # screencast?
        5: 'video3',
    }

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for embed_url in super()._extract_embed_urls(url, webpage):
            yield smuggle_url(embed_url, {'UrlReferrer': url})

    def __extract_slides(self, *, stream_id, snum, stream, duration, images):
        slide_base_url = stream['SlideBaseUrl']
        playback_ticket = stream.get('SlidePlaybackTicketId')
        fname_template = stream['SlideImageFileNameTemplate']
        if fname_template != 'slide_{0:D4}.jpg' and fname_template != 'slide_%s_{0:D4}.jpg' % stream_id:
            self.report_warning('Unusual slide file name template; report a bug if slide downloading fails')
        fname_template = re.sub(r'\{0:D([0-9]+)\}', r'{0:0\1}', fname_template)

        fragments = []
        for i, slide in enumerate(stream['Slides']):
            if i == 0:
                if slide['Time'] > 0:
                    default_slide = images.get('DefaultSlide')
                    if default_slide is None:
                        default_slide = images.get('DefaultStreamImage')
                    if default_slide is not None:
                        default_slide = default_slide['ImageFilename']
                    if default_slide is not None:
                        fragments.append({
                            'path': default_slide,
                            'duration': slide['Time'] / 1000,
                        })

            next_time = try_call(
                lambda: stream['Slides'][i + 1]['Time'],
                lambda: duration,
                lambda: slide['Time'],
                expected_type=(int, float))

            fragments.append({
                'path': join_nonempty(fname_template.format(slide.get('Number', i + 1)),
                                      playback_ticket, delim='?playbackTicket='),
                'duration': (next_time - slide['Time']) / 1000,
            })

        return {
            'format_id': f'{stream_id}-{snum}.slides',
            'ext': 'mhtml',
            'url': slide_base_url,
            'protocol': 'mhtml',
            'acodec': 'none',
            'vcodec': 'none',
            'format_note': 'Slides',
            'fragments': fragments,
            'fragment_base_url': slide_base_url,
        }

    def _get_transcript_txt(self, transcript_url, resource_id, lang_code, lang_name=None, force_download=True):
        ts = {
            'name': join_nonempty(lang_name, '(Untimed)', delim=' '),
            'ext': 'ttml',
        }
        if ((self.get_param('writesubtitles') or self.get_param('writeautomaticsub'))
                and (force_download or 'ttml' in self.get_param('subtitlesformat'))):
            if transcript := self._download_webpage(
                    transcript_url, resource_id, note='Downloading transcript', fatal=False):
                d = ('<?xml version="1.0" encoding="utf-8" ?>\n'
                     '<tt\n  xmlns="http://www.w3.org/ns/ttml"\n'
                     '  xmlns:ttp="http://www.w3.org/ns/ttml#parameter"\n'
                     '  xmlns:xml="http://www.w3.org/XML/1998/namespace"\n'
                     f'  xml:lang="{lang_code}">\n'
                     '<head>\n</head>\n<body>\n<div>\n<p xml:id="transcript">\n<span>\n</span><span>'
                     + re.sub(r'\r?\n[\t\f ]*', '\n</span><span>', transcript.replace('&', '&amp;').strip())
                     + '\n</span>\n</p>\n</div>\n</body>\n</tt>')
                return {'data': d, **ts}
        else:
            return {'url': transcript_url, **ts}
        return {}

    def _real_extract(self, url):
        url, data = unsmuggle_url(url, {})
        mobj = self._match_valid_url(url)
        resource_id = mobj.group('id')
        query = mobj.group('query')

        webpage, urlh = self._download_webpage_handle(url, resource_id)  # XXX: add UrlReferrer?
        redirect_url = urlh.url

        # XXX: might have also extracted UrlReferrer and QueryString from the html
        service_path = urllib.parse.urljoin(redirect_url, self._html_search_regex(
            r'<div[^>]+\bid=["\']ServicePath[^>]+>(.+?)</div>', webpage, resource_id,
            default='/Mediasite/PlayerService/PlayerService.svc/json'))

        player_options = self._download_json(
            f'{service_path}/GetPlayerOptions', resource_id,
            headers={
                'Content-type': 'application/json; charset=utf-8',
                'X-Requested-With': 'XMLHttpRequest',
            },
            data=json.dumps({
                'getPlayerOptionsRequest': {
                    'ResourceId': resource_id,
                    'QueryString': query,
                    'UrlReferrer': data.get('UrlReferrer', ''),
                    'UseScreenReader': False,
                },
            }).encode())['d']

        presentation = player_options['Presentation']
        if presentation is None:
            if iframe_src := self._html_search_regex(
                    r'<iframe src="([^"]+)"', webpage, 'iframe_src', default=None):
                u = urllib.parse.urlparse(iframe_src)
                return self.url_result(
                    u._replace(netloc=u.netloc.replace(str(u.port), '')).geturl())
            raise ExtractorError(
                'Mediasite says: {}'.format(player_options['PlayerPresentationStatusMessage']),
                expected=True)

        title = (presentation.get('Title')
                 or self._html_extract_title(webpage, 'title', fatal=False))
        thumbnails = []
        formats = []
        for snum, stream in enumerate(presentation['Streams']):
            stream_type = stream.get('StreamType')
            if stream_type is None:
                continue

            video_urls = stream.get('VideoUrls')
            if not isinstance(video_urls, list):
                video_urls = []

            stream_id = self._STREAM_TYPES.get(
                stream_type, 'type%u' % stream_type)

            stream_formats = []
            for unum, video in enumerate(video_urls):
                video_url = url_or_none(video.get('Location'))
                if not video_url:
                    continue
                # XXX: if Stream.get('CanChangeScheme', False), switch scheme to HTTP/HTTPS

                media_type = video.get('MediaType')
                ext = mimetype2ext(video.get('MimeType'))
                if media_type == 'SS':
                    stream_formats.extend(self._extract_ism_formats(
                        video_url, resource_id,
                        ism_id=f'{stream_id}-{snum}.{unum}',
                        fatal=False))
                elif media_type == 'Dash':
                    stream_formats.extend(self._extract_mpd_formats(
                        video_url, resource_id,
                        mpd_id=f'{stream_id}-{snum}.{unum}',
                        fatal=False))
                elif ext in ('m3u', 'm3u8'):
                    stream_formats.extend(self._extract_m3u8_formats(
                        video_url, resource_id, media_type.lower(),
                        m3u8_id=f'{stream_id}-{snum}.{unum}',
                        fatal=False))
                elif self._is_valid_url(video_url, resource_id, f'{stream_id}-{snum}.{unum}'):
                    # TODO: investigate why always error 400
                    stream_formats.append({
                        'format_id': f'{stream_id}-{snum}.{unum}',
                        'url': video_url,
                        'ext': ext,
                    })

            images = traverse_obj(
                player_options, ('PlayerLayoutOptions', 'Images', {dict}), default={})
            if stream.get('HasSlideContent'):
                stream_formats.append(self.__extract_slides(
                    stream_id=stream_id,
                    snum=snum,
                    stream=stream,
                    duration=presentation.get('Duration'),
                    images=images,
                ))

            # disprefer 'secondary' streams
            if stream_type != 0:
                for fmt in stream_formats:
                    fmt['quality'] = -10

            thumbnail_url = stream.get('ThumbnailUrl')
            if thumbnail_url:
                thumbnails.append({
                    'id': f'{stream_id}-{snum}',
                    'url': urljoin(redirect_url, thumbnail_url),
                    'preference': -1 if stream_type != 0 else 0,
                })
            formats.extend(stream_formats)

        for i, cast_url in enumerate(('PodcastUrl', 'VodcastUrl')):
            if url_or_none(presentation.get(cast_url)):
                formats.append({
                    'format_id': cast_url.lower().replace('url', ''),
                    'url': presentation.get(cast_url).split('?attachmentName=')[0],
                    'vcodec': None if i else 'none',
                    'preference': None if i else -2,
                })

        transcripts = presentation.get('Transcripts', [])
        captions, subtitles = {}, {}
        for transcript in transcripts:
            lang_code = traverse_obj(
                transcript, (('DetailedLanguageCode', 'LanguageCode'), {str}), get_all=False) or 'und'
            lang_name = transcript.get('Language')
            t = {
                'url': transcript.get('CaptionsUrl'),
                'name': lang_name,
            }
            if 'Auto-Generated' in lang_name:
                captions.setdefault(lang_code, []).append(t)
            else:
                subtitles.setdefault(lang_code, []).append(t)
        if transcript_url := url_or_none(presentation.get('TranscriptUrl')):
            if 'playbackTicket=' not in transcript_url:
                transcript_url = join_nonempty(
                    transcript_url, traverse_obj(presentation, ('Streams', 0, 'SlidePlaybackTicketId', {str})),
                    delim='?playbackTicket=')
            if determine_ext(transcript_url) != 'txt':
                ts = {'url': transcript_url}
            else:
                ts = self._get_transcript_txt(
                    transcript_url, resource_id,
                    *([lang_code, lang_name, False] if len(transcripts) == 1 else ['und']))
            if len(transcripts) == 1:
                (captions or subtitles)[lang_code].insert(0, {
                    'name': lang_name,
                    **ts,
                })
            else:
                subtitles.setdefault('und', []).insert(0, ts)

        return {
            'id': resource_id,
            'title': title,
            'description': presentation.get('Description'),
            'duration': float_or_none(presentation.get('Duration'), 1000),
            'timestamp': float_or_none(presentation.get('UnixTime'), 1000),
            'formats': formats,
            'automatic_captions': captions,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
            'cast': traverse_obj(presentation, ('Presenters', ..., 'Name', {str})),
        }


class MediasiteCatalogIE(InfoExtractor):
    _VALID_URL = rf'''(?xi)
                        (?P<url>https?://[^/]+/Mediasite)
                        /Catalog/Full/
                        (?P<catalog_id>{_ID_RE})
                        (?:
                            /(?P<current_folder_id>{_ID_RE})
                            /(?P<root_dynamic_folder_id>{_ID_RE})
                        )?
                    '''
    _TESTS = [{
        'url': 'http://events7.mediasite.com/Mediasite/Catalog/Full/631f9e48530d454381549f955d08c75e21',
        'info_dict': {
            'id': '631f9e48530d454381549f955d08c75e21',
            'title': 'WCET Summit: Adaptive Learning in Higher Ed: Improving Outcomes Dynamically',
        },
        'playlist_count': 6,
        'expected_warnings': ['is not a supported codec'],
    }, {
        # with CurrentFolderId and RootDynamicFolderId
        'url': 'https://medaudio.medicine.iu.edu/Mediasite/Catalog/Full/9518c4a6c5cf4993b21cbd53e828a92521/97a9db45f7ab47428c77cd2ed74bb98f14/9518c4a6c5cf4993b21cbd53e828a92521',
        'info_dict': {
            'id': '9518c4a6c5cf4993b21cbd53e828a92521',
            'title': 'IUSM Family and Friends Sessions',
        },
        'playlist_count': 2,
    }, {
        'url': 'http://uipsyc.mediasite.com/mediasite/Catalog/Full/d5d79287c75243c58c50fef50174ec1b21',
        'only_matching': True,
    }, {
        # no AntiForgeryToken
        'url': 'https://live.libraries.psu.edu/Mediasite/Catalog/Full/8376d4b24dd1457ea3bfe4cf9163feda21',
        'only_matching': True,
    }, {
        'url': 'https://medaudio.medicine.iu.edu/Mediasite/Catalog/Full/9518c4a6c5cf4993b21cbd53e828a92521/97a9db45f7ab47428c77cd2ed74bb98f14/9518c4a6c5cf4993b21cbd53e828a92521',
        'only_matching': True,
    }, {
        # dashed id
        'url': 'http://events7.mediasite.com/Mediasite/Catalog/Full/631f9e48-530d-4543-8154-9f955d08c75e',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        mediasite_url = mobj.group('url')
        catalog_id = mobj.group('catalog_id')
        current_folder_id = mobj.group('current_folder_id') or catalog_id
        root_dynamic_folder_id = mobj.group('root_dynamic_folder_id')

        webpage = self._download_webpage(url, catalog_id)

        # AntiForgeryToken is optional (e.g. [1])
        # 1. https://live.libraries.psu.edu/Mediasite/Catalog/Full/8376d4b24dd1457ea3bfe4cf9163feda21
        anti_forgery_token = self._search_regex(
            r'AntiForgeryToken\s*:\s*(["\'])(?P<value>(?:(?!\1).)+)\1',
            webpage, 'anti forgery token', default=None, group='value')
        if anti_forgery_token:
            anti_forgery_header = self._search_regex(
                r'AntiForgeryHeaderName\s*:\s*(["\'])(?P<value>(?:(?!\1).)+)\1',
                webpage, 'anti forgery header name',
                default='X-SOFO-AntiForgeryHeader', group='value')

        data = {
            'IsViewPage': True,
            'IsNewFolder': True,
            'AuthTicket': None,
            'CatalogId': catalog_id,
            'CurrentFolderId': current_folder_id,
            'RootDynamicFolderId': root_dynamic_folder_id,
            'ItemsPerPage': 1000,
            'PageIndex': 0,
            'PermissionMask': 'Execute',
            'CatalogSearchType': 'SearchInFolder',
            'SortBy': 'Date',
            'SortDirection': 'Descending',
            'StartDate': None,
            'EndDate': None,
            'StatusFilterList': None,
            'PreviewKey': None,
            'Tags': [],
        }

        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
            'Referer': url,
            'X-Requested-With': 'XMLHttpRequest',
        }
        if anti_forgery_token:
            headers[anti_forgery_header] = anti_forgery_token

        catalog = self._download_json(
            f'{mediasite_url}/Catalog/Data/GetPresentationsForFolder',
            catalog_id, data=json.dumps(data).encode(), headers=headers)

        entries = []
        for video in catalog['PresentationDetailsList']:
            if not isinstance(video, dict):
                continue
            video_id = str_or_none(video.get('Id'))
            if not video_id:
                continue
            entries.append(self.url_result(
                f'{mediasite_url}/Play/{video_id}',
                ie=MediasiteIE.ie_key(), video_id=video_id))

        title = try_get(
            catalog, lambda x: x['CurrentFolder']['Name'], str)

        return self.playlist_result(entries, catalog_id, title)


class MediasiteNamedCatalogIE(InfoExtractor):
    _VALID_URL = r'(?xi)(?P<url>https?://[^/]+/Mediasite)/Catalog/catalogs/(?P<catalog_name>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://msite.misis.ru/Mediasite/Catalog/catalogs/2016-industrial-management-skriabin-o-o',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        mediasite_url = mobj.group('url')
        catalog_name = mobj.group('catalog_name')

        webpage = self._download_webpage(url, catalog_name)

        catalog_id = self._search_regex(
            rf'CatalogId\s*:\s*["\']({_ID_RE})', webpage, 'catalog id')

        return self.url_result(
            f'{mediasite_url}/Catalog/Full/{catalog_id}',
            ie=MediasiteCatalogIE.ie_key(), video_id=catalog_id)


class MediasiteChannelIE(InfoExtractor):
    _QY_RE = r'[^/#?]+/[\w-]+/[^/#?]+/\d+/[^/#?]+'
    _VALID_URL = rf'(?xi)(?P<url>https?://[^/]+/Mediasite/Channel/(?P<id>[^/#?]+)(?:/browse/(?P<query>{_QY_RE}))?/?$)'
    _TESTS = [{
        'url': 'https://fau.mediasite.com/Mediasite/Channel/2024-twts/browse/null/oldest/null/0/null',
        'info_dict': {
            'id': '2024-twts',
            'title': '2024 Teaching with Technology Showcase',
        },
        'playlist_mincount': 13,
    }, {
        'url': 'https://ers.mediasite.com/mediasite/Channel/august_ers_meeting/browse/audit report/relevance/null/0/null',
        'info_dict': {
            'id': 'august_ers_meeting',
            'title': 'August 25th ERS Meeting',
        },
        'playlist_mincount': 4,
    }, {
        'url': 'https://fau.mediasite.com/Mediasite/Channel/osls-2023/',
        'info_dict': {
            'id': 'osls-2023',
            'title': 'Ocean Science Lecture Series 2023',
        },
        'playlist_mincount': 11,
    }, {
        'url': 'https://fau.mediasite.com/Mediasite/Channel/osls-2023',
        'only_matching': True,
    }]

    def _entries(self, json_data, channel_id, query):
        site_data = json_data['SiteData']
        app_root = site_data['ApplicationRoot']
        query = query or [None] * 5
        _sort_by = ('most-recent', 'oldest', 'title-az', 'title-za', 'views')
        for i in itertools.count():
            postdata = {
                'Page': str(i),
                'Rows': 12,
                'SortBy': query[1] or _sort_by[json_data['DefaultSort']],
                'UrlChannelId': channel_id,
                'MediasiteChannelId': json_data['MediasiteChannelId'],
                'AuthTicketId': json_data['AuthTicketId'],
                'SearchBy': query[0],
                'SearchTerm': query[0],
                'Tags': query[2].split(' ') if query[2] else None,
                'FocusToolbarList': None,
                'FolderSelected': query[4],
                'FolderName': None,
                'NavigateFunction': None,
            }
            postdata['FiltersAsJson'] = json.dumps(postdata)
            channel_data = self._download_json(
                f'{app_root}/webapps-api/MediasiteChannelApp/GetMediasiteChannelAppContent',
                channel_id, fatal=True, data=json.dumps(postdata).encode(), headers={
                    'Content-Type': 'application/json; charset=utf-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    site_data['AntiForgeryHeaderName']: site_data['AntiForgeryToken'],
                })
            if traverse_obj(channel_data, ('Results', 'records', {int})) > 0:
                for entry in traverse_obj(channel_data, ('Results', 'rows', ..., {dict})):
                    if play_url := (url_or_none(entry.get('PlayUrl'))
                                    or (f"{app_root.replace('Channel', 'Play')}{entry.get('Id')}"
                                        if entry.get('Id') else None)):
                        yield self.url_result(
                            f"{play_url}?Collection={json_data['MediasiteChannelId']}",
                            **traverse_obj(entry, {
                                'id': ('Id', {str}),
                                'title': (('ObjectData', None), ('Title', 'Name'), {str}),
                                'description': (('ObjectData', None), 'Description', {str_or_none}),
                                'thumbnail': ('ThumbnailUrl', {url_or_none}),
                                'duration': ('ObjectData', ('Duration', 'MediaLength'),
                                             {lambda v: float_or_none(v, 1000)}),
                                'upload_date': ((('ObjectData', 'RecordDateTimeUtc'), 'RecordDate'),
                                                {unified_strdate}),
                            }, get_all=False),
                            **traverse_obj(entry, {
                                'cast': ('ObjectData', 'PresenterList', ..., 'DisplayName', {str_or_none}),
                                'tags': ('Tags'),
                            }))
                if i == traverse_obj(channel_data, ('Results', 'total', {int})) - 1:
                    break
            else:
                return None

    def _real_extract(self, url):
        url, data = unsmuggle_url(url, {})
        mobj = self._match_valid_url(url)
        channel_id = mobj.group('id')
        if query := mobj.group('query'):
            query = [None if x.lower() == 'null' else urllib.parse.unquote(x)
                     for x in query.split('/')]

        webpage = self._download_webpage(url, channel_id)
        init_json = self._search_json(r'window\.ApplicationInitialization\s*=', webpage,
                                      'ApplicationInitialization', channel_id, fatal=True)
        return self.playlist_result(self._entries(init_json, channel_id, query),
                                    playlist_id=channel_id,
                                    playlist_title=init_json['MediasiteChannelName'])
