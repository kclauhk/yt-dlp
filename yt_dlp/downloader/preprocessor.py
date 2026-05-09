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
            info_dict, ('downloader_options', 'preprocessor', 'args', {dict}), default={})

        filename, info_dict = self._process(filename, info_dict, prep_key, prep_args)
        info_dict['downloader_options'].pop('preprocessor', None)
        downloader = get_suitable_downloader(
            info_dict, self.params or {}, protocol=info_dict.get('protocol'))
        fd = downloader(self.ydl, self.params or {})
        url = info_dict['url']
        self.write_debug(f'Invoking {fd.FD_NAME} downloader on "{url}"')
        return fd.real_download(filename, info_dict)

    def _process(self, filename, info_dict, processor, preprocessor_args):
        video_id = info_dict.get('id')
        new_info = copy.deepcopy(info_dict)

        match processor:
            case 'Gimy':
                msg = join_nonempty(video_id, 'Obtaining manifest URL', delim=': ')
                self.to_screen(f'[info] {msg}')
                try:
                    data = {}
                    if json_data := self.ydl.urlopen(
                            f"{info_dict['url']}&_t={int(time.time() * 1000)}"):
                        data = json.loads(json_data.read())
                        self.write_debug(join_nonempty(
                            video_id, f"Parse result: {data.get('msg')}", delim=': '))
                    if data.get('code') == 200:
                        if url := traverse_obj(data, ('url', {url_or_none})):
                            new_info['url'] = url
                            if 'www.bilibili.com/' in info_dict['url']:
                                new_info['http_headers']['origin'] = 'https://www.bilibili.com'
                                new_info['http_headers']['referer'] = 'https://www.bilibili.com/'
                            return filename, new_info
                    # cannot obtain manifest URL
                    raise DownloadError(data.get('msg'))
                except BaseException as e:
                    msg = join_nonempty(
                        video_id, 'Unable to obtain manifest URL', e, delim=': ')
                    if info_dict.get('filename'):
                        # info_dict['filename'] exists when actual download
                        # raise exception if download will fail
                        raise DownloadError(f'[{self.FD_NAME}] {msg}')
                    # report error when check format
                    self.report_error(f'[{self.FD_NAME}] {msg}')

            case _:
                pass

        return filename, new_info   # don't change this line
