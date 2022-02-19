import datetime
import json
import unittest
import unittest.mock as mock
import pytest

from fdm_connector import FdmConnectorPlugin
from fdm_connector.constants import Errors, State
from tests.utils import mock_settings_get, mock_settings_global_get, mock_settings_custom, create_fake_at, \
    mocked_host_intercepted


class TestPluginAnnouncing(unittest.TestCase):
    @classmethod
    def setUp(cls):
        cls.settings = mock.MagicMock()  # Replace or refine with set/get
        cls.logger = mock.MagicMock()

        cls.plugin = FdmConnectorPlugin()
        cls.plugin._settings = cls.settings
        cls.plugin._settings.get = mock_settings_get
        cls.plugin._settings.get = mock_settings_global_get
        cls.plugin._write_persisted_data = lambda *args: None
        cls.plugin._logger = cls.logger
        cls.plugin._logger.info = print
        cls.plugin._logger.error = print
        # Nice way to test persisted data
        cls.plugin._data_folder = "test_data/announcements"

    def assert_state(self, state):
        assert self.plugin._state is state

    def test_call_mocked_announcement_improperly(self):
        """Call the query announcement, make sure it validates 'access_token'"""

        self.assert_state(State.BOOT)

        with pytest.raises(Exception) as e:
            self.plugin._query_announcement("asd", "asd")

        assert e.value.args[0] == Errors.access_token_too_short
        self.assert_state(State.CRASHED)

    def test_announcement_without_baseurl(self):
        """Call the query announcement, make sure it doesnt crash"""

        fake_token = create_fake_at()
        self.assert_state(State.BOOT)

        with pytest.raises(Exception) as e:
            self.plugin._query_announcement(None, access_token=fake_token)

        assert e.value.args[0] == Errors.base_url_not_provided
        self.assert_state(State.CRASHED)

    # This method will be used by the mock to replace requests.get
    def mocked_requests_post(*args, **kwargs):
        class MockResponse:
            def __init__(self, status_code, text):
                self.status_code = status_code
                self.text = text

        if f"{mocked_host_intercepted}:443" in args[0]:
            fake_token = create_fake_at()
            return MockResponse(200, json.dumps({"access_token": fake_token, "expires_in": 100}))
        return MockResponse(404, "{}")

    @mock.patch('requests.post', side_effect=mocked_requests_post)
    def test_announcement_with_proper_data(self, mock_post):
        """Call the query announcement properly"""

        fake_token = create_fake_at()
        url = "testwrong_url"
        self.assert_state(State.BOOT)

        # TODO wrong url is not prevented
        self.plugin._query_announcement(url, fake_token)

        # assert e.value.args[0] == Errors.base_url_not_provided
        self.assert_state(State.SLEEP)

    def test_check_fdm(self):
        with pytest.raises(Exception) as e:
            self.plugin._check_fdmmonster()

        assert e.value.args[0] == Errors.config_openid_missing
        self.assert_state(State.CRASHED)

    def test_check_fdmmonster_unreachable_settings(self):
        self.plugin._settings.get = mock_settings_custom
        self.assert_state(State.BOOT)

        self.plugin._check_fdmmonster()

        # TODO We are crashed with a connection error being caught. Save the reason
        self.assert_state(State.CRASHED)

    @mock.patch('requests.post', side_effect=mocked_requests_post)
    def test_check_fdmmonster_reachable_settings(self, mock_request):
        self.plugin._settings.get = mock_settings_custom
        self.assert_state(State.BOOT)

        self.plugin._check_fdmmonster()
        self.assert_state(State.SLEEP)

    @mock.patch('requests.post', side_effect=mocked_requests_post)
    def test_check_fdmmonster_reachable_settings_expired(self, mock_request):
        self.plugin._settings.get = mock_settings_custom
        self.plugin._persisted_data["requested_at"] = datetime.datetime.utcnow().timestamp()
        self.plugin._persisted_data["expires"] = -100
        self.assert_state(State.BOOT)

        self.plugin._check_fdmmonster()

        self.assert_state(State.SLEEP)

    @mock.patch('requests.post', side_effect=mocked_requests_post)
    def test_check_fdmmonster_reachable_settings_unexpired(self, mock_request):
        self.plugin._settings.get = mock_settings_custom
        self.plugin._persisted_data["requested_at"] = datetime.datetime.utcnow().timestamp()
        self.plugin._persisted_data["expires"] = 10000000
        self.plugin._persisted_data["access_token"] = create_fake_at()

        self.assert_state(State.BOOT)
        self.plugin._check_fdmmonster() # We skip querying the access_token
        self.assert_state(State.SLEEP)
