from typing import List
from urllib.parse import quote_plus

from brotab.mediator.log import mediator_logger
from brotab.mediator.transport import Transport


class BrowserRemoteAPI:
    """
    Communicates with a browser using stdin/stdout. This mediator is supposed
    to be run by the browser after a request from the helper extension.
    """

    def __init__(self, transport: Transport):
        self._transport: Transport = transport

    def list_tabs(self):
        command = {'name': 'list_tabs'}
        self._transport.send(command)
        return self._transport.recv()

    def query_tabs(self, query_info: str):
        mediator_logger.info('query info: %s', query_info)
        command = {'name': 'query_tabs', 'query_info': query_info}
        self._transport.send(command)
        return self._transport.recv()

    def move_tabs(self, move_triplets: str):
        """
        :param move_triplets: Comma-separated list of:
            <tabID> <windowID> <newIndex>
        """
        mediator_logger.info('move_tabs, move_triplets: %s', move_triplets)

        triplets = [list(map(int, triplet.split(' ')))
                    for triplet in move_triplets.split(',')]
        mediator_logger.info('moving tab ids: %s', triplets)
        command = {'name': 'move_tabs', 'move_triplets': triplets}
        self._transport.send(command)
        return self._transport.recv()

    def open_urls(self, urls: List[str], window_id=None):
        """
        Open specified list of URLs in a window, specified by window_id.

        If window_id is None, currently active window is used.
        """
        mediator_logger.info('open urls: %s', urls)

        command = {'name': 'open_urls', 'urls': urls}
        if window_id is not None:
            command['window_id'] = window_id
        self._transport.send(command)
        return self._transport.recv()

    def update_tabs(self, updates: [object]):
        """
        Sends a list of updates to the browser. Format:
        [ {
            'tab_id': <tab_id>,
            'properties': {
                'url': <url>,
            }
        } ]
        see https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/tabs/update
        """
        mediator_logger.info('update tabs: %s', updates)
        command = {'name': 'update_tabs', 'updates': updates}
        self._transport.send(command)
        return self._transport.recv()

    def close_tabs(self, tab_ids: str):
        """
        :param tab_ids: Comma-separated list of tab IDs to close.
        """
        int_tab_ids = [int(id_) for id_ in tab_ids.split(',')]
        mediator_logger.info('closing tab ids: %s', int_tab_ids)
        command = {'name': 'close_tabs', 'tab_ids': int_tab_ids}
        self._transport.send(command)
        return self._transport.recv()

    def new_tab(self, query: str):
        url = "https://www.google.com/search?q=%s" % quote_plus(query)
        mediator_logger.info('opening url: %s', url)
        command = {'name': 'new_tab', 'url': url}
        self._transport.send(command)
        return self._transport.recv()

    def activate_tab(self, tab_id: int, focused: bool):
        mediator_logger.info('activating tab id: %s', tab_id)
        command = {'name': 'activate_tab', 'tab_id': tab_id, 'focused': focused}
        self._transport.send(command)

    def get_active_tabs(self) -> str:
        mediator_logger.info('getting active tabs')
        command = {'name': 'get_active_tabs'}
        self._transport.send(command)
        return self._transport.recv()

    def get_words(self, tab_id: str, match_regex: str, join_with: str):
        mediator_logger.info('getting tab words: %s', tab_id)
        command = {
            'name': 'get_words',
            'tab_id': tab_id,
            'match_regex': match_regex,
            'join_with': join_with,
        }
        self._transport.send(command)
        return self._transport.recv()

    def get_text(self, delimiter_regex: str, replace_with: str):
        mediator_logger.info('getting text, delimiter_regex=%s, replace_with=%s',
                             delimiter_regex, replace_with)
        command = {
            'name': 'get_text',
            'delimiter_regex': delimiter_regex,
            'replace_with': replace_with,
        }
        self._transport.send(command)
        return self._transport.recv()

    def get_html(self, delimiter_regex: str, replace_with: str):
        mediator_logger.info('getting html, delimiter_regex=%s, replace_with=%s',
                             delimiter_regex, replace_with)
        command = {
            'name': 'get_html',
            'delimiter_regex': delimiter_regex,
            'replace_with': replace_with,
        }
        self._transport.send(command)
        return self._transport.recv()

    def get_browser(self):
        mediator_logger.info('getting browser name')
        command = {'name': 'get_browser'}
        self._transport.send(command)
        return self._transport.recv()


def default_remote_api(transport: Transport) -> BrowserRemoteAPI:
    return BrowserRemoteAPI(transport)
