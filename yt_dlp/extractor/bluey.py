import re

from .common import InfoExtractor
from .youtube import YoutubeIE
from .youtube.jsc._director import initialize_jsc_director
from .youtube.pot._director import initialize_pot_director
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    join_nonempty,
    merge_dicts,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class BlueyIE(InfoExtractor):
    _VALID_URL = r'https?://www\.bluey\.tv/(?:.+/)?(?P<id>[^/]+)/?$'
    _TESTS = [{
        # Episode (YouTube embeded: https://youtu.be/u6D2ucvSas0)
        'url': 'https://www.bluey.tv/watch/season-1/mums-and-dads/',
        'info_dict': {
            'id': 'mums-and-dads',
            'ext': 'mp4',
            'title': 'Mums and Dads',
            'description': r're:When Indy and Rusty play Mums and Dads, they can’t agree on who should go to work, so they part company',
            'thumbnail': 'https://www.bluey.tv/wp-content/uploads/2023/07/ABTI325R50_MUMS_AND_DADS_Image_15-scaled.jpg',
            'timestamp': 1591362032,
            'upload_date': '20200605',
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
            'media_type': 'video',
        },
        'params': {'extractor_args': {'youtube': {'player_client': ['android_sdkless']}}},
    }, {
        # Episode with trailer video
        'url': 'https://www.bluey.tv/watch/season-3/the-sign/',
        'info_dict': {
            'id': 'the-sign',
            'title': 'The Sign',
            'description': r're:The 28 minute Bluey special.',
            'thumbnail': 'https://www.bluey.tv/wp-content/uploads/2024/02/Sign-Sq.png',
            'uploader': 'Official Bluey TV',
            'season': 'Season 3',
            'season_number': 3,
            'episode': 'Episode 49',
            'episode_number': 49,
        },
        'playlist_count': 2,
        'params': {'extractor_args': {'youtube': {'player_client': ['android_sdkless']}}},
    }, {
        # Minisode (Brightcove)
        'url': 'https://www.bluey.tv/watch/minisodes/robo-bingo/',
        'info_dict': {
            'id': 'robo-bingo',
            'ext': 'mp4',
            'title': 'Robo Bingo',
            'description': 'Mum attempts to get Robo Bingo to clean its teeth with very specific instructions.',
            'thumbnail': 'https://cf-images.us-east-1.prod.boltdns.net/v1/jit/6041795457001/0412a8e4-be18-45ae-b721-0fe483d07143/main/1280x720/9s994ms/match/image.jpg',
            'upload_date': '20241206',
            'uploader': 'Official Bluey TV',
            'tags': [],
            'episode': 'Episode 16',
            'episode_number': 16,
            'duration': 19989,
        },
        'params': {'extractor_args': {'youtube': {'player_client': ['android_sdkless']}}},
    }, {
        # Book-read (YouTube embeded: https://youtu.be/NbLxoLyPGyc)
        'url': 'https://www.bluey.tv/watch/bluey-book-reads/charades-2/',
        'info_dict': {
            'id': 'charades-2',
            'ext': 'mp4',
            'title': '\'Charades\' with Jenna Fischer',
            'description': r're:Jenna Fischer reads \'Charades\'',
            'thumbnail': 'https://www.bluey.tv/wp-content/uploads/2024/02/AVSA067W_BlueyBookReads_S01_E06_Charades_TitlePromo_16x9.png',
            'timestamp': 1713538806,
            'release_date': '20240419',
            'release_timestamp': 1713538806,
            'upload_date': '20240419',
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
            'media_type': 'video',
        },
        'params': {'extractor_args': {'youtube': {'player_client': ['android_sdkless']}}},
    }, {
        # Bonus-bit (YouTube embeded: https://youtu.be/UUkb_b5UEE0)
        'url': 'https://www.bluey.tv/watch/bonus-bits/tea-party/',
        'info_dict': {
            'id': 'tea-party',
            'ext': 'mp4',
            'title': 'Tea Party',
            'description': r're:Bluey and Honey invite Honey\'s mum and dad to a tea party.',
            'thumbnail': 'https://www.bluey.tv/wp-content/uploads/2021/03/Bluey_Tea_Party_001.jpg',
            'timestamp': 1614960018,
            'upload_date': '20210305',
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
            'media_type': 'video',
        },
        'params': {'extractor_args': {'youtube': {'player_client': ['android_sdkless']}}},
    }, {
        # Characters (YouTube embeded: https://youtu.be/HlOIzz-GIxk)
        'url': 'https://www.bluey.tv/characters/bluey/',
        'info_dict': {
            'id': 'bluey',
            'ext': 'mp4',
            'title': 'BLUEY\'S HIGHLIGHTS',
            'description': r're:Bluey is a blue heeler pup who loves to make up and play fun and imaginative games with her family and friends.',
            'thumbnail': r're:https?://.*\.jpg$',
            'timestamp': 1665759612,
            'upload_date': '20221014',
            'uploader': 'Official Bluey TV',
            'uploader_id': '@BlueyOfficialChannel',
            'uploader_url': 'https://www.youtube.com/@BlueyOfficialChannel',
            'channel': 'Bluey - Official Channel',
            'channel_id': 'UCVzLLZkDuFGAE2BGdBuBNBg',
            'channel_url': 'https://www.youtube.com/channel/UCVzLLZkDuFGAE2BGdBuBNBg',
            'channel_follower_count': int,
            'channel_is_verified': True,
            'duration': 604,
            'view_count': int,
            'like_count': int,
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Film & Animation'],
            'live_status': 'not_live',
            'playable_in_embed': True,
            'tags': 'count:24',
            'media_type': 'video',
        },
        'params': {'extractor_args': {'youtube': {'player_client': ['android_sdkless']}}},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        def extract_brightcove(brightcove_id, video_id):
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
                        'id': ('id', {str}),
                        'title': (('name', 'description'), {str_or_none}),
                        'description': (('long_description', 'description'), {str_or_none}),
                        'thumbnails': (('poster', 'thumbnail'), {lambda x: [{
                            'url': x,
                            'preference': 0,
                        }] if url_or_none(x) else []}),
                        'tags': ('tags', {list}),
                        'upload_date': (('published_at', 'created_at'),
                                        {lambda x: x[:10].replace('-', '') if x else None}),
                        'duration': ('duration', {int_or_none}),
                    }, get_all=False),
                    'formats': formats,
                    'subtitles': subtitles,
                }
            else:
                return None

        def extract_youtube(url):
            youtube = YoutubeIE()
            youtube._downloader = self._downloader
            youtube._jsc_director = initialize_jsc_director(youtube)
            youtube._pot_director = initialize_pot_director(youtube)
            try:
                return youtube._real_extract(url)
            except ExtractorError as e:
                youtube.to_screen(e)

        entries, player_poster, featured_image, player_title = [], [], None, None
        if player_data := re.findall(r'fe-(\w+)-player" data-props="({[^"]+?})"', webpage):
            for idx, data in enumerate(player_data):
                if video_data := self._parse_json(clean_html(data[1]), video_id):
                    player_title = traverse_obj(video_data, ('title', {lambda x: x if x != 'Watch the trailer' else None}))
                    player_poster.append(traverse_obj(video_data, {
                        'url': (('featuredImage', 'posterImage'), {url_or_none}),
                    }, get_all=False, default=None))
                    if poster := video_data.get('poster'):
                        if sizes := poster.get('sizes'):
                            for key in [k for k, v in sizes.items() if str(v)[:4] == 'http']:
                                player_poster.append({
                                    'url': url_or_none(sizes[key]),
                                    'width': int_or_none(sizes[f'{key}-width']),
                                    'height': int_or_none(sizes[f'{key}-height']),
                                })
                        player_poster.append(traverse_obj(poster, {
                            'url': ('url', {url_or_none}),
                            'width': ('width', {int_or_none}),
                            'height': ('height', {int_or_none}),
                        }))
                    if idx == 0:
                        featured_image = traverse_obj(video_data, (('featuredImage', 'posterImage'), {url_or_none}), get_all=False)
                    if ((video_data.get('type') == 'brightcove' and video_data.get('brightcoveId'))
                            or (video_data.get('videoPlayer') == 'brightcove' and int_or_none(video_data.get('url')))):
                        if entry := extract_brightcove(video_data.get('brightcoveId') or video_data.get('url'), video_id):
                            entry['thumbnails'].extend(player_poster)
                            entries.append(entry)
                    elif ((video_data.get('type') == 'youtube' and video_data.get('youtubeId'))
                          or (video_data.get('videoPlayer') == 'youtube' and video_data.get('url'))):
                        if entry := extract_youtube(video_data.get('youtubeId') or video_data.get('url')):
                            entry['thumbnails'] = sorted(entry['thumbnails'], key=lambda d: d['preference'])
                            entry['thumbnails'][-1]['preference'] = -1
                            player_poster[-1]['preference'] = 0
                            entry['thumbnails'].extend(player_poster)
                            entries.append(entry)

        if json_ld := list(self._yield_json_ld(webpage, video_id)):
            info = {
                'id': video_id,
                **traverse_obj(json_ld[-1], {
                    'title': (('containsSeason', '@graph'), 0, (('episode', 'name'), 'name'),
                              {lambda x: re.sub(r'\W+Bluey Official Website$', '', x).split(' | ')[-1] if x else None}),
                    'description': (('containsSeason', '@graph'), 0,
                                    (('episode', 'description'), 'description'), {str_or_none}),
                    'thumbnail': ('containsSeason', 0, 'episode', 'image',
                                  {lambda x: x if url_or_none(x) else featured_image}),
                    'season': ('containsSeason', 0, 'name',
                               {lambda x: x if re.match(r'Season \d+$', x) else None}),
                    'season_number': ('containsSeason', 0, 'name',
                                      {lambda x: int(x.replace('Season ', '')) if re.match(r'Season \d+$', x) else None}),
                    'episode': ('containsSeason', 0, 'episode', 'episodeNumber',
                                {lambda x: f'Episode {x}' if x else None}),
                    'episode_number': ('containsSeason', 0, 'episode', 'episodeNumber', {int_or_none}),
                }, get_all=False),
            }
        else:
            title = re.sub(r'\W+Bluey Official Website$', '', self._og_search_title(webpage))
            info = {
                'id': video_id,
                'title': title.split(' | ')[-1],
                'description': self._og_search_description(webpage),
                'thumbnail': featured_image or self._og_search_thumbnail(webpage),
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
        elif len(entries) == 1:
            info['title'] = player_title or info['title']
            info['description'] = join_nonempty(info.get('description'), entries[0].get('description'), delim='\n\n')
            info['thumbnail'] = entries[0]['thumbnail'] = None
            return merge_dicts(info, entries[0])
        else:
            return info
