import json
import re
import urllib.parse

from .common import InfoExtractor
from ..compat import compat_etree_fromstring
from ..networking import Request
from ..networking.exceptions import network_exceptions
from ..utils import (
    ExtractorError,
    clean_html,
    determine_ext,
    float_or_none,
    format_field,
    get_first,
    int_or_none,
    join_nonempty,
    js_to_json,
    merge_dicts,
    parse_count,
    parse_qs,
    qualities,
    str_or_none,
    traverse_obj,
    try_get,
    url_or_none,
    urlencode_postdata,
    urljoin,
    variadic,
)


class FacebookIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                (?:
                    https?://
                        (?:[\w-]+\.)?(?:facebook\.com|facebookwkhpilnemxj7asaniu7vnjjbiltxjqhye3mhbshg7kx5tfyd\.onion)/
                        (?:[^#]*?\#!/)?
                        (?:
                            (?:
                                (?:video/)?[a-z]{5,}(?:\.php|/live)?/?
                            )\?(?:.*?)(?:v|video_id|story_fbid)=|
                            [^/]+/(?:videos|posts)/(?:[^/]+/)?|
                            events/(?:[^/]+/)?|
                            groups/[^/]+/(?:permalink|posts)/|
                            [a-z]{5,}/|
                        )|
                    facebook:
                )
                (?P<id>pfbid[A-Za-z0-9]+|\d+)
                '''
    _EMBED_REGEX = [
        r'<iframe[^>]+?src=(["\'])(?P<url>https?://www\.facebook\.com/(?:video/embed|plugins/video\.php).+?)\1',
        # Facebook API embed https://developers.facebook.com/docs/plugins/embedded-video-player
        r'''(?x)<div[^>]+
                class=(?P<q1>[\'"])[^\'"]*\bfb-(?:video|post)\b[^\'"]*(?P=q1)[^>]+
                data-href=(?P<q2>[\'"])(?P<url>(?:https?:)?//(?:www\.)?facebook.com/.+?)(?P=q2)''',
    ]
    _LOGIN_URL = 'https://www.facebook.com/login.php?next=http%3A%2F%2Ffacebook.com%2Fhome.php&login_attempt=1'
    _CHECKPOINT_URL = 'https://www.facebook.com/checkpoint/?next=http%3A%2F%2Ffacebook.com%2Fhome.php&_fb_noscript=1'
    _NETRC_MACHINE = 'facebook'
    IE_NAME = 'facebook'

    _VIDEO_PAGE_TEMPLATE = 'https://www.facebook.com/video/video.php?v=%s'
    _VIDEO_PAGE_TAHOE_TEMPLATE = 'https://www.facebook.com/video/tahoe/async/%s/?chain=true&isvideo=true&payloadtype=primary'

    _TESTS = [{
        # data.video.story.attachments[].media
        'url': 'https://www.facebook.com/radiokicksfm/videos/3676516585958356/',
        'info_dict': {
            'id': '3676516585958356',
            'ext': 'mp4',
            'title': 'dr Adam Przygoda',
            'description': 'md5:34675bda53336b1d16400265c2bb9b3b',
            'duration': 3133.583,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1692346159,
            'upload_date': '20230818',
            'uploader': 'RADIO KICKS FM',
            'uploader_id': '100063551323670',
            'uploader_url': r're:https?://\w',
            'live_status': 'was_live',
            'concurrent_view_count': int,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
        'skip': 'no longer available',
    }, {
        'url': 'https://www.facebook.com/video.php?v=637842556329505&fref=nf',
        'only_matching': True,
    }, {
        # data.video.story.attachments[].media
        'url': 'https://www.facebook.com/video.php?v=274175099429670',
        'info_dict': {
            'id': '274175099429670',
            'ext': 'mp4',
            'title': r're:Asif',
            'description': '',
            'duration': 131.03,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1399398998,
            'upload_date': '20140506',
            'uploader': 'Asif Nawab Butt',
            'uploader_id': r're:pfbid.*',
            'uploader_url': r're:https?://\w',
            'live_status': 'not_live',
            'concurrent_view_count': int,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
    }, {
        # data.video.story.attachments[].media
        'url': 'https://www.facebook.com/cnn/videos/10155529876156509/',
        'info_dict': {
            'id': '10155529876156509',
            'ext': 'mp4',
            'title': 'Holocaust survivor becomes US citizen',
            'description': 'She survived the holocaust — and years later, she’s getting her citizenship so she can vote for Hillary Clinton http://cnn.it/2eERh5f',
            'duration': 44.181,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1477818095,
            'upload_date': '20161030',
            'uploader': 'CNN',
            'uploader_id': '100059479812265',
            'uploader_url': r're:https?://\w',
            'live_status': 'not_live',
            'concurrent_view_count': int,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
    }, {
        # web_link url: http://giphy.com/gifs/l3vR8BKU0m8uX2mAg
        'url': 'https://www.facebook.com/LaGuiaDelVaron/posts/1072691702860471',
        'info_dict': {
            'id': 'l3vR8BKU0m8uX2mAg',
            'ext': 'mp4',
            'title': 'Nada mas satisfactorio que los otros 5... - La Guía Del Varón',
            'description': 'Nada mas satisfactorio que los otros 5 minutos',
            'tags': ['giphyupload'],
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1477305000,
            'upload_date': '20161022',
            'uploader': 'La Guía Del Varón',
            'uploader_id': '100050567346031',
            'uploader_url': r're:https?://\w',
            'like_count': int,
            'comment_count': int,
        },
        'skip': 'Gif on giphy.com',
    }, {
        # data.node.comet_sections.content.story.attachments[].styles.attachment.media
        'url': 'https://www.facebook.com/groups/1024490957622648/permalink/1396382447100162/',
        'info_dict': {
            'id': '202882990186699',
            'ext': 'mp4',
            'title': 'birb (O v O")',
            'description': 'md5:963dee8a667a2b49f2059cf7ab54fe55',
            'duration': 23.714,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1486035494,
            'upload_date': '20170202',
            'uploader': 'Elisabeth Ahtn',
            'uploader_id': r're:pfbid.*',
            'uploader_url': r're:https?://\w',
            'live_status': 'not_live',
            'concurrent_view_count': int,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
        },
    }, {
        # web_link url: https://www.facebook.com/attn/videos/1569199726448814/
        'url': 'https://www.facebook.com/groups/1645456212344334/posts/3737828833107051/',
        'info_dict': {
            'id': '1569199726448814',
            'ext': 'mp4',
            'title': 'What if marijuana companies were allowed to have TV ads like B...',
            'description': 'What if we treated marijuana ads like big pharma ads?',
            'duration': 148.224,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1511548260,
            'upload_date': '20171124',
            'uploader': 'ATTN:',
            'uploader_id': '100064451419378',
            'uploader_url': r're:https?://\w',
            'live_status': 'not_live',
            'concurrent_view_count': int,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
        'skip': 'post no longer available',
    }, {
        # data.node.comet_sections.content.story.attachments[].styles.attachment.media
        'url': 'https://www.facebook.com/attn/posts/pfbid0j1Czf2gGDVqeQ8KiMLFm3pWN8GxsQmeRrVhimWDzMuKQoR8r4b1knNsejELmUgyhl',
        'info_dict': {
            'id': '6968553779868435',
            'ext': 'mp4',
            'title': 'ATTN: - Learning new problem-solving skills is hard for...',
            'description': 'md5:2f2fcf93e97ac00244fe64521bbdb0cb',
            'duration': 132.675,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1701975646,
            'upload_date': '20231207',
            'uploader': 'ATTN:',
            'uploader_id': '100064451419378',
            'uploader_url': r're:https?://\w',
            'live_status': 'not_live',
            'concurrent_view_count': int,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
        },
    }, {
        # data.node.comet_sections.content.story.attachments[].styles.attachment.media
        'url': 'https://www.facebook.com/permalink.php?story_fbid=pfbid0fqQuVEQyXRa9Dp4RcaTR14KHU3uULHV1EK7eckNXSH63JMuoALsAvVCJ97zAGitil&id=100068861234290',
        'info_dict': {
            'id': '270103405756416',
            'ext': 'mp4',
            'title': 'Lela Evans - Today Makkovik\'s own Pilot Mandy Smith made...',
            'description': 'md5:cc93a91feb89923303c1f78656791e4d',
            'duration': 394.347,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1703804085,
            'upload_date': '20231228',
            'uploader': 'Lela Evans',
            'uploader_id': r're:pfbid.*',
            'uploader_url': r're:https?://\w',
            'live_status': 'not_live',
            'concurrent_view_count': int,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
        },
    }, {
        'url': 'https://www.facebook.com/story.php?story_fbid=pfbid0Fnzhm8UuzjBYpPMNFzaSpFE9UmLdU4fJN8qTANi1Dmtj5q7DNrL5NERXfsAzDEV7l&id=100073071055552',
        'only_matching': True,
    }, {
        'url': 'https://www.facebook.com/amogood/videos/1618742068337349/?fref=nf',
        'only_matching': True,
    }, {
        # data.mediaset.currMedia.edges[].node
        'url': 'https://www.facebook.com/ChristyClarkForBC/videos/vb.22819070941/10153870694020942/?type=2&theater',
        'info_dict': {
            'id': '10153870694020942',
            'ext': 'mp4',
            'title': 'My playoff challenge to Jim Prentice. Go Canucks Go!',
            'description': 'md5:079134a18ac00b11ec5815fccf75a5a8',
            'duration': 31.197,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1429133517,
            'upload_date': '20150415',
            'uploader': 'Christy Clark',
            'uploader_id': '100045032167189',
            'uploader_url': r're:https?://\w',
            'live_status': 'not_live',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
        },
    }, {
        # data.video.story.attachments[].media
        'url': 'facebook:544765982287235',
        'only_matching': True,
    }, {
        'url': 'https://zh-hk.facebook.com/peoplespower/videos/1135894589806027/',
        'only_matching': True,
    }, {
        'url': 'https://www.facebookwkhpilnemxj7asaniu7vnjjbiltxjqhye3mhbshg7kx5tfyd.onion/video.php?v=274175099429670',
        'only_matching': True,
    }, {
        # data.video.story.attachments[].media
        'url': 'https://www.facebook.com/WatchESLOne/videos/359649331226507/',
        'info_dict': {
            'id': '359649331226507',
            'ext': 'mp4',
            'title': 'Fnatic vs. EG - Group A - Opening Match - ESL One Birmingham Day 1',
            'description': '#ESLOne VoD - Birmingham Finals Day#1 Fnatic vs. @Evil Geniuses',
            'duration': 4524.001,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1527084179,
            'upload_date': '20180523',
            'uploader': 'ESL One Dota 2',
            'uploader_id': '100066514874195',
            'uploader_url': r're:https?://\w',
            'live_status': 'not_live',
            'concurrent_view_count': int,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # data.video.story.attachments[].media
        'url': 'https://www.facebook.com/100033620354545/videos/106560053808006/',
        'info_dict': {
            'id': '106560053808006',
            'ext': 'mp4',
            'title': r're:Josef',
            'description': '',
            'duration': 3.283,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1549275572,
            'upload_date': '20190204',
            'uploader': 'Josef Novak',
            'uploader_id': r're:pfbid.*',
            'uploader_url': r're:https?://\w',
            'live_status': 'not_live',
            'concurrent_view_count': int,
            'comment_count': int,
        },
    }, {
        # data.video.story.attachments[].media
        'url': 'https://www.facebook.com/watch/?v=647537299265662',
        'info_dict': {
            'id': '647537299265662',
            'ext': 'mp4',
            'title': 'Padre enseña a su hijo a cómo bañar un recién nacido junto con su...',
            'description': 'Padre ense\u00f1a a su hijo a c\u00f3mo ba\u00f1ar un reci\u00e9n nacido junto con su gato y se hace viral, mir\u00e1 el video 😍',
            'duration': 136.179,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1605534618,
            'upload_date': '20201116',
            'uploader': 'InfoPico',
            'uploader_id': '100064391811349',
            'uploader_url': r're:https?://\w',
            'live_status': 'not_live',
            'concurrent_view_count': int,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
    }, {
        # data.video.story.attachments[].media
        'url': 'https://m.facebook.com/Alliance.Police.Department/posts/4048563708499330',
        'info_dict': {
            'id': '117576630041613',
            'ext': 'mp4',
            'title': 'Officers Rescue Trapped Motorist from Mahoning River Crash 11-22-20',
            'duration': 101.504,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1606162592,
            'upload_date': '20201123',
            'uploader': 'City of Alliance Police Department',
            'uploader_id': '100064413680392',
            'uploader_url': r're:https?://\w',
            'concurrent_view_count': int,
            'view_count': int,
            'comment_count': int,
        },
        'skip': 'Requires logging in',
    }, {
        'url': 'https://www.facebook.com/groups/ateistiskselskab/permalink/10154930137678856/',
        'only_matching': True,
    }, {
        # data.video.story.attachments[].media
        'url': 'https://www.facebook.com/watch/live/?v=1823658634322275',
        'info_dict': {
            'id': '1823658634322275',
            'ext': 'mp4',
            'title': 'Live Webcam from Corfu - Greece',
            'description': 'md5:84c1af6894ecffe710c79744e4873e85',
            'duration': 14424.199,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1521449766,
            'upload_date': '20180319',
            'uploader': 'SkylineWebcams',
            'uploader_id': '100064307154679',
            'uploader_url': r're:https?://\w',
            'live_status': 'was_live',
            'concurrent_view_count': int,
            'view_count': int,
            'comment_count': int,
        },
        'skip': 'no longer available',
    }, {
        # data.node.comet_sections.content.story.attachments[].style.attachment.all_subattachments.nodes[].media.video_grid_renderer.video
        'url': 'https://www.facebook.com/story.php?story_fbid=5268096689957022&id=100002702286715',
        'info_dict': {
            'id': '669977824610306',
            'ext': 'mp4',
            'title': 'md5:f2666feb05057a09f8b6f542cd7a3eda',
            'description': 'md5:f5775e7245153857caade33e757ceb21',
            'duration': 20.666,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1671780203,
            'upload_date': '20221223',
            'uploader': 'Azura Tan Siow Ling',
            'uploader_id': '100002702286715',
            'uploader_url': r're:https?://\w',
            'live_status': 'not_live',
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
        },
    }, {
        # data.node.comet_sections.content.story.attachments[].styles.attachment.all_subattachments.nodes[].media.video_grid_renderer.video
        'url': 'https://www.facebook.com/hanaryushi/posts/pfbid02Thgaymz9f4QXZ1XogoP4eETpdY2WSy7CLGCMuy3VVQopeet9MHbYR7H9tXYD4UE5l',
        'info_dict': {
            'id': 'pfbid02Thgaymz9f4QXZ1XogoP4eETpdY2WSy7CLGCMuy3VVQopeet9MHbYR7H9tXYD4UE5l',
            'title': 'Hana Ryuushi - “sharing a relationship of having our...',
            'description': 'md5:75d2f9d921f40e90ba3b176f0d827cf7',
            'timestamp': 1706949770,
            'upload_date': '20240203',
            'uploader': 'Hana Ryuushi',
            'uploader_id': '100005357179289',
            'uploader_url': 'https://www.facebook.com/hanaryushi',
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
        },
        'playlist_count': 2,
    }, {
        # data.event.cover_media_renderer.cover_video
        'url': 'https://www.facebook.com/events/464667289575302/',
        'info_dict': {
            'id': '859946639295361',
            'ext': 'mp4',
            'title': 'June Salsa & Bachata Classes On Sundays for Absolute Beginners, Improvers & Advance level.',
            'description': 'Dance event in Hong Kong by Dance With Style on Sunday, June 16 2024',
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'uploader': 'Dance With Style',
            'uploader_id': '100064171651675',
            'uploader_url': r're:https?://\w',
            'live_status': 'not_live',
        },
    }, {
        'url': 'https://m.facebook.com/stories/121668313179875/',
        'only_matching': True,
    }, {
        'url': 'https://www.facebook.com/stories/100944752039935/UzpfSVNDOjY2ODMzMzk5NTUwMzc2MA==/',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        # <iframe> embed
        'url': 'http://www.unique-almeria.com/mini-hollywood.html',
        'md5': 'cba5d8c5021e9340dcefe925255e2c3e',
        'info_dict': {
            'id': '1529066599879',
            'ext': 'mp4',
            'title': 'Facebook video #1529066599879',
        },
        'expected_warnings': ['unable to extract uploader'],
    }, {
        # FIXME: Embed detection
        # <iframe> embed, plugin video
        'url': 'https://www.newsmemory.com/eedition/e-publishing-solutions/2-in-one-app/',
        'md5': 'ae97d4a44f8cc9a8b1a4c03b9ed793af',
        'info_dict': {
            'id': '10155710648695814',
            'ext': 'mp4',
            'title': 'Download the all new and improved Trinidad Express App',
            'concurrent_view_count': int,
            'description': 'md5:4806195c99908e4189b45b1c23bd4f89',
            'duration': 69.408,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1533919195,
            'upload_date': '20180810',
            'uploader': 'Trinidad Express Newspapers',
            'uploader_id': '100064446413648',
            'view_count': int,
        },
        'skip': 'Unsupported URL',
    }, {
        # API embed
        'url': 'https://www.curs.md/ro',
        'info_dict': {
            'id': '334484292523563',
            'ext': 'mp4',
            'title': r're:48\. Retragerea aureliană Criza secolului trei',
            'concurrent_view_count': int,
            'description': 'md5:0ba98567a61c640f9fabf1882235b33d',
            'duration': 8789.891,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1700603114,
            'upload_date': '20231121',
            'uploader': 'Istoria Moldovei',
            'uploader_id': '100063529778592',
            'uploader_url': r're:https?://',
            'live_status': 'not_live',
            'comment_count': int,
            'like_count': int,
            'view_count': int,
        },
        'params': {'extractor_args': {'generic': {'impersonate': ['chrome']}}},
    }]
    _SUPPORTED_PAGLETS_REGEX = r'(?:pagelet_group_mall|permalink_video_pagelet|hyperfeed_story_id_[0-9a-f]+)'
    _api_config = {
        'graphURI': '/api/graphql/',
    }

    def _perform_login(self, username, password):
        # raise error because login with username/password is not working
        self.raise_login_required('Login with username/password is currently not working', method='cookies')

        login_page_req = Request(self._LOGIN_URL)
        self._set_cookie('facebook.com', 'locale', 'en_US')
        login_page = self._download_webpage(login_page_req, None,
                                            note='Downloading login page',
                                            errnote='Unable to download login page')
        lsd = self._search_regex(
            r'<input type="hidden" name="lsd" value="([^"]*)"',
            login_page, 'lsd')
        lgnrnd = self._search_regex(r'name="lgnrnd" value="([^"]*?)"', login_page, 'lgnrnd')

        login_form = {
            'email': username,
            'pass': password,   # "encpass" is needed instead of plain password
            'lsd': lsd,
            'lgnrnd': lgnrnd,
            'next': 'http://facebook.com/home.php',
            'default_persistent': '0',
            'legacy_return': '1',
            'timezone': '-60',
            'trynum': '1',
        }
        request = Request(self._LOGIN_URL, urlencode_postdata(login_form))
        request.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        try:
            login_results = self._download_webpage(request, None,
                                                   note='Logging in', errnote='unable to fetch login page')
            if re.search(r'<form(.*)name="login"(.*)</form>', login_results) is not None:
                error = self._html_search_regex(
                    r'(?s)<div[^>]+class=(["\']).*?login_error_box.*?\1[^>]*><div[^>]*>.*?</div><div[^>]*>(?P<error>.+?)</div>',
                    login_results, 'login error', default=None, group='error')
                if error:
                    raise ExtractorError(f'Unable to login: {error}', expected=True)
                self.report_warning('unable to log in: bad username/password, or exceeded login rate limit (~3/min). Check credentials or wait.')
                return

            fb_dtsg = self._search_regex(
                r'name="fb_dtsg" value="(.+?)"', login_results, 'fb_dtsg', default=None)
            h = self._search_regex(
                r'name="h"\s+(?:\w+="[^"]+"\s+)*?value="([^"]+)"', login_results, 'h', default=None)

            if not fb_dtsg or not h:
                return

            check_form = {
                'fb_dtsg': fb_dtsg,
                'h': h,
                'name_action_selected': 'dont_save',
            }
            check_req = Request(self._CHECKPOINT_URL, urlencode_postdata(check_form))
            check_req.headers['Content-Type'] = 'application/x-www-form-urlencoded'
            check_response = self._download_webpage(check_req, None,
                                                    note='Confirming login')
            if re.search(r'id="checkpointSubmitButton"', check_response) is not None:
                self.report_warning('Unable to confirm login, you have to login in your browser and authorize the login.')
        except network_exceptions as err:
            self.report_warning(f'unable to log in: {err}')
            return

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = (self._VIDEO_PAGE_TEMPLATE % video_id if url.startswith('facebook:')
               else re.sub(r'://(?:[\w-]+\.)?facebook\.com/', '://www.facebook.com/', url))
        webpage = self._download_webpage(url, video_id)

        post_data = re.findall(r'data-sjs>({.*?ScheduledServerJS.*?})</script>', webpage)
        sjs_data = [self._parse_json(j, video_id, fatal=False) for j in post_data]
        cookies = self._get_cookies(url)
        # user passed logged-in cookies or attempted to login
        login_data = cookies.get('c_user') and cookies.get('xs')
        logged_in = False
        if login_data:
            logged_in = get_first(sjs_data, (
                'require', ..., ..., ..., '__bbox', 'define',
                lambda _, v: 'CurrentUserInitialData' in v, ..., 'ACCOUNT_ID'), default='0') != '0'
            if logged_in and (info := get_first(sjs_data, (
                'require', ..., ..., ..., '__bbox', 'require', ..., ..., ..., '__bbox', 'result', 'data',
                (('ufac_client', 'state', (('set_contact_point_state_renderer', 'title'),
                                           ('intro_state_renderer', 'header_title'))),
                 ('epsilon_checkpoint', 'screen', 'title')),
            ))):
                if any(content in info for content in ['days left to appeal', 'suspended your account']):
                    raise ExtractorError('Your account is suspended', expected=True)
                if 'Enter mobile number' == info:
                    raise ExtractorError('Facebook is requiring mobile number confirmation', expected=True)
                if 'your account has been locked' in info:
                    raise ExtractorError('Your account has been locked', expected=True)

        if props := get_first(sjs_data, (
                'require', ..., ..., ..., '__bbox', 'require', ..., ..., ..., (None, (..., ...)), 'rootView',
                lambda _, v: v.get('title') is not None)):
            if not self._cookies_passed:
                self.raise_login_required(method='cookies')
            else:
                msg = re.sub(r'\s{2,}', ' ', join_nonempty('title', 'body', delim='. ', from_dict=props))
                raise ExtractorError(f'This video is not available. Facebook said: {msg}', expected=True)

        if post_data and not re.search(r'"[^"]+[^(feed)]_story[^"]*":', ','.join(post_data)):
            raise ExtractorError('An unknown error occurred. Please try again.', expected=True)

        def truncate_string(s, left, right=0, threshold=0):
            assert left > 3 and right >= 0 and threshold >= 0
            if s is None or len(s) <= max(left + right, threshold):
                return s
            pos = left - 3
            return f'{s[:pos + s[pos:pos + 20].rfind(" ")]}...{s[-right:] if right else ""}'

        def find_json_obj(json_strings, *patterns, obj_in_value=False, get_all=False):
            """
            Find JSON object, in the form of a string, by regular expression
            >>> obj = find_json_obj([json_a, _and_b], regex_a, (regex_b, _or_c), obj_in_value=False, get_all=True)
            @param  json_strings    string/list     JSON string/a list of JSON strings (match all)
                    *patterns       string/tuple    regex patterns (if tuple, return only the 1st matched pattern)
                    obj_in_value    boolean         False:  find the object(s) containing (one of) the pattern(s)
                                                    True :  given pattern(s) of the key(s) to find the
                                                            object(s) in the value of that key(s)
                    get_all         boolean         return the 1st or all of the results of each regex pattern
            @return                 list of tuple   a list of (matching pattern, matched JSON object)
            """
            def find_offset(string, bracket, quotation):
                _BRACKET_MAP = {
                    '{': ([f'{{{quotation}'], ['},', '}]', '}}', f'}}{quotation}'], (1 if obj_in_value else -1)),
                    '}': (['},', '}]', '}}', f'}}{quotation}'], [f'{{{quotation}'], 1),
                }      # ([search pattern], [opposite sign], search direction); search direction: 1 - forward, -1 - backward
                string = re.sub(rf'{{\\{quotation}([^{quotation}]+\\{quotation}:)', rf'{{{quotation}\1 ', string.replace('{}', '[]'))
                count, b_sum, offset = 0, 0, 0
                for y, x in zip(((string[1:] + ' ') if _BRACKET_MAP[bracket][2] > 0 else (' ' + string[:-1]))[::_BRACKET_MAP[bracket][2]],
                                string[::_BRACKET_MAP[bracket][2]]):
                    s = (x + y) if _BRACKET_MAP[bracket][2] > 0 else (y + x)
                    count += (1 if s in _BRACKET_MAP[bracket][0] or s in _BRACKET_MAP[bracket][1] else 0)
                    b_sum += (1 if s in _BRACKET_MAP[bracket][0] else (-1 if s in _BRACKET_MAP[bracket][1] else 0))
                    offset += 1
                    if count > 0 and b_sum >= (0 if obj_in_value else 1):
                        break
                return offset * _BRACKET_MAP[bracket][2]

            for json_str in variadic(json_strings):   # loop all
                if isinstance(json_str, str):
                    # check if json_str is a JSON string and get the quotation mark (either " or ')
                    if quotation := self._search_regex(r'(["\']):\s*[\[{]*\1', json_str, 'quotation', default=None):
                        for patterns_item in patterns:
                            for pattern in variadic(patterns_item):
                                # 'patterns_item' loop - loop each item in *patterns (item can be a str or tuple)
                                found = False
                                if isinstance(pattern, str):
                                    for m in re.finditer(pattern, json_str):    # break according to get_all
                                        if obj_in_value:
                                            i = (lambda x, y: (m.start(m.lastindex or 0) + x - 1) if x > 0
                                                 else ((m.end(m.lastindex or 0) + len(y.group(0)) - 1) if y else None)
                                                 )(m.group(m.lastindex or 0).rfind('{'),
                                                   re.match(r'^\w*(?:":)?:?\s*{', json_str[m.end(m.lastindex or 0):]))
                                        else:
                                            i = m.start(m.lastindex or 0)
                                        if i:
                                            opening = (i + find_offset(
                                                json_str[(i * obj_in_value):(i * (not obj_in_value) - obj_in_value * 2 + 1)],
                                                '{', quotation,
                                            ) - obj_in_value)
                                            closing = i + find_offset(json_str[i:], '}', quotation)
                                            if isinstance(opening, int) and isinstance(closing, int):
                                                found = True
                                                yield (m.group(0), json_str[opening:closing])
                                                if not get_all:
                                                    break
                                    else:   # if this for loop ends with break (i.e. not get_all), else clause is not executed
                                        if found:
                                            break   # break 'patterns_item' loop if found and get_all
                                        continue    # move on to the next 'pattern' (if exists) in 'patterns_item' if not found
                                    break           # break 'patterns_item' loop if found and not get_all
                                if found and isinstance(patterns_item, tuple):
                                    break           # break 'patterns_item' loop if found and patterns_item is a tuple

        def extract_metadata(field=None):
            if webpage_info.get(field) is not None:
                return webpage_info[field]
            elif field is None and webpage_info.get('timestamp') is not None:
                return webpage_info
            # extract data
            description = title = uploader_info = None
            # uploader
            if field == 'uploader':
                for x in find_json_obj(post_data, (rf'actors{Q}:[^}}]+{Q}__isActor{Q}:',
                                                   rf'owner{Q}:[^}}]+{Q}name{Q}:\s*{Q}[^{Q}]'),
                                       get_all=True):
                    if re.search(rf'id{Q}:\s*{Q}(?:{s_id}|{video_id}){Q}', x[1]):
                        uploader_info = traverse_obj(json.loads(x[1]), {
                            'uploader': ((('actors', ...), ('owner', 'owner_as_page'), 'video_owner'),
                                         'name', {str}),
                            'uploader_id': ((('actors', ...), ('owner', 'owner_as_page'), 'video_owner'),
                                            'id', {str}),
                            'uploader_url': ((('actors', ...), ('owner', 'owner_as_page'), 'video_owner'),
                                             ('url', 'profile_url'), {url_or_none}),
                        }, get_all=False)
                        break
                if uploader_info:
                    webpage_info.update(uploader_info)
            # title / description
            if field in ('title', 'description', None):
                for x in find_json_obj(post_data,
                        rf'{Q}message{Q}:(?:(?!{Q}message{Q}:)[^}}])+{Q}text{Q}:\s*{Q}[^{Q}](?:(?!{Q}id{Q}:).)+{Q}id{Q}:',
                        get_all=True):
                    x_dict = json.loads(x[1])
                    for i in [i for i in [s_id, p_id] if i is not None]:
                        if x_dict.get('id') == i:
                            if (description := x_dict['message'] if isinstance(x_dict['message'], str)
                                    else traverse_obj(x_dict, ('message', 'text', {str_or_none}))):
                                if track_title := self._search_regex(rf'({Q}track_title{Q}:\s*{Q}(?:(?:[^{Q}\\]|\\.)*){Q})',
                                                                     x[1], 'track title', default=None):
                                    description += '. ' + json.loads('{' + track_title + '}')['track_title']
                                break
                    if description:
                        break
                description = description or self._html_search_meta(
                    ['description', 'og:description', 'twitter:description'],
                    webpage, 'description', default=None)
                for x in find_json_obj(post_data, rf'title{Q}:\s*[^}}]+{Q}text{Q}:\s*{Q}[^{Q}]', get_all=True):
                    x_dict = json.loads(x[1])
                    if p_id:
                        if (text := traverse_obj(x_dict, ('title', 'text', {str_or_none}))):
                            title = title or (text if x_dict.get('id') == p_id else None)
                            description = description or (text if x_dict.get('id') == s_id else description)
                    if title and description:
                        break
                title = (lambda x: x if x != extract_metadata('uploader') else None
                         )(title
                           or (self._html_search_regex(
                               (r'\s<title>(?P<content>[\s\S]+?)</title>\s',
                                r'<h2\s+[^>]*class="uiHeaderTitle"[^>]*>(?P<content>[^<]*)</h2>',
                                r'(?s)<span class="fbPhotosPhotoCaption".*?id="fbPhotoPageCaption"><span class="hasCaption">(?P<content>.*?)</span>'),
                               re.sub(r'<title>(Facebook(\sLive)?)|(Video)</title>', '', webpage),
                               'title', default='', group='content')
                               or (lambda x: '' if not x or x.group(1) in ('Video', 'Facebook', 'Facebook Live')
                                   else x.group(1).encode().decode('unicode_escape')
                                   )(re.search(rf'{Q}meta{Q}:\s*{{{Q}title{Q}:\s*{Q}((?:[^{Q}\\]|\\.)*){Q}', webpage))
                               or og_title
                               ).split(' | ')[0]
                           or re.sub(r'(\s*\n\s*)', ' ', description or f'Facebook video #{video_id}'))
                webpage_info['title'] = truncate_string(title, 50, threshold=100)
                webpage_info['description'] = description
            # timestamp
            if field in ('timestamp', None):
                for x in find_json_obj(post_data, rf'creation_time{Q}:\s*\d+,', rf'created_time{Q}:\s*\d+,',
                                       rf'publish_time{Q}:\s*\d+,', get_all=True):
                    if re.search(rf'id{Q}:\s*{Q}(?:(?:{s_id})|(?:{p_id})){Q}', x[1]):
                        webpage_info['timestamp'] = json.loads(x[1]).get(re.split(f'{Q}', x[0])[0])
                        break
            # like count
            if field in ('like_count', None):
                like_count = (re.search(rf'localized_name{Q}:\s*{Q}Like{Q}.[^}}]+{Q}reaction_count{Q}:\s*(\d+)}}', feedback_data)
                              or re.search(rf'likers{Q}:\s*{{{Q}count{Q}:\s*(\d+)}}', feedback_data))
                webpage_info['like_count'] = int(like_count.group(1)) if like_count else None
            # comment count
            if field in ('comment_count', None):
                for x in find_json_obj(feedback_data, (rf'comments{Q}:\s*[^}}]+(total_count{Q}:\s*\d+)',
                                                       rf'total_comment_count{Q}:\s*\d+')):
                    webpage_info['comment_count'] = parse_count(traverse_obj(json.loads(x[1]),
                        (('total_count', (..., 'ig_comment_count'), 'total_comment_count'), {str_or_none}), get_all=False))
            # share count
            if field in ('repost_count', None):
                for x in find_json_obj(feedback_data, (rf'share_count{Q}:\s*[^}}]+(count{Q}:\s*"?\d+)',
                                                       rf'share_count(?:_reduced){Q}:\s*"?\d+')):
                    webpage_info['repost_count'] = parse_count(traverse_obj(json.loads(x[1]),
                        (('count', 'share_count_reduced', 'total_count'), {str_or_none}), get_all=False))
            # return data
            return webpage_info.get(field) if field else webpage_info

        og_title = self._og_search_title(webpage, default='').split(' | ')
        if len(og_title) > 1 and re.search(r'\d+\w?\s(?:reactions|shares|views)', og_title[0]):
            og_title.pop(0)
        og_title = re.sub(r'(\s*\n\s*)', ' ', ' | '.join(og_title))
        thumbnail = self._html_search_meta(
            ['og:image', 'twitter:image'], webpage, 'thumbnail', default=None)
        if thumbnail and not re.search(r'\.(?:gif|jpg|png|webp)', thumbnail):
            thumbnail = None

        webpage_info = {
            'thumbnails': [{k: v for k, v in {
                'url': thumbnail,
                'height': int_or_none(self._search_regex(
                                      r'stp=.+_[a-z]\d+x(\d+)&', thumbnail, 'thumbnail height', default=None)),
                'preference': None if 'stp=' in thumbnail else 1,
            }.items() if v is not None}] if url_or_none(thumbnail) else [],
            'view_count': parse_count(self._search_regex(
                (r'\bviewCount\s*:\s*["\']([\d,.]+)', r'video_view_count["\']\s*:\s*(\d+)'),
                webpage, 'view count', default=None)),
        }

        p_id, s_id, linked_url, data, feedback_data = None, None, None, [], ''
        Q = self._search_regex(r'(["\']):\s*[\[{]*\1', (post_data[0] if post_data else ''), 'quotation', default='"')
        for p_data in post_data[:]:
            if (rf'{Q}feed_unit{Q}:' in p_data
                    or rf'{Q}news_feed{Q}:' in p_data
                    or not re.search(rf'{Q}(?:dash_manifest_urls?|message|event_description){Q}:', p_data)):
                # discard useless feed data
                post_data.remove(p_data)
            else:
                if (not s_id or not p_id) and (f'{Q}story{Q}:' in p_data or f'{Q}creation_story{Q}:' in p_data):
                    p_id = p_id or self._search_regex(rf'{Q}(?:post_id|videoId|video_id){Q}:\s*{Q}(\d+){Q}', p_data,
                                                      'post id', default=(video_id if video_id.isnumeric() else None))
                    s_id = s_id or self._search_regex(rf'id{Q}:\s*{Q}(Uzpf[^{Q}]+){Q}', p_data, 'story id', default=None)
                if not data:
                    if re.search(rf'{Q}attachment{Q}:\s*{{{Q}(?:source|web_link){Q}:', p_data):
                        # linked video
                        for x in find_json_obj(p_data, rf'{Q}attachment{Q}:\s*{{{Q}(?:source|web_link){Q}:',
                                               obj_in_value=True):
                            if linked_url := traverse_obj(
                                    json.loads(x[1]), (('web_link', None), 'url', {url_or_none}), get_all=False):
                                url_transparent = '.facebook.com' not in urllib.parse.urlparse(linked_url).netloc
                                data = x[1]
                                break
                    elif f'{Q}dash_manifest_url' in p_data[:p_data.find(f'{Q}comment_list_renderer{Q}:')]:
                        for x in find_json_obj(p_data, rf'{Q}data{Q}:\s*{{', rf'{Q}data{Q}:', obj_in_value=True):
                            if f'{Q}dash_manifest_url' in x[1]:
                                data = x[1]
                                break
            if (not feedback_data
                    and (f'{Q}likers{Q}:' in p_data or f'{Q}Like{Q}}},' in p_data or f'comment_count{Q}:' in p_data)):
                for x in find_json_obj(p_data, rf'fb_reel_react_button{Q}:\s*{{', rf'reaction_count{Q}:\s*{{', rf'feedback{Q}:\s*{{'):
                    if (((s_id or p_id or video_id) in x[1] or (p_id or video_id) in x[1])
                            and webpage.count(json.loads(x[1]).get('id', 'null')) > 1):
                        feedback_data = x[1]
                        break

        if linked_url:
            return self.url_result(linked_url, video_id=video_id, url_transparent=url_transparent,
                                   **{k: v for k, v in (extract_metadata() if url_transparent else {}).items() if v})

        def extract_dash_manifest(vid_data, formats, subtitle, mpd_url=None):
            if dash_manifest := traverse_obj(vid_data, 'dash_manifest_xml_string', 'manifest_xml',
                                             'playlist', 'dash_manifest', expected_type=str):
                fmts, subs = self._parse_mpd_formats_and_subtitles(
                    compat_etree_fromstring(urllib.parse.unquote_plus(dash_manifest)),
                    mpd_url=url_or_none(vid_data.get('dash_manifest_url')) or mpd_url)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitle[0])

        def process_formats(info):
            for f in info['formats']:
                # Downloads with browser's User-Agent are rate limited. Working around
                # with non-browser User-Agent.
                f.setdefault('http_headers', {})['User-Agent'] = 'facebookexternalhit/1.1'
                # Formats larger than ~500MB will return error 403 unless chunk size is regulated
                f.setdefault('downloader_options', {})['http_chunk_size'] = 250 << 20

        if data:
            def parse_graphql_video(video, video_avc=None):
                v_id = video.get('videoId') or video.get('id') or video_id
                formats, captions, subtitles = [], {}, {}
                q = qualities(['sd', 'hd'])
                is_broadcast = traverse_obj(video, ('is_video_broadcast', {bool}))

                # videoDeliveryLegacy formats extraction
                fmt_data = traverse_obj(video, ('videoDeliveryLegacyFields', {dict})) or video
                for key, format_id in (('browser_native_hd_url', 'hd'), ('browser_native_sd_url', 'sd')):
                        # obsoleted: ('playable_url', 'sd'), ('playable_url_quality_hd', 'hd'), ('playable_url_dash', '')
                    if playable_url := fmt_data.get(key):
                        if determine_ext(playable_url) == 'mpd':
                            fmts, subs = self._extract_mpd_formats_and_subtitles(playable_url, video_id, fatal=False)
                            formats.extend(fmts)
                            self._merge_subtitles(subs, target=(captions if is_broadcast else subtitles))
                        else:
                            q = qualities(['sd', 'hd'])
                            formats.append({
                                'format_id': format_id,
                                # sd, hd formats w/o resolution info should be deprioritized below DASH
                                'quality': q(format_id) - 3,
                                'url': playable_url,
                            })
                extract_dash_manifest(fmt_data, formats, [captions if is_broadcast else subtitles])
                if video_avc:
                    extract_dash_manifest(traverse_obj(video_avc, ('videoDeliveryLegacyFields', {dict})),
                                          formats, [captions if is_broadcast else subtitles])

                # videoDeliveryResponse formats extraction
                if fmt_data := traverse_obj(video, ('videoDeliveryResponseFragment', 'videoDeliveryResponseResult')):
                    mpd_urls = traverse_obj(fmt_data, ('dash_manifest_urls', ..., 'manifest_url', {url_or_none}))
                    dash_manifests = traverse_obj(fmt_data, ('dash_manifests', lambda _, v: v['manifest_xml']))
                    for idx, dash_manifest in enumerate(dash_manifests):
                        extract_dash_manifest(dash_manifest, formats, [captions if is_broadcast else subtitles],
                                              mpd_url=traverse_obj(mpd_urls, idx))
                    if not dash_manifests:
                        # Only extract from MPD URLs if the manifests are not already provided
                        for mpd_url in mpd_urls:
                            fmts, subs = self._extract_mpd_formats_and_subtitles(mpd_url, video_id, fatal=False)
                            formats.extend(fmts)
                            self._merge_subtitles(subs, target=(captions if is_broadcast else subtitles))
                    for prog_fmt in traverse_obj(fmt_data, ('progressive_urls', lambda _, v: v['progressive_url'])):
                        format_id = traverse_obj(prog_fmt, ('metadata', 'quality', {str.lower}))
                        formats.append({
                            'format_id': format_id,
                            # sd, hd formats w/o resolution info should be deprioritized below DASH
                            'quality': q(format_id) - 3,
                            'url': prog_fmt['progressive_url'],
                        })
                    for m3u8_url in traverse_obj(fmt_data, ('hls_playlist_urls', ..., 'hls_playlist_url', {url_or_none})):
                        fmts, subs = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, 'mp4',
                                                                              fatal=False, m3u8_id='hls')
                        formats.extend(fmts)
                        self._merge_subtitles(subs, target=(captions if is_broadcast else subtitles))

                # captions/subtitles
                for caption in traverse_obj(video, (
                    'video_available_captions_locales',
                    {lambda x: sorted(x, key=lambda c: c['locale'])},
                    lambda _, v: url_or_none(v['captions_url']),
                )):
                    lang = caption.get('localized_language') or 'und'
                    subs = {
                        'url': caption['captions_url'],
                        'name': format_field(caption, 'localized_country', f'{lang} (%s)', default=lang),
                    }
                    if caption.get('localized_creation_method') or is_broadcast:
                        captions.setdefault(caption['locale'], []).append(subs)
                    else:
                        subtitles.setdefault(caption['locale'], []).append(subs)
                captions_url = traverse_obj(video, ('captions_url', {url_or_none}))
                if captions_url and not captions and not subtitles:
                    locale = self._html_search_meta(
                        ['og:locale', 'twitter:locale'], webpage, 'locale', default='en_US')
                    (captions if is_broadcast else subtitles)[locale] = [{'url': captions_url}]
                # thumbnails
                thumbnails = []
                for url in [uri for uri in [traverse_obj(video, path) for path in [
                    ('thumbnailImage', 'uri'), ('preferred_thumbnail', 'image', 'uri'),
                    ('image', 'uri'), ('previewImage', 'uri'),
                ]] if url_or_none(uri) is not None]:
                    if (re.search(r'\.(?:jpg|png)', url)
                            and not any(url.split('_cat=')[0] in t['url'] for t in thumbnails)):
                        thumbnails.append({k: v for k, v in {
                            'url': url,
                            'height': int_or_none(self._search_regex(
                                                  r'stp=.+_[a-z]\d+x(\d+)&', url, 'thumbnail height', default=None)),
                            'preference': None if 'stp=' in url else 1,
                        }.items() if v is not None})
                # timestamp
                v_timestamp = traverse_obj(video, 'publish_time', 'creation_time', 'created_time', {int_or_none})
                if not v_timestamp and v_id != video_id:
                    for x in find_json_obj(post_data, rf'creation_time{Q}:\s*\d+,', rf'created_time{Q}:\s*\d+,',
                                           rf'publish_time{Q}:\s*\d+,', get_all=True):
                        if re.search(rf'id{Q}:\s*{Q}{v_id}{Q}', x[1]):
                            if v_timestamp := json.loads(x[1]).get(x[0].split(f'{Q}')[0]):
                                break
                # uploader
                if uploader_id := traverse_obj(video, ('owner', 'id', {str_or_none})):
                    if x := list(find_json_obj(data, (rf'id{Q}:\s*{Q}{uploader_id}{Q}[^}}]*{Q}name{Q}:\s*{Q}[^{Q}]',
                                                      rf'{Q}name{Q}:\s*{Q}[^{Q}][^}}]*{Q}id{Q}:\s*{Q}{uploader_id}{Q}'))):
                        if x[0][1]:
                            video['owner'] = merge_dicts(video['owner'], json.loads(x[0][1]))
                elif x := list(find_json_obj(post_data, (rf'(owner{Q}:)[^}}]*{Q}name{Q}:\s*{Q}[^{Q}]'),
                                                         rf'((?!share)\w{{5}}_creator{Q}:)[^}}]*{Q}name{Q}:\s*{Q}[^{Q}]',
                                             obj_in_value=True)):
                    if x[0][1]:
                        video['owner'] = json.loads(x[0][1])
                        uploader_id = traverse_obj(video, ('owner', 'id', {str_or_none}))
                uploader = traverse_obj(video, ('owner', 'name', {str_or_none})) or extract_metadata('uploader')
                # description
                v_desc = traverse_obj(video, ('savable_description', 'text', {str_or_none}))
                if not v_desc and v_id != video_id:
                    if vs_id := traverse_obj(video, (
                            (None, (..., 'video')), 'creation_story', 'id', {str_or_none}), get_all=False):
                        if x := list(find_json_obj(
                                data, rf'{Q}message{Q}:(?:(?!{Q}message{Q}:)[^}}])+{Q}text{Q}:\s*{Q}[^{Q}](?:(?!{Q}id{Q}:).)+{Q}id{Q}:\s*{Q}{vs_id}{Q}')):
                            v_desc = (lambda x: x if x != uploader else None)(json.loads(x[0][1])['message']['text'])
                    # else:
                    #    for x in find_json_obj(data, rf'video{Q}:\s*{{{Q}id{Q}:\s*{Q}{v_id}{Q}', get_all=True):
                    #        if v_desc := traverse_obj(json.loads(x[1]), ('message', 'text', {str_or_none})):
                    #            break

                self._remove_duplicate_formats(formats)
                info = {
                    'id': v_id,
                    'title': (truncate_string(video.get('name'), 50, threshold=100) if video.get('name')
                              else (f"{extract_metadata('title')} - video #{v_id}" if extract_metadata('title')
                                    else (f'{uploader} - video #{v_id}' if uploader else f'Facebook video #{v_id}'))),
                    'description': v_desc or extract_metadata('description'),
                    'thumbnails': thumbnails,
                    'timestamp': v_timestamp or extract_metadata('timestamp'),
                    'uploader': uploader,
                    'uploader_id': uploader_id or webpage_info.get('uploader_id'),
                    'uploader_url': (traverse_obj(video, ('owner', 'url', {url_or_none}))
                                     or (webpage_info.get('uploader_url') if webpage_info.get('uploader') == uploader else None)
                                     or (lambda x: f'https://www.facebook.com/profile.php?id={x}' if x else None
                                         )(uploader_id or webpage_info.get('uploader_id'))),
                    'duration': (float_or_none(video.get('playable_duration_in_ms'), 1000)
                                 or float_or_none(video.get('length_in_second'))),
                    'formats': formats,
                    'automatic_captions': captions,
                    'subtitles': subtitles,
                    'is_live': video.get('is_live_streaming'),
                    'was_live': (video.get('broadcast_status') == 'VOD_READY'),
                    'concurrent_view_count': video.get('liveViewerCount'),
                    'like_count': extract_metadata('like_count'),
                    'comment_count': extract_metadata('comment_count'),
                    'repost_count': extract_metadata('repost_count'),
                    'age_limit': 18 if (re.search(rf'{Q}validator{Q}:\s*{Q}GRAPHIC{Q}', data)
                                        and f'{Q}OverlayWarningScreenViewModel{Q}' in data) else None,
                }
                process_formats(info)
                entries.append(info)

            entries, video_ids, data_avc = [], [], None
            if 'codecs=\\"avc' not in data:
                if 'cookiefile' in self._downloader.params or 'cookiesfrombrowser' in self._downloader.params:
                    if self.cookiejar.filename:
                        self.cookiejar.save()
                    # discard cookies
                    self._downloader.params['cookiefile'], self._downloader.params['cookiesfrombrowser'] = None, None
                    self.cookiejar.clear()
                data_avc = [{x.get('id') or x.get('videoId'): x} for x in [
                    json.loads(x[1]) for x in find_json_obj(
                        self._download_webpage(url, video_id, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.135 Safari/537.36'}),
                        (rf'videoDeliveryLegacyFields{Q}:'), get_all=True)]]
            for idx, x in enumerate(find_json_obj(data, (rf'videoDeliveryLegacyFields{Q}:'), get_all=True)):
                media = json.loads(x[1])
                if (media.get('__typename', 'Video') == 'Video'
                        and not media.get('sticker_image')
                        and media.get('id', f'{video_id}_{idx}') not in video_ids):
                    video_ids.append(media.get('id', f'{video_id}_{idx}'))
                    media_avc = traverse_obj(data_avc, (..., media.get('id'), {dict}), get_all=False)
                    parse_graphql_video(media, media_avc)
                    if media.get('id') == video_id:
                        break

            if len(entries) > 1:
                return self.playlist_result(entries, video_id, **{
                    k: v for k, v in extract_metadata().items() if v})

            video_info = entries[0] if entries else {'id': video_id}
            video_info['title'] = re.sub(r' - video #\d{15,}$', '', video_info.get('title'))
            if webpage_info['thumbnails']:
                if not (any(webpage_info['thumbnails'][0]['url'].split('_cat=')[0] in thumbnail['url']
                            for thumbnail in video_info['thumbnails'])):
                    video_info['thumbnails'].extend(webpage_info['thumbnails'])
            return merge_dicts(video_info, webpage_info)

        # if 'data' not found
        video_data = None

        def extract_video_data(instances):
            video_data = []
            for item in instances:
                if try_get(item, lambda x: x[1][0]) == 'VideoConfig':
                    video_item = item[2][0]
                    if video_item.get('video_id'):
                        video_data.append(video_item['videoData'])
            return video_data

        def extract_from_jsmods_instances(js_data):
            if js_data:
                return extract_video_data(try_get(
                    js_data, lambda x: x['jsmods']['instances'], list) or [])

        if server_js_data := self._parse_json(self._search_regex(
                [r'handleServerJS\(({.+})(?:\);|,")', r'\bs\.handle\(({.+?})\);'],
                webpage, 'server js data', default='{}'), video_id, fatal=False):
            video_data = extract_video_data(server_js_data.get('instances', []))

        if not video_data:
            if server_js_data := self._parse_json(self._search_regex([
                r'bigPipe\.onPageletArrive\(({.+?})\)\s*;\s*}\s*\)\s*,\s*["\']onPageletArrive\s+' + self._SUPPORTED_PAGLETS_REGEX,
                rf'bigPipe\.onPageletArrive\(({{.*?id\s*:\s*"{self._SUPPORTED_PAGLETS_REGEX}".*?}})\);',
            ], webpage, 'js data', default='{}'), video_id, js_to_json, False):
                video_data = extract_from_jsmods_instances(server_js_data)

        if not video_data and False:    # skipped because not working
            # Video info not in first request, do a secondary request using
            # tahoe player specific URL
            tahoe_data = self._download_webpage(
                self._VIDEO_PAGE_TAHOE_TEMPLATE % p_id, video_id,
                fatal=False,
                expected_status=404,
                data=urlencode_postdata({
                    '__a': 1,
                    '__pc': self._search_regex(
                        r'pkg_cohort["\']\s*:\s*["\'](.+?)["\']', webpage,
                        'pkg cohort', default='PHASED:DEFAULT'),
                    '__rev': self._search_regex(
                        r'client_revision["\']\s*:\s*(\d+),', webpage,
                        'client revision', default='3944515'),
                    'fb_dtsg': self._search_regex(
                        r'"DTSGInitialData"\s*,\s*\[\]\s*,\s*{\s*"token"\s*:\s*"([^"]+)"',
                        webpage, 'dtsg token', default=''),
                }),
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                })
            if tahoe_data:
                tahoe_js_data = self._parse_json(
                    self._search_regex(
                        r'for\s+\(\s*;\s*;\s*\)\s*;(.+)', tahoe_data,
                        'tahoe js data', default='{}'),
                    video_id, fatal=False)
                video_data = extract_from_jsmods_instances(tahoe_js_data)

        if not video_data:
            m_msg = re.search(r'class="[^"]*uiInterstitialContent[^"]*"><div>(.*?)</div>', webpage)
            if m_msg is not None:
                raise ExtractorError(
                    f'The video is not available, Facebook said: "{m_msg.group(1)}"',
                    expected=True)
            elif any(p in webpage for p in (
                    '>You must log in to continue',
                    'id="login_form"',
                    'id="loginbutton"')):
                self.raise_login_required(method='cookies')
            elif not login_data:
                self.raise_login_required('No video formats found', method='cookies')
            elif not logged_in:
                self.raise_login_required('Failed to login with provided data', method='cookies')
            self.raise_no_formats('No video formats found!')

        if len(video_data) > 1:
            entries = []
            for v in video_data:
                video_url = v[0].get('video_url')
                if not video_url:
                    continue
                entries.append(self.url_result(urljoin(
                    url, video_url), self.ie_key(), v[0].get('video_id')))
            return self.playlist_result(entries, video_id)

        video_data = video_data[0]

        formats = []
        subtitles = {}
        for f in video_data:
            format_id = f['stream_type']
            if f and isinstance(f, dict):
                f = [f]
            if not f or not isinstance(f, list):
                continue
            for quality in ('sd', 'hd'):
                for src_type in ('src', 'src_no_ratelimit'):
                    src = f[0].get(f'{quality}_{src_type}')
                    if src:
                        # sd, hd formats w/o resolution info should be deprioritized below DASH
                        # TODO: investigate if progressive or src formats still exist
                        preference = -10 if format_id == 'progressive' else -3
                        if quality == 'hd':
                            preference += 1
                        formats.append({
                            'format_id': f'{format_id}_{quality}_{src_type}',
                            'url': src,
                            'quality': preference,
                            'height': 720 if quality == 'hd' else None,
                        })
            extract_dash_manifest(f[0], formats, [subtitles])
            subtitles_src = f[0].get('subtitles_src')
            if subtitles_src:
                subtitles.setdefault('en', []).append({'url': subtitles_src})

        info_dict = {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
        }
        process_formats(info_dict)
        info_dict.update(extract_metadata())

        return info_dict


class FacebookPluginsVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[\w-]+\.)?facebook\.com/plugins/video\.php\?.*?\bhref=(?P<id>https.+)'

    _TESTS = [{
        'url': 'https://www.facebook.com/plugins/video.php?href=https%3A%2F%2Fwww.facebook.com%2Fgov.sg%2Fvideos%2F10154383743583686%2F&show_text=0&width=560',
        'info_dict': {
            'id': '10154383743583686',
            'ext': 'mp4',
            'title': 'What to do during the haze?',
            'description': 'md5:81839c0979803a014b20798df255ed0b',
            'duration': 65.087,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1472184808,
            'upload_date': '20160826',
            'uploader': 'gov.sg',
            'uploader_id': '100064718678925',
            'uploader_url': r're:https?://\w',
            'view_count': int,
            'concurrent_view_count': int,
            'live_status': 'not_live',
            'like_count': int,
            'comment_count': int,
        },
        'add_ie': [FacebookIE.ie_key()],
    }, {
        'url': 'https://www.facebook.com/plugins/video.php?href=https%3A%2F%2Fwww.facebook.com%2Fvideo.php%3Fv%3D10204634152394104',
        'only_matching': True,
    }, {
        'url': 'https://www.facebook.com/plugins/video.php?href=https://www.facebook.com/gov.sg/videos/10154383743583686/&show_text=0&width=560',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self.url_result(
            urllib.parse.unquote(self._match_id(url)),
            FacebookIE.ie_key())


class FacebookRedirectURLIE(InfoExtractor):
    IE_DESC = False  # Do not list
    _VALID_URL = r'https?://(?:[\w-]+\.)?facebook\.com/flx/warn[/?]'
    _TESTS = [{
        'url': 'https://www.facebook.com/flx/warn/?h=TAQHsoToz&u=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DpO8h3EaFRdo&s=1',
        'info_dict': {
            'id': 'pO8h3EaFRdo',
            'ext': 'mp4',
            'title': 'Tripeo Boiler Room x Dekmantel Festival DJ Set',
            'description': 'md5:2d713ccbb45b686a1888397b2c77ca6b',
            'channel_id': 'UCGBpxWJr9FNOcFYA5GkKrMg',
            'playable_in_embed': True,
            'categories': ['Music'],
            'channel': 'Boiler Room',
            'uploader_id': '@boilerroom',
            'uploader': 'Boiler Room',
            'tags': 'count:11',
            'duration': 3332,
            'live_status': 'not_live',
            'thumbnail': 'https://i.ytimg.com/vi/pO8h3EaFRdo/maxresdefault.jpg',
            'channel_url': 'https://www.youtube.com/channel/UCGBpxWJr9FNOcFYA5GkKrMg',
            'availability': 'public',
            'uploader_url': r're:https?://\w',
            'upload_date': '20150917',
            'timestamp': 1442489450,
            'age_limit': 0,
            'view_count': int,
            'like_count': int,
            'heatmap': 'count:100',
            'channel_is_verified': True,
            'channel_follower_count': int,
            'comment_count': int,
            'media_type': 'video',
        },
        'add_ie': ['Youtube'],
        'params': {'skip_download': 'Youtube'},
    }]

    def _real_extract(self, url):
        redirect_url = url_or_none(parse_qs(url).get('u', [None])[-1])
        if not redirect_url:
            raise ExtractorError('Invalid facebook redirect URL', expected=True)
        return self.url_result(redirect_url)


class FacebookReelIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[\w-]+\.)?facebook\.com/reel/(?P<id>\d+)'
    IE_NAME = 'facebook:reel'

    _TESTS = [{
        'url': 'https://www.facebook.com/reel/1195289147628387',
        'info_dict': {
            'id': '1195289147628387',
            'ext': 'mp4',
            'title': 're:When your trying to help your partner out with an arrest and',
            'description': 're:When your trying to help your partner out with an arrest and',
            'duration': 9.579,
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1637502609,
            'upload_date': '20211121',
            'uploader': 'Beast Camp Training',
            'uploader_id': '100040874179269',
            'uploader_url': r're:https?://\w',
            'live_status': 'not_live',
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            f'https://www.facebook.com/watch/?v={video_id}', FacebookIE, video_id)


class FacebookAdsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[\w-]+\.)?facebook\.com/ads/library/?\?(?:[^#]+&)?id=(?P<id>\d+)'
    IE_NAME = 'facebook:ads'

    _TESTS = [{
        'url': 'https://www.facebook.com/ads/library/?id=1315864699599579',
        'info_dict': {
            'id': '1315864699599579',
            'ext': 'mp4',
            'title': 'video by Kandao',
            'description': 'md5:598dbd8efd04e088d9f0bab3c8138d74',
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1753354249,
            'upload_date': '20250724',
            'uploader': 'Kandao',
            'uploader_id': '774114102743284',
            'uploader_url': r're:https?://\w',
            'like_count': int,
        },
    }, {
        'url': 'https://www.facebook.com/ads/library/?id=736210102215641',
        'info_dict': {
            'id': '736210102215641',
            'ext': 'mp4',
            'title': 'video by mat.nawrocki',
            'description': 'md5:7c7dae197dc1d1c952e259cf27044080',
            'thumbnail': r're:https?://scontent\.[\w-]+\.fna\.fbcdn\.net/.+',
            'timestamp': 1751698356,
            'upload_date': '20250705',
            'uploader': 'mat.nawrocki',
            'uploader_id': '148586968341456',
            'uploader_url': r're:https?://\w',
            'like_count': int,
        },
    }, {
        'url': 'https://www.facebook.com/ads/library/?id=689836030134727',
        'info_dict': {
            'id': '689836030134727',
            'title': 'Eataly : un lieu où l’on mange, découvre et apprend l’Italie !',
            'timestamp': 1743518181,
            'upload_date': '20250401',
            'uploader': 'Eataly Paris Marais',
            'uploader_id': '2086668958314152',
            'uploader_url': r're:https?://\w',
            'like_count': int,
        },
        'playlist_count': 2,
    }, {
        'url': 'https://es-la.facebook.com/ads/library/?id=901230958115569',
        'only_matching': True,
    }, {
        'url': 'https://m.facebook.com/ads/library/?id=901230958115569',
        'only_matching': True,
    }]

    _FORMATS_MAP = {
        'watermarked_video_sd_url': ('sd-wmk', 'SD, watermarked'),
        'video_sd_url': ('sd', None),
        'watermarked_video_hd_url': ('hd-wmk', 'HD, watermarked'),
        'video_hd_url': ('hd', None),
    }

    def _extract_formats(self, video_dict):
        formats = []
        for format_key, format_url in traverse_obj(video_dict, (
            {dict.items}, lambda _, v: v[0] in self._FORMATS_MAP and url_or_none(v[1]),
        )):
            formats.append({
                'format_id': self._FORMATS_MAP[format_key][0],
                'format_note': self._FORMATS_MAP[format_key][1],
                'url': format_url,
                'ext': 'mp4',
                'quality': qualities(tuple(self._FORMATS_MAP))(format_key),
            })
        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        if post_data := traverse_obj(
                re.findall(r'data-sjs>({.*?ScheduledServerJS.*?})</script>', webpage), (..., {json.loads})):
            data = get_first(post_data, (
                'require', ..., ..., ..., '__bbox', 'require', ..., ..., ...,
                'entryPointRoot', 'otherProps', 'deeplinkAdCard', 'snapshot', {dict}))
        elif post_data := traverse_obj(
                re.findall(r's\.handle\(({.*})\);requireLazy\(', webpage), (..., {json.loads})):
            data = get_first(post_data, (
                'require', ..., ..., ..., 'props', 'deeplinkAdCard', 'snapshot', {dict}))
        if not data:
            raise ExtractorError('Unable to extract ad data')

        title = data.get('title')
        if not title or title == '{{product.name}}':
            title = join_nonempty('display_format', 'page_name', delim=' by ', from_dict=data)
        markup_id = traverse_obj(data, ('body', '__m', {str}))
        markup = traverse_obj(post_data, (
            ..., 'require', ..., ..., ..., '__bbox', 'markup', lambda _, v: v[0].startswith(markup_id),
            ..., '__html', {clean_html}, {lambda x: not x.startswith('{{product.') and x}, any))

        info_dict = merge_dicts({
            'title': title,
            'description': markup or None,
        }, traverse_obj(data, {
            'description': ('link_description', {lambda x: x if not x.startswith('{{product.') else None}),
            'uploader': ('page_name', {str}),
            'uploader_id': ('page_id', {str_or_none}),
            'uploader_url': ('page_profile_uri', {url_or_none}),
            'timestamp': ('creation_time', {int_or_none}),
            'like_count': ('page_like_count', {int_or_none}),
        }))

        entries = []
        for idx, entry in enumerate(traverse_obj(
            data, (('videos', 'cards'), lambda _, v: any(url_or_none(v.get(f)) for f in self._FORMATS_MAP))), 1,
        ):
            entries.append({
                'id': f'{video_id}_{idx}',
                'title': entry.get('title') or title,
                'description': traverse_obj(entry, 'body', 'link_description') or info_dict.get('description'),
                'thumbnail': url_or_none(entry.get('video_preview_image_url')),
                'formats': self._extract_formats(entry),
            })

        if len(entries) == 1:
            info_dict.update(entries[0])

        elif len(entries) > 1:
            info_dict.update({
                'title': entries[0]['title'],
                'entries': entries,
                '_type': 'playlist',
            })

        info_dict['id'] = video_id

        return info_dict
