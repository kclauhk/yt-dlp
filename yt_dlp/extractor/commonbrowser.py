import asyncio
import os
import random
import sys

try:
    from DrissionPage import Chromium, ChromiumOptions
    from DrissionPage.errors import (
        BrowserConnectError,
        PageDisconnectedError,
    )
    dp_available = True
except ImportError:
    dp_available = False

try:
    import nodriver
    from nodriver import (
        cdp,
        loop,
        start,
    )
    nd_available = True
except ImportError:
    nd_available = False

from .common import InfoExtractor
from ..networking.exceptions import (
    HTTPError,
    TransportError,
)
from ..utils import (
    NO_DEFAULT,
    ExtractorError,
    join_nonempty,
    traverse_obj,
)


class BrowserIE(InfoExtractor):
    IE_DESC = False

    def _close_browser(self):
        if hasattr(self, '_browser'):
            if callable(getattr(self._browser, 'quit', None)):
                self._browser.quit()
            elif callable(getattr(self._browser, 'stop', None)):
                self._browser.stop()

    def _browser_get_webpage(
            self, url, video_id, note=None, errnote=None, fatal=True, tries=1,
            timeout=NO_DEFAULT, browser_config: dict = {}, *args, **kwargs):
        """
        Keyword arguments:
        tries -- number of tries
        timeout -- sleep interval between tries (value re-assigned to "interval")
        note -- note printed before downloading (string)
        errnote -- note printed in case of an error (string)
        fatal -- flag denoting whether error should be considered fatal,
            i.e. whether it should cause ExtractionError to be raised,
            otherwise a warning will be reported and extraction continued
        browser_config -- browser options: the dictionary may includes:
            headless:   headless mode (boolean) (not recommended, can't handle Cloudflare challenge)
            eager_load: stop loading after DOM ready (for DrissionPage)
            arguments:  browser startup options (dictionary)
            evaluate:   a function to check if the desired webpage has been retrieved
        """

        if errnote is None:
            errnote = 'Unable to download webpage'

        if (not browser_config and hasattr(self, '_browser_config')
                and isinstance(self._browser_config, dict)):
            browser_config = self._browser_config
        headless = browser_config.get('headless', False)
        eager_load = browser_config.get('eager_load', False)
        browser_args = {}
        if 'arguments' in browser_config and isinstance(browser_config['arguments'], dict):
            browser_args = browser_config['arguments']
        if 'evaluate' in browser_config and callable(browser_config['evaluate']):
            evaluate = browser_config['evaluate']
        else:
            evaluate = lambda x: False

        browser_executable_path = (
            self._configuration_arg(
                'browser_path', casesense=True, default=[None])[0]
            # backwards-compat
            or self._configuration_arg(
                'browser_path', [None], ie_key=self.ie_key(), casesense=True)[0]
        )

        interval = 0 if timeout is NO_DEFAULT else timeout
        request_timeout = self.get_param('socket_timeout') or 30
        timeout = 10

        def is_challenge(response):
            # check if the response contains a anti-bot challenge
            # only Cloudflare for now
            return ('(function(){window._cf_chl_opt' in response)

        if not hasattr(self, '_browser'):
            self._browser = None

        random.seed(os.getpid())
        local_port = int(random.random() * 65535)

        if dp_available:
            if note is not False:
                self.report_download_webpage(video_id, note=note)

            if not self._browser or not self._browser.states.is_alive:
                self.to_screen(
                    f'{video_id}: Launching browser due to anti-bot challenge. '
                    'Do not close the browser window.')
                co = ChromiumOptions()
                co.set_browser_path(browser_executable_path)
                co.set_local_port(local_port)
                co.set_timeouts(base=timeout)
                co.set_timeouts(page_load=request_timeout)
                co.set_argument('--app', url)
                for arg, value in browser_args.items():
                    if value is None:
                        co.set_argument(arg)
                    else:
                        co.set_argument(arg, value)

                # use headless mode
                if headless:
                    co.headless()
                    if sys.platform == 'linux' or sys.platform == 'linux2':
                        platform_identifier = 'X11; Linux x86_64'
                    elif sys.platform == 'darwin':
                        platform_identifier = 'Macintosh; Intel Mac OS X 10_15_7'
                    elif sys.platform == 'win32':
                        platform_identifier = 'Windows NT 10.0; Win64; x64'
                    co.set_user_agent(
                        f'Mozilla/5.0 ({platform_identifier}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36')

                try:
                    self._browser = Chromium(co)
                except BrowserConnectError as err:
                    raise ExtractorError(f'Failed to start browser: {err}') from err

            tab = self._browser.latest_tab
            if eager_load:
                tab.set.load_mode.eager()

            try_count = 0
            while self._browser.states.is_alive:
                try:
                    tab.get(url, retry=1)
                    if not is_challenge(tab.html):
                        return tab.html
                    else:
                        if eager_load:
                            tab.set.load_mode.normal()
                            tab.get(url, retry=1)
                        tab.run_js('try { turnstile.reset() } catch(e) { }')
                        for _ in range(timeout if try_count else timeout * 2):
                            try:
                                chl_solution = tab.ele('@name=cf-turnstile-response')
                                chl_wrapper = chl_solution.parent()
                                chl_iframe = chl_wrapper.shadow_root.ele('tag:iframe')
                                chl_iframe.run_js('''
                                    window.dtp = 1
                                    function getRandomInt(min, max) {
                                        return Math.floor(Math.random() * (max - min + 1)) + min;
                                    }

                                    // old method wouldn't work on 4k screens
                                    let screenX = getRandomInt(800, 1200);
                                    let screenY = getRandomInt(400, 600);

                                    Object.defineProperty(MouseEvent.prototype, 'screenX', { value: screenX });
                                    Object.defineProperty(MouseEvent.prototype, 'screenY', { value: screenY });
                                    ''')
                                chl_iframe_body = chl_iframe.ele('tag:body').shadow_root
                                chl_button = chl_iframe_body.ele('tag:input')
                                chl_button.click()
                            except Exception:
                                pass

                            if '(function(){window._cf_chl_opt' not in tab.html:
                                break
                            else:
                                self._sleep(1, video_id)

                    if data := self._search_json(
                            r'var loadTimeDataRaw\s*=', tab.html, 'loadtime_data',
                            video_id, end_pattern=';</scrip', fatal=False, default=None):
                        msg = traverse_obj(data, ('heading', 'msg', {str}))
                        sub_msg = self._html_search_regex(
                            r'main-message">[\s\S]+?<p>([^$].+)</p', tab.html,
                            'message', fatal=False, default=None)
                        if sub_msg == msg:
                            sub_msg = None
                        errmsg = join_nonempty(f'{msg}.', sub_msg, delim=' ')
                    else:
                        for _ in range(timeout):
                            if not evaluate(tab.html):
                                self._sleep(1, video_id)
                        if is_challenge(tab.html):
                            errmsg = 'Security verification failed.'
                        else:
                            return tab.html
                    raise TransportError(errmsg)
                except (BrowserConnectError, PageDisconnectedError) as err:
                    error = err.__dict__['_args'][0]
                    raise ExtractorError(
                        f'{errnote}: {error}', cause=err, video_id=video_id,
                        expected=True) from err
                except TransportError as err:
                    errmsg = f'{errnote}: {err}'
                    try_count += 1
                    if try_count >= tries:
                        if fatal:
                            raise ExtractorError(errmsg, video_id=video_id) from err
                        else:
                            self.report_warning(errmsg, video_id=video_id)
                            return False
                    self.to_screen(f'{video_id}: {errmsg}')
                    self._sleep(interval, video_id)
                    self.to_screen(f'{video_id}: Retrying ({try_count}/{tries - 1})...')
                except Exception as err:
                    raise ExtractorError(
                        f'{errnote}: {err}', cause=err, video_id=video_id,
                        expected=True) from err

        elif nd_available:
            if note is not False:
                self.report_download_webpage(video_id, note=note)

            def get_config(browser_args):
                arguments = []
                for arg, value in browser_args.items():
                    if value is None:
                        arguments.append(arg)
                    else:
                        arguments.append(f'{arg}={value}')
                return nodriver.core.config.Config(
                    headless=headless,
                    browser_executable_path=browser_executable_path,
                    browser_args=arguments,
                )

            self._new_response = None

            async def response_handler(event: cdp.network.ResponseReceived):
                self._new_response = True
                if hasattr(self, '_response_handler'):
                    self._response_handler(event)

            async def download_webpage(url):
                if not self._browser or self._browser.stopped:
                    self.to_screen(
                        f'{video_id}: Launching browser due to anti-bot challenge. '
                        'Do not close the browser window.')
                    try:
                        self._browser = await start(config=get_config(browser_args))
                        page = await asyncio.wait_for(
                            self._browser.get('about:blank'), timeout=5)
                        page.add_handler(cdp.network.ResponseReceived, response_handler)
                    except Exception as err:
                        raise ExtractorError(f'Failed to start browser: {err}') from err

                try_count = 0
                while not self._browser.stopped:
                    html = ''
                    try:
                        page = await asyncio.wait_for(
                            self._browser.get(url), timeout=request_timeout)
                        html = await asyncio.wait_for(page.get_content(), timeout=timeout)
                        for _ in range(timeout if try_count else timeout * 2):
                            if evaluate(html) or self._browser.stopped:
                                break
                            elif data := self._search_json(
                                    r'var loadTimeDataRaw\s*=', html, 'loadtime',
                                    video_id, end_pattern=';</script', fatal=False,
                                    default=None):
                                msg = traverse_obj(data, ('heading', 'msg', {str}))
                                sub_msg = self._html_search_regex(
                                    r'main-message">[\s\S]+?<p>([^$].+)</p', html,
                                    'message', fatal=False, default=None)
                                if sub_msg == msg:
                                    sub_msg = None
                                raise TransportError(
                                    join_nonempty(f'{msg}.', sub_msg, delim=' '))
                            elif is_challenge(html) or self._new_response:
                                if '(function(){window._cf_chl_opt' in html:
                                    await asyncio.wait_for(page.verify_cf(), timeout=timeout)
                                self._new_response = False
                                self._sleep(1, video_id)
                            html = await asyncio.wait_for(page.get_content(), timeout=timeout)
                        if is_challenge(html):
                            raise TransportError('Security verification failed.')
                        else:
                            return html
                    except TransportError as err:
                        errmsg = f'{errnote}: {err}'
                        try_count += 1
                        if try_count >= tries:
                            if fatal:
                                raise ExtractorError(
                                    errmsg, video_id=video_id, expected=True) from err
                            else:
                                self.report_warning(errmsg, video_id=video_id)
                                return False
                        self.to_screen(f'{video_id}: {errmsg}')
                        self._sleep(interval, video_id)
                        self.to_screen(
                            f'{video_id}: Retrying ({try_count}/{tries - 1})...')
                    except Exception as err:
                        raise ExtractorError(
                            f'{errnote}: {err}', cause=err, video_id=video_id,
                            expected=True) from err

            if not hasattr(self, '_loop'):
                self._loop = loop()
            return self._loop.run_until_complete(download_webpage(url))

        else:
            return super()._download_webpage(
                url, video_id, note, errnote, fatal, tries, timeout, *args, **kwargs)

    def _download_webpage(
            self, url, video_id, note=None, errnote=None, fatal=True, tries=1,
            timeout=NO_DEFAULT, browser_config: dict = {}, *args, **kwargs):

        def is_challenge(response):
            # check if the response contains a anti-bot challenge
            # only Cloudflare for now
            return (response.get_header('server').lower() == 'cloudflare'
                    and response.get_header('cf-mitigated') == 'challenge')

        if not hasattr(self, '_browser_required'):
            self._browser_required = False
        try:
            if self._browser_required:
                return self._browser_get_webpage(
                    url, video_id, note, errnote, fatal, max(3, tries), 0, browser_config)
            else:
                return super()._download_webpage(
                    url, video_id, note, errnote, fatal, tries, timeout, *args, **kwargs)
        except Exception as err:
            if hasattr(err, 'cause'):
                if not isinstance(err.cause, HTTPError) or err.cause.status != 403:
                    raise
                response = err.cause.response
                if is_challenge(response):
                    try:
                        self._browser_required = True
                        return self._browser_get_webpage(
                            url, video_id, note, errnote, fatal, max(3, tries), 0, browser_config)
                    except Exception as err:
                        if (hasattr(err, 'cause')
                                and isinstance(err.cause, HTTPError)
                                and err.cause.status == 403):
                            raise ExtractorError(
                                'Got HTTP Error 403 caused by anti-bot challenge; '
                                'try again after install a Chromium-based browser, and package(s): '
                                'a) DrissionPage (https://pypi.org/project/DrissionPage/), '
                                'or b) opencv-python and nodriver 0.47.0 (https://pypi.org/project/nodriver/0.47.0/)',
                                video_id=video_id, ie=self.IE_NAME, expected=True) from err
            raise
