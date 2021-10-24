from random import choice
from string import ascii_uppercase

from hub_connector import Config

mocked_host_intercepted = "https://hub123asdasdasdasd.com"

def mock_settings_get(accessor):
    if accessor[0] == "hub_host":
        return Config.default_hub_host
    if accessor[0] == "hub_port":
        return Config.default_hub_port
    if accessor[0] == "ping":
        return Config.default_ping_secs
    return None


def mock_settings_custom(accessor):
    if accessor[0] == "hub_host":
        return mocked_host_intercepted
    if accessor[0] == "hub_port":
        return 443
    if accessor[0] == "ping":
        return 300
    if accessor[0] == "oidc_client_id":
        return "ValidAnnoyer123"
    if accessor[0] == "oidc_client_secret":
        return "ValidPawo321"
    return None


def mock_settings_global_get(accessor):
    if accessor[0] == "server" and accessor[1] == "host":
        return Config.default_octoprint_host
    return None


def mock_settings_get_int(accessor):
    if accessor[0] == "hub_port":
        return Config.default_hub_port
    if accessor[0] == "ping":
        return Config.default_ping_secs
    return None


def create_fake_at():
    return ''.join(choice(ascii_uppercase) for i in range(Config.access_token_length))
