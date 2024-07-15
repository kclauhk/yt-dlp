import datetime
import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    merge_dicts,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class BlueyIE(InfoExtractor):
    _VALID_URL = r'https?://www\.bluey\.tv/watch/(?:.+[/])?(?P<id>[^/]+)/?$'
    _TESTS = [{
        # Episode (YouTube embeded: https://youtu.be/u6D2ucvSas0)
        'url': 'https://www.bluey.tv/watch/season-1/mums-and-dads/',
        'info_dict': {
            'id': 'u6D2ucvSas0',
            'ext': 'mp4',
            'title': 'Mums and Dads',
            'description': 'md5:e215cd5c6d6ec050a354d2b06ad6fc9d',
            'thumbnail': 'https://www.bluey.tv/wp-content/uploads/2023/08/ABTI325R50_MUMS_AND_DADS_Image_00.jpg',
            'timestamp': 1591362032,
            'upload_date': '20230920',
            'uploader': 'Official Bluey TV',
            'uploader_id': '@BlueyOfficialChannel',
            'uploader_url': 'https://www.youtube.com/@BlueyOfficialChannel',
            'channel': 'Bluey - Official Channel',
            'channel_id': 'UCVzLLZkDuFGAE2BGdBuBNBg',
            'channel_url': 'https://www.youtube.com/channel/UCVzLLZkDuFGAE2BGdBuBNBg',
            'channel_follower_count': int,
            'channel_is_verified': True,
            'duration': 118,
            'view_count': int,
            'like_count': int,
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Film & Animation'],
            'tags': 'count:18',
            'heatmap': 'count:100',
            'live_status': 'not_live',
            'playable_in_embed': True,
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 33',
            'episode_number': 33,
        },
    }, {
        # Episode with trailer video
        'url': 'https://www.bluey.tv/watch/season-3/the-sign/',
        'info_dict': {
            'id': 'the-sign',
            'title': 'The Sign',
            'description': 'md5:6e9b01b32f35bdcf33160c86a15080f7',
            'thumbnail': 'https://www.bluey.tv/wp-content/uploads/2024/02/Sign-Sq.png',
            'upload_date': '20240226',
            'uploader': 'Official Bluey TV',
            'season': 'Season 3',
            'season_number': 3,
            'episode': 'Episode 49',
            'episode_number': 49,
        },
        'playlist_count': 2,
    }, {
        # Minisode (Brightcove)
        'url': 'https://www.bluey.tv/watch/minisodes/animals/',
        'info_dict': {
            'id': 'animals',
            'ext': 'mp4',
            'title': 'Animals',
            'description': 'Mum is playing the animal game on Bingo\'s back.',
            'thumbnail': 'https://cf-images.us-east-1.prod.boltdns.net/v1/jit/6041795457001/b8000e79-49d6-4732-88be-09fb0d484a98/main/1280x720/11s413ms/match/image.jpg',
            'upload_date': '20240703',
            'uploader': 'Official Bluey TV',
            'tags': [],
            'episode': 'Episode 7',
            'episode_number': 7,
        },
    }, {
        # Book-read (YouTube embeded: https://youtu.be/NbLxoLyPGyc)
        'url': 'https://www.bluey.tv/watch/bluey-book-reads/charades-2/',
        'info_dict': {
            'id': 'NbLxoLyPGyc',
            'ext': 'mp4',
            'title': 'Charades',
            'description': 'Jenna Fischer reads \'Charades\'',
            'thumbnail': 'https://www.bluey.tv/wp-content/uploads/2024/02/BOOK-READS-1920x1080_CHARADES.png',
            'timestamp': 1713538806,
            'release_date': '20240419',
            'release_timestamp': 1713538806,
            'upload_date': '20240212',
            'uploader': 'Official Bluey TV',
            'uploader_id': '@BlueyOfficialChannel',
            'uploader_url': 'https://www.youtube.com/@BlueyOfficialChannel',
            'channel': 'Bluey - Official Channel',
            'channel_id': 'UCVzLLZkDuFGAE2BGdBuBNBg',
            'channel_url': 'https://www.youtube.com/channel/UCVzLLZkDuFGAE2BGdBuBNBg',
            'channel_follower_count': int,
            'channel_is_verified': True,
            'duration': 280,
            'view_count': int,
            'like_count': int,
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Film & Animation'],
            'heatmap': 'count:100',
            'live_status': 'not_live',
            'playable_in_embed': True,
            'tags': 'count:28',
        },
    }, {
        # Bonus-bit (YouTube embeded: https://youtu.be/UUkb_b5UEE0)
        'url': 'https://www.bluey.tv/watch/bonus-bits/tea-party/',
        'info_dict': {
            'id': 'UUkb_b5UEE0',
            'ext': 'mp4',
            'title': 'Tea Party',
            'description': 'Bluey and Honey invite Honey\'s mum and dad to a tea party.',
            'thumbnail': 'https://www.bluey.tv/wp-content/uploads/2021/03/Bluey_Tea_Party_001.jpg',
            'timestamp': 1614960018,
            'upload_date': '20220524',
            'uploader': 'Official Bluey TV',
            'uploader_id': '@BlueyOfficialChannel',
            'uploader_url': 'https://www.youtube.com/@BlueyOfficialChannel',
            'channel': 'Bluey - Official Channel',
            'channel_id': 'UCVzLLZkDuFGAE2BGdBuBNBg',
            'channel_url': 'https://www.youtube.com/channel/UCVzLLZkDuFGAE2BGdBuBNBg',
            'channel_follower_count': int,
            'channel_is_verified': True,
            'duration': 95,
            'view_count': int,
            'like_count': int,
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Film & Animation'],
            'heatmap': 'count:100',
            'live_status': 'not_live',
            'playable_in_embed': True,
            'tags': 'count:24',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        def brightcove_api(brightcove_id, video_id):
            headers = {'Accept': 'application/json;pk=BCpkADawqM0-e9kbtiYMtk9IxVZUWQ1X3DfbKGkMTtgzX-8zRbWKYj31aVgMTPXxCK3Uy_J4wYE8mXuYHlLUhu47Tsco9l6H_-3_BJKL10ip7fnY8tUiCotYIoaMcOTeqCwM9Vn2trMyy3HM'}
            if data := self._download_json(f'https://edge.api.brightcove.com/playback/v1/accounts/6041795457001/videos/{brightcove_id}',
                                           video_id, headers=headers, fatal=False):
                formats, subtitles = [], {}
                for source in data.get('sources'):
                    if source.get('type') == 'application/x-mpegURL' and source.get('src'):
                        fmts, subs = self._extract_m3u8_formats_and_subtitles(
                            source['src'], video_id, 'mp4', m3u8_id='hls', fatal=False)
                        for idx, f in enumerate(fmts):
                            fmts[idx]['format_id'] = f['format_id'].replace(' ', '').replace(')', '') + '-' + source['src'].split(':')[0]
                        formats.extend(fmts)
                        self._merge_subtitles(subs, target=subtitles)
                    elif source.get('type') == 'application/dash+xml' and source.get('src'):
                        fmts, subs = self._extract_mpd_formats_and_subtitles(
                            source['src'], video_id, mpd_id='dash', fatal=False)
                        for idx, f in enumerate(fmts):
                            fmts[idx]['format_id'] = f['format_id'] + '-' + source['src'].split(':')[0]
                        formats.extend(fmts)
                        self._merge_subtitles(subs, target=subtitles)
                return {
                    **traverse_obj(data, {
                        'id': ('id', {lambda x: x or video_id}),
                        'title': (('name', 'description'), {str_or_none}),
                        'description': (('long_description', 'description'), {str_or_none}),
                        'thumbnail': (('poster', 'thumbnail'), {url_or_none}),
                        'tags': ('tags', {list}),
                        'upload_date': (('published_at', 'created_at'),
                                        {lambda x: x[:10].replace('-', '') if x else None}),
                    }, get_all=False),
                    'formats': formats,
                    'subtitles': subtitles,
                }
            else:
                return {}

        entries = []
        if player_data := re.findall(r'fe-(\w+)-player" data-props="({[^"]+?})"', webpage):
            for data in player_data:
                if video_data := self._parse_json(clean_html(data[1]), video_id):
                    if data[0] == 'media':
                        if video_data.get('type') == 'brightcove' and video_data.get('brightcoveId'):
                            entries.append(brightcove_api(video_data['brightcoveId'], video_id))
                        elif video_data.get('type') == 'youtube' and video_data.get('youtubeId'):
                            entries.append(self.url_result(video_data['youtubeId'], url_transparent=True))
                    elif data[0] == 'video':
                        entries.append(self.url_result(video_data.get('url'), url_transparent=True))

        if json_ld := list(self._yield_json_ld(webpage, video_id)):
            info = {
                'id': video_id,
                **traverse_obj(json_ld[-1], {
                    'title': (('containsSeason', '@graph'), 0, (('episode', 'name'), 'name'),
                              {lambda x: x.split(' | ')[-1] if x else None}),
                    'description': (('containsSeason', '@graph'), 0,
                                    (('episode', 'description'), 'description'), {str_or_none}),
                    'thumbnail': (('containsSeason', '@graph'), 0,
                                  (('episode', 'image'), 'thumbnailUrl'), {url_or_none}),
                    'season': ('containsSeason', 0, 'name',
                               {lambda x: x if re.match(r'Season \d+$', x) else None}),
                    'season_number': ('containsSeason', 0, 'name',
                                      {lambda x: int(x.replace('Season ', '')) if re.match(r'Season \d+$', x) else None}),
                    'episode': ('containsSeason', 0, 'episode', 'episodeNumber',
                                {lambda x: f'Episode {x}' if x else None}),
                    'episode_number': ('containsSeason', 0, 'episode', 'episodeNumber', {int_or_none}),
                }, get_all=False),
                'upload_date': traverse_obj(json_ld[0], ('@graph', 0, 'datePublished',
                                            {lambda x: x[:10].replace('-', '') if x else None}), get_all=False),
            }
        else:
            title = self._og_search_title(webpage)
            published_time = self._html_search_meta('article:published_time', webpage)
            info = {
                'id': video_id,
                'title': title.split(' | ')[-1],
                'description': self._og_search_description(webpage),
                'thumbnail': self._og_search_thumbnail(webpage),
                'upload_date': (datetime.datetime.strptime(published_time.split(' ')[0], '%m/%d/%y').strftime('%Y%m%d')
                                if published_time else None),
            }
            if season_number := self._search_regex(r' Season (\d+)', title, 'season_number', default=None):
                info['season'] = f'Season {season_number}'
                info['season_number'] = int(season_number)
            if episode_number := self._search_regex(r' Episode (\d+)', title, 'episode_number', default=None):
                info['episode'] = f'Episode {episode_number}'
                info['episode_number'] = int(episode_number)
        info['uploader'] = self._html_search_meta('article:author', webpage)

        if len(entries) > 1:
            return self.playlist_result(entries, video_id, **{
                k: v for k, v in info.items() if v})
        else:
            if entries[0].get('thumbnail'):
                info['thumbnail'] = None
            return merge_dicts(info, entries[0])
