class Errors:
    access_token_too_short = "The 'access_token' did not meet the expected length of 43 characters. Preventing "
    "announcement query to FDM Monster"
    access_token_not_saved = "Conditional error: 'access_token' was not saved properly. Please report a bug to the " \
                             "plugin developers. Aborting "
    base_url_not_provided = "The 'base_url' was not provided. Preventing announcement query to FDM Monster"
    openid_config_unset = "Error connecting to FDM Monster. 'oidc_client_id' or 'oidc_client_secret' not set"
    config_openid_missing = "Configuration error: 'oidc_client_id' or 'oidc_client_secret' not set"
    ping_setting_unset = "'ping' config value not set. Aborting"


class Keys:
    persistence_uuid_key = "persistence_uuid"
    device_uuid_key = "device_uuid"


class Config:
    access_token_length = 43
    uuid_length = 36
    persisted_data_file = "backup_excluded_data.json"
    default_octoprint_host = "http://127.0.0.1"
    default_fdm_host = "http://127.0.0.1"
    default_fdm_port = 4000
    default_ping_secs = 120


class State:
    BOOT = "boot"
    SUCCESS = "success"
    SLEEP = "sleep"
    CRASHED = "crashed"
    RETRY = "retry"
