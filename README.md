**Warning: This plugin is currently not in use, and it will not work with FDM Monster.**

# FDM Connector

The FDM Connector is an OctoPrint plugin that simplifies the initial connection to FDM Monster. The plugin is also expected to facilitate setting up a tunnel connection and tracking filament usage in future versions.

## Current feature(s)

- Auto-registration - Send your OctoPrint connection parameters to FDM Monster securely to make setting up printers a breeze.

## Future features

- Filament Pedometer - Send filament usage data to FDM Monster, cooperating with the plugin SpoolManager without external database (Filament Manager is not our aim).
- Http Tunnel - Connect to FDM Monster to make connection to printers easy, especially over docker, VPN, DMZ, VLAN, the cloud, or other complex network setups.
- Single-Sign-On - Client-to-machine (C2M) and machine-to-machine (M2M) authentication, removing the need for more than 1 set of credentials across the farm.

For more feature requests, bugs, or ideas, please visit the [FDM Connector Discussions page](https://github.com/fdm-monster/fdm-connector/discussions).

## Setup

**Note: This plugin is currently in the alpha stage and requires the plugin system on FDM Monster, which is not yet released.**

To install the FDM Connector, use the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html) or manually use this URL:

```
https://github.com/fdm-monster/fdm-connector/archive/main.zip
```

Configure the plugin completely for one or more printers before checking FDM Monster.


## Configuration
**Warning - restoring from an OctoPrint backup can be a cause of security weakness due to copied passwords. In the end, we are not responsible for your choices, but we advise changing the `accessControl:salt` and regenerating the main user account for each OctoPrint instance.**

### Configuration - auto-registration
Properly configuring the auto-registration can massively improve the steps you need to undertake to set up your farm.

- REQUIRED `fdm_host`: the host to reach FDM Monster with (IP, localhost, domain name, etc)
- REQUIRED `fdm_port`: the port to approach the FDM Monster server (number)
- REQUIRED `oidc_client_id`: the client ID to authenticate with the FDM Monster server using OpenID Connect (string)
- REQUIRED `oidc_client_secret`: the client secret key to authenticate with the FDM Monster server using OpenID Connect (string)
- OPTIONAL `port_override`: the announced port for how FDM Monster can reach OctoPrint later (default is taken from `server:port`, but this is not always correct in case of Docker or a proxy.)

We understand if you restore OctoPrint backups to install new OctoPrints. For that reason, we've introduced two unique IDs (UUID).
- AUTOGENERATED `persistence_uuid`: a unique identifier stored in the plugin folder in `device.json`, which is excluded from backups to prevent duplicate printers. Don't adjust this if you don't understand it.
- AUTOGENERATED `device_uuid`: a unique identifier stored in the `config.yaml` at startup. Don't adjust this if you don't understand it.

Periodic updates
- OPTIONAL `ping`: the time in seconds between each call to FDM Monster (default is 15 * 60, or 15 minutes)

The `ping` setting specifies the frequency at which the plugin will send updates to FDM Monster. The default is every 15 minutes, but you can adjust this value if you prefer a different update frequency.

## Conclusion

FDM Connector is an OctoPrint plugin that simplifies the initial connection to FDM Monster and offers future features such as filament usage tracking and tunnel connection setup. The plugin is currently in the alpha stage and requires the plugin system on FDM Monster, which is not yet released. If you have any feature requests, bugs, or ideas, please visit the [FDM Connector Discussions page](https://github.com/fdm-monster/fdm-connector/discussions).
