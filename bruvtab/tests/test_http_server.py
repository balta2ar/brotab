from unittest.mock import Mock, patch
from urllib.parse import quote_plus

from bruvtab.mediator.http_server import MediatorHttpServer


def test_move_tabs_route_forwards_triplets():
    remote_api = Mock()
    remote_api.move_tabs.return_value = 'OK'
    with patch('bruvtab.mediator.http_server.make_server'):
        server = MediatorHttpServer('127.0.0.1', 0, remote_api, 0.1)
    server.app.config['TESTING'] = True
    triplets = '9624740 9624730 44,9624741 9624730 45'

    response = server.app.test_client().get('/move_tabs/' + quote_plus(triplets))

    assert response.status_code == 200
    assert response.data == b'OK'
    remote_api.move_tabs.assert_called_once_with(triplets)
