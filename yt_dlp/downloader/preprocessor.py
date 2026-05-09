import copy
import json
import time

from . import get_suitable_downloader
from .common import FileDownloader
from ..utils import (
    DownloadError,
    join_nonempty,
    traverse_obj,
    url_or_none,
)


class preprocessorFD(FileDownloader):
    """ Process info dict before download """

    def real_download(self, filename, info_dict):
        prep_key = traverse_obj(
            info_dict, ('downloader_options', 'preprocessor', 'key', {str}))
        if not prep_key:
            raise DownloadError('[info] Preprocessor not specified')
        # arguments passed from the extractor
        prep_args = traverse_obj(
            info_dict, ('downloader_options', 'preprocessor', 'args', {dict}))
        prep_args = prep_args or {}

        video_id = info_dict.get('id')
        # duplicate info_dict
        info_copy = info_dict.copy()

        # get the ultimate downloader class
        def get_downloader(info, params={}, ydl=self.ydl):
            info['downloader_options'].pop('preprocessor', None)
            downloader = get_suitable_downloader(
                info, params, protocol=info.get('protocol'))
            return downloader(ydl, params)
        dl = get_downloader(copy.deepcopy(info_dict), self.params or {})

        match prep_key:
            case 'Gimy':
                msg = join_nonempty(video_id, 'Obtaining m3u8 manifest URL', delim=': ')
                self.to_screen(f'[info] {msg}')
                try:
                    data = self.ydl.urlopen(
                        f"{info_dict['url']}&_t={int(time.time() * 1000)}")
                    data_dict = json.loads(data.read())
                    if data_dict.get('code') == 200:
                        if url := traverse_obj(data_dict, ('url', {url_or_none})):
                            info_copy['url'] = url
                            return dl.real_download(filename, info_copy)
                    # cannot obtain manifest URL
                    raise DownloadError(data_dict.get('msg'))
                except BaseException as e:
                    msg = join_nonempty(
                        video_id, 'Unable to obtain m3u8 manifest URL', e, delim=': ')
                    if info_dict.get('filename'):
                        # info_dict['filename'] exists when actual download
                        # raise exception when download will fail
                        raise DownloadError(f'[{self.FD_NAME}] {msg}')
                    # report error when check format
                    self.report_error(f'[{self.FD_NAME}] {msg}')
                return dl.real_download(filename, info_copy)
