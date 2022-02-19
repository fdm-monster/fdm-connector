import json
import unittest
import unittest.mock as mock

import pytest
from werkzeug.exceptions import BadRequest

from fdm_connector import FdmConnectorPlugin, State


class TestPluginConnection(unittest.TestCase):
    @classmethod
    def setUp(cls):
        cls.settings = mock.MagicMock()  # Replace or refine with set/get
        cls.logger = mock.MagicMock()

        cls.plugin = FdmConnectorPlugin()
        cls.plugin._settings = cls.settings
        cls.plugin._logger = cls.logger
        cls.plugin._logger.info = print
        cls.plugin._logger.error = print
        cls.plugin._ping_worker = dict()  # disable it
        cls.plugin._data_folder = "test_data/connection"
        cls.plugin._write_persisted_data = lambda *args: None

    def assert_state(self, state):
        assert self.plugin._state is state

    # This method will be used by the mock to replace requests.get
    def mocked_requests_get(*args, **kwargs):
        class MockResponse:
            def __init__(self, json_data, status_code, text):
                self.json_data = json_data
                self.status_code = status_code
                self.text = text

            def json(self):
                return self.json_data

        return MockResponse({"version": "test-version"}, 200, json.dumps({"version": "test-version"}))

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def test_fdm_connection_test(self, mocked_requests_get):
        """Call the FDM Monster connection test properly"""

        m = mock.MagicMock()
        m.data = json.dumps({"url": "http://127.0.0.1"})

        with mock.patch("fdm_connector.request", m):
            # somefile.method_called_from_route()
            response = self.plugin.test_fdmmonster_connection()
            assert response["version"] == "test-version"

    def _assert_bad_request_parameter(self, exception_info, param):
        assert str(exception_info.value) == f"400 Bad Request: Expected '{param}' parameter"

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def test_fdm_connection_test_validation(self, mocked_requests_get):
        """Call the FDM Monster connection test with faulty input"""

        m = mock.MagicMock()
        m.data = json.dumps({})
        with mock.patch("fdm_connector.request", m):
            with pytest.raises(BadRequest) as e:
                self.plugin.test_fdmmonster_connection()
            self._assert_bad_request_parameter(e, "url")

    @mock.patch('requests.post', side_effect=mocked_requests_get)
    def test_fdm_openid_validation(self, mocked_requests_get):
        """Call the FDM Monster OpenID connection test with faulty input"""

        m = mock.MagicMock()
        m.data = json.dumps({})
        with mock.patch("fdm_connector.request", m):
            with pytest.raises(BadRequest) as e:
                self.plugin.test_fdmmonster_openid()
            self._assert_bad_request_parameter(e, "url")

        m = mock.MagicMock()
        m.data = json.dumps({"url": "http://127.0.0.1"})
        with mock.patch("fdm_connector.request", m):
            with pytest.raises(BadRequest) as e:
                self.plugin.test_fdmmonster_openid()
            self._assert_bad_request_parameter(e, "client_id")

        m = mock.MagicMock()
        m.data = json.dumps({"url": "http://127.0.0.1", "client_secret": "asd"})
        with mock.patch("fdm_connector.request", m):
            with pytest.raises(BadRequest) as e:
                self.plugin.test_fdmmonster_openid()
            self._assert_bad_request_parameter(e, "client_id")

        m = mock.MagicMock()
        m.data = json.dumps({"url": "http://127.0.0.1", "client_id": "asd"})
        with mock.patch("fdm_connector.request", m):
            with pytest.raises(BadRequest) as e:
                self.plugin.test_fdmmonster_openid()
            self._assert_bad_request_parameter(e, "client_secret")

    # This method will be used by the mock to replace requests.get
    def mocked_openid_response_notfound(*args, **kwargs):
        class MockResponse:
            def __init__(self, status_code, text):
                self.status_code = status_code
                self.text = text

        return MockResponse({}, 404)

    @mock.patch('requests.post', side_effect=mocked_openid_response_notfound)
    def test_fdm_openid_bug_response(self, mocked_requests_get):
        """Call the FDM Monster OpenID connection test with a not found error"""

        m = mock.MagicMock()
        m.data = json.dumps({"url": "http://127.0.0.1", "client_id": "asd", "client_secret": "ok"})
        with mock.patch("fdm_connector.request", m):
            self.assert_state(State.BOOT)
            self.plugin.test_fdmmonster_openid()
            self.assert_state(State.CRASHED)

    # This method will be used by the mock to replace requests.get or requests.post
    def mocked_openid_response_maximal(*args, **kwargs):
        class MockResponse:
            def __init__(self, status_code, text):
                self.status_code = status_code
                self.text = text

        return MockResponse(200, json.dumps({"access_token": "test-token", "expires_in": 600, "token_type": "Bearer",
                                             "scope": "openid profile email pincode bank_id"}))

    # This method will be used by the mock to replace requests.get or requests.post
    def mocked_openid_response_minimal(*args, **kwargs):
        class MockResponse:
            def __init__(self, status_code, text):
                self.status_code = status_code
                self.text = text

        return MockResponse(200,
                            json.dumps({"access_token": "test-token", "expires_in": 600}))

    @mock.patch('requests.post', side_effect=mocked_openid_response_maximal)
    def test_fdm_openid_success_maximal(self, mocked_requests_get):
        """Call the FDM Monster OpenID connection test properly with maximum property set"""

        m = mock.MagicMock()
        m.data = json.dumps({"url": "http://127.0.0.1", "client_id": "asd", "client_secret": "ok"})
        with mock.patch("fdm_connector.request", m):
            self.assert_state(State.BOOT)
            self.plugin.test_fdmmonster_openid()
            self.assert_state(State.SUCCESS)

    @mock.patch('requests.post', side_effect=mocked_openid_response_minimal)
    def test_fdm_openid_success_minimal(self, mocked_requests_get):
        """Call the FDM Monster OpenID connection test properly with missing response properties 'scope' and
        'token_type' """

        m = mock.MagicMock()
        m.data = json.dumps({"url": "http://127.0.0.1", "client_id": "asd", "client_secret": "ok"})
        with mock.patch("fdm_connector.request", m):
            self.assert_state(State.BOOT)
            self.plugin.test_fdmmonster_openid()
            self.assert_state(State.SUCCESS)
