/*
 * View model for FDM Connector
 *
 * Author: David Zwart
 * License: AGPLv3
 */
$(function () {
    function FdmConnectorViewModel(parameters) {
        const self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];

        // this will hold the Fdm URL currently saved
        // self.currentUrl = ko.observable();
        //
        //         // This will get called before the HelloWorldViewModel gets bound to the DOM, but after its
        // // dependencies have already been initialized. It is especially guaranteed that this method
        // // gets called _after_ the settings have been retrieved from the OctoPrint backend and thus
        // // the SettingsViewModel been properly populated.
        // self.onBeforeBinding = function() {
        //     self.currentUrl(self.settings.settings.plugins.fdm_connector.fdm_host());
        //     self.currentPort(self.settings.settings.plugins.fdm_connector.fdm_port());
        //
        //     console.log(self.currentUrl(), self.currentPort())
        // }

        function getCurrentProposedUrl() {
            const host = $("#settings-fdm_connector-fdm_host")[0];
            const port = $("#settings-fdm_connector-fdm_port")[0];

            const proposedUrl = new URL(host.value);
            proposedUrl.port = port.value;

            return proposedUrl;
        }

        function getClientIdAndSecret() {
            const client_id = $("#settings-oidc-client-id")[0].value;
            const client_secret = $("#settings-oidc-client-secret")[0].value;

            return {
                client_id,
                client_secret
            };
        }

        self.settings.openfdmmonster = function () {
            const currentUrl = getCurrentProposedUrl();

            window.open(currentUrl, '_blank');
        }

        self.settings.testUrlBackend = async function () {
            const loader = $("#connection-loader");
            const successBar = $("#connection-success");
            const failureBar = $("#connection-failed");
            const responseVersion = $("#response-version");

            const currentUrl = getCurrentProposedUrl();

            var fullUrl = PLUGIN_BASEURL + "fdm_connector/test_fdmmonster_connection";

            loader.show();
            successBar.hide();
            failureBar.hide();
            responseVersion[0].innerText = "unset";
            return await fetch(fullUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: currentUrl
                })
            })
                .then(async (response) => {
                    try {
                        if (response.status >= 300) {
                            successBar.hide();
                            failureBar.show();
                        } else {
                            successBar.show();
                            const body = await response.json();
                            responseVersion[0].innerText = body.version;
                        }
                    } catch (e) {
                        console.log("Error occurred while testing FDM Monster", e);
                    } finally {
                        loader.hide();
                    }
                });
        };

        self.settings.testCredentialsBackend = async function () {
            const loader = $("#credentials-loader");
            const successBar = $("#credentials-success");
            const failureBar = $("#credentials-failed");
            const bugBar = $("#credentials-bug");
            const responseState = $("#response-state");

            const currentUrl = getCurrentProposedUrl();

            var fullUrl = PLUGIN_BASEURL + "fdm_connector/test_fdmmonster_openid";

            loader.show();
            successBar.hide();
            failureBar.hide();
            responseState[0].innerText = "unset";
            return await fetch(fullUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: currentUrl,
                    ...getClientIdAndSecret()
                })
            })
                .then(async (response) => {
                    try {
                        if (response.status == 400) {
                            successBar.hide();
                            bugBar.show();
                            failureBar.hide();
                        } else if (response.status >= 300) {
                            successBar.hide();
                            bugBar.hide();
                            failureBar.show();
                        } else {
                            successBar.show();
                            const body = await response.json();
                            responseState[0].innerText = body.state;
                        }
                    } catch (e) {
                        console.log("Error occurred while testing FDM Monster", e);
                    } finally {
                        loader.hide();
                    }
                });
        };
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push([
        FdmConnectorViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        [
            "loginStateViewModel", "settingsViewModel"
        ],
        // Elements to bind to, e.g. #settings_plugin_fdm_connector, #tab_plugin_fdm_connector, ...
        [
            // "#settings_plugin_fdm_connector",
            // "#navbar_plugin_fdm_connector"
        ]
    ]);
});
