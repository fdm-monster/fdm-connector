# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import io
import json
import os
import uuid
from datetime import datetime
from urllib.parse import urljoin

import flask
import octoprint.plugin
import requests
from flask import request
from octoprint.util import RepeatedTimer

from hub_connector.constants import Errors, State, Config, Keys


def is_docker():
    path = '/proc/self/cgroup'
    return (
            os.path.exists('/.dockerenv') or
            os.path.isfile(path) and any('docker' in line for line in open(path))
    )


hub_announce_route = 'api/plugins/octoprint/announce'
hub_access_token_route = 'api/plugins/oidc/token'
hub_version_route = 'api/version'
requested_scopes = 'openid'


class HubConnectorPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.ShutdownPlugin,
    octoprint.plugin.BlueprintPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
):
    def __init__(self):
        self._ping_worker = None
        # device UUID and OIDC opaque access_token + metadata
        self._persisted_data = dict()
        self._excluded_persistence_datapath = None
        self._state = State.BOOT

    def on_after_startup(self):
        if self._settings.get(["hub_host"]) is None:
            self._settings.set(["hub_host"], Config.default_hub_host)
        if self._settings.get(["hub_port"]) is None:
            self._settings.set(["hub_port"], Config.default_hub_port)
        self._get_device_uuid()
        self._start_periodic_check()

    def get_excluded_persistence_datapath(self):
        self._excluded_persistence_datapath = os.path.join(self.get_plugin_data_folder(),
                                                           Config.persisted_data_file)
        return self._excluded_persistence_datapath

    def get_template_vars(self):
        hub_host = self._settings.get(["hub_host"])
        hub_port = self._settings.get(["hub_port"])
        base_url = f"{hub_host}:{hub_port}"
        favicon = f"{base_url}/favicon.ico"
        return dict(url=base_url, of_favicon=favicon)

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False),
            dict(type="navbar", custom_bindings=False)
        ]

    # TODO make http://https:// slash robust
    def get_settings_defaults(self):
        return {
            "hub_host": None,  # Without adjustment this config value is OFTEN useless
            "hub_port": None,  # Without adjustment this config value is OFTEN useless
            "port_override": None,  # Without adjustment this config value is SOMETIMES useless
            "device_uuid": None,  # Auto-generated and unique
            "oidc_client_id": None,  # Without adjustment this config value is ALWAYS useless
            "oidc_client_secret": None,  # Without adjustment this config value is ALWAYS useless
            "ping": Config.default_ping_secs
        }

    def get_settings_version(self):
        return 1

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return dict(
            js=["js/hub_connector.js"],
            css=["css/hub_connector.css"],
            less=["less/hub_connector.less"]
        )

    def initialize(self):
        self._fetch_persisted_data()

    def _fetch_persisted_data(self):
        filepath = self.get_excluded_persistence_datapath()
        if os.path.exists(filepath):
            try:
                with io.open(filepath, "r", encoding="utf-8") as f:
                    persistence_file = f.read()
                    persistence_json = json.loads(persistence_file)
                    self._persisted_data = persistence_json
            except json.decoder.JSONDecodeError as e:
                self._logger.warning(
                    "3D Hub persisted device Id file was of invalid format.")
                self._write_new_device_uuid(filepath)
        else:
            self._write_new_device_uuid(filepath)

    def _write_new_access_token(self, filepath, at_data):
        self._persisted_data["access_token"] = at_data["access_token"]
        self._persisted_data["expires_in"] = at_data["expires_in"]
        self._persisted_data["requested_at"] = int(datetime.utcnow().timestamp())
        if "token_type" in at_data.keys():
            self._persisted_data["token_type"] = at_data["token_type"]
        if "scope" in at_data.keys():
            self._persisted_data["scope"] = at_data["scope"]
        self._write_persisted_data(filepath)
        self._logger.info("3D Hub persisted data file was updated (access_token)")

    def _write_new_device_uuid(self, filepath):
        persistence_uuid = str(uuid.uuid4())
        self._persisted_data[Keys.persistence_uuid_key] = persistence_uuid
        self._write_persisted_data(filepath)
        self._logger.info("3D Hub persisted data file was updated (device_uuid).")

    def _write_persisted_data(self, filepath):
        with io.open(filepath, "w", encoding="utf-8") as f:
            f.write(json.dumps(self._persisted_data))

    def _get_device_uuid(self):
        device_uuid = self._settings.get([Keys.device_uuid_key])
        if device_uuid is None:
            device_uuid = str(uuid.uuid4())
            self._settings.set([Keys.device_uuid_key], device_uuid)
            self._settings.save()
        return device_uuid

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return dict(
            hub_connector=dict(
                displayName="3D-Hub Connector Plugin",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="3d-hub",
                repo="3d-hub-connector",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/3d-hub/3d-hub-connector/archive/{target_version}.zip"
            )
        )

    def _start_periodic_check(self):
        if self._ping_worker is None:
            ping_interval = self._settings.get_int(["ping"])
            if ping_interval:
                self._ping_worker = RepeatedTimer(
                    ping_interval, self._check_3dhub, run_first=True
                )
                self._ping_worker.start()
            else:
                return self._logger.error(Errors.ping_setting_unset)

    def _check_3dhub(self):
        hub_host = self._settings.get(["hub_host"])
        hub_port = self._settings.get(["hub_port"])

        if hub_host is not None and hub_port is not None:
            base_url = f"{hub_host}:{hub_port}"

            # OIDC client_credentials flow result
            access_token = self._persisted_data.get("access_token", None)
            requested_at = self._persisted_data.get("requested_at", None)
            expires = self._persisted_data.get("expires", None)

            # Token expiry check - prone to time desync
            is_expired = None
            if requested_at is not None and expires is not None:
                current_time = datetime.utcnow().timestamp()
                is_expired = current_time > requested_at + expires

            token_invalid = not access_token or is_expired

            if token_invalid:
                oidc_client_id = self._settings.get(["oidc_client_id"])
                oidc_client_secret = self._settings.get(["oidc_client_secret"])
                self._logger.info("Refreshing access_token as it was expired")
                success = self._query_access_token(base_url, oidc_client_id, oidc_client_secret)
                if not success:
                    self._state = State.CRASHED
                    return False
            else:
                # We skip querying the token
                self._state = State.SUCCESS

            if "access_token" not in self._persisted_data.keys():
                # Quite unlikely as we'd be crashed
                raise Exception(Errors.access_token_not_saved)

            at = self._persisted_data["access_token"]

            self._query_announcement(base_url, at)

        else:
            self._logger.error(Errors.openid_config_unset)
            self._state = State.CRASHED
            raise Exception(Errors.config_openid_missing)

    def _query_access_token(self, base_url, oidc_client_id, oidc_client_secret):
        if not oidc_client_id or not oidc_client_secret:
            self._logger.error("Configuration error: 'oidc_client_id' or 'oidc_client_secret' not set")
            self._state = State.CRASHED
            return False

        at_data = None
        try:
            data = {'grant_type': 'client_credentials', 'scope': requested_scopes}
            self._logger.info("Calling 3D Hub at URL: " + base_url)
            url = urljoin(base_url, hub_access_token_route)
            response = requests.post(url, data=data,
                                     verify=False, allow_redirects=False, auth=(oidc_client_id, oidc_client_secret))
            self._logger.info(response.text)
            self._logger.info(response.status_code)
            at_data = json.loads(response.text)
        except requests.exceptions.ConnectionError:
            self._state = State.RETRY  # TODO apply this with a backoff scheme
            self._logger.error("ConnectionError: error sending access_token request to 3D Hub")
        except Exception as e:
            self._state = State.CRASHED
            self._logger.error(
                "Generic Exception: error requesting access_token request to 3D Hub. Exception: " + str(e))

        if at_data is not None:
            if "access_token" not in at_data.keys():
                raise Exception(
                    "Response error: 'access_token' not received. Check your 3D Hub server logs. Aborting")
            if "expires_in" not in at_data.keys() is None:
                raise Exception("Response error: 'expires_in' not received. Check your 3D Hub server logs. Aborting")

            # Saves to file and to this plugin instance self._persistence_data accordingly
            self._write_new_access_token(self.get_excluded_persistence_datapath(), at_data)
            self._state = State.SUCCESS
            return True
        else:
            self._state = State.CRASHED
            self._logger.error("Response error: access_token data response was empty. Aborting")

    def _query_announcement(self, base_url, access_token):
        if self._state != State.SUCCESS and self._state != State.SLEEP:
            self._logger.error("State error: tried to announce when state was not 'success'")

        if base_url is None:
            self._state = State.CRASHED
            raise Exception(Errors.base_url_not_provided)

        if len(access_token) < 43:
            self._state = State.CRASHED
            raise Exception(Errors.access_token_too_short)

        # Announced data
        octoprint_port = self._settings.get(["port_override"])
        octoprint_host = self._settings.global_get(["server", "host"])
        # TODO maybe let 3D Hub decide instead of swapping ourselves?
        if octoprint_port is None:
            # Risk of failure when behind proxy (docker, vm, vpn, rev-proxy)
            octoprint_port = self._settings.global_get(["server", "port"])

        try:
            # Data folder based
            self._fetch_persisted_data()
            # Config file based
            device_uuid = self._get_device_uuid()

            check_data = {
                "deviceUuid": device_uuid,
                "persistenceUuid": self._persisted_data["persistence_uuid"],
                "host": octoprint_host,
                "port": int(octoprint_port),
                "docker": bool(is_docker())
            }

            headers = {'Authorization': 'Bearer ' + access_token}
            url = urljoin(base_url, hub_announce_route)
            response = requests.post(url, headers=headers, json=check_data)

            self._state = State.SLEEP
            self._logger.info(f"Done announcing to 3D Hub server ({response.status_code})")
            self._logger.info(response.text)
        except requests.exceptions.ConnectionError:
            self._state = State.CRASHED
            self._logger.error("ConnectionError: error sending announcement to 3D Hub")

    def _call_validator_abort(self, key):
        flask.abort(400, description=f"Expected '{key}' parameter")

    @staticmethod
    def additional_excludes_hook(excludes, *args, **kwargs):
        return [Config.persisted_data_file]

    @octoprint.plugin.BlueprintPlugin.route("/test_3dhub_connection", methods=["POST"])
    def test_3dhub_connection(self):
        input = json.loads(request.data)
        keys = ["url"]
        for key in keys:
            if key not in input:
                return self._call_validator_abort(key)

        proposed_url = input["url"]
        self._logger.info("Testing 3D Hub URL " + proposed_url)

        url = urljoin(proposed_url, hub_version_route)
        response = requests.get(url)
        version_data = json.loads(response.text)

        self._logger.info("Version response from 3D Hub " + version_data["version"])

        return version_data

    @octoprint.plugin.BlueprintPlugin.route("/test_3dhub_openid", methods=["POST"])
    def test_3dhub_openid(self):
        input = json.loads(request.data)
        keys = ["url", "client_id", "client_secret"]
        for key in keys:
            if key not in input:
                return self._call_validator_abort(key)

        proposed_url = input["url"]
        oidc_client_id = input["client_id"]
        oidc_client_secret = input["client_secret"]
        self._query_access_token(proposed_url, oidc_client_id, oidc_client_secret)

        self._logger.info("Queried access_token from 3D Hub")

        return {
            "state": self._state,
        }


__plugin_name__ = "3D Hub Connector"
__plugin_version__ = "0.1.0"
__plugin_description__ = "The 3D Hub plugin for OctoPrint"
__plugin_pythoncompat__ = ">=3,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = HubConnectorPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.plugin.backup.additional_excludes": __plugin_implementation__.additional_excludes_hook
    }
