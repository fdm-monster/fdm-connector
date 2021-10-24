# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0-rc1-build3]

### Added
    - Test configuration and announcing with coverage up to 92%.

### Changed

### Removed

### Fixed
    - Abstracted state variable and accessor keys


## [0.1.0-rc1-build2]

### Added

### Changed

### Removed

### Fixed
    - #10 README fixed about settings saved to `config.yaml`
    - #11 Plugin URL was incorrect
    - #12 Password field wasnt hidden


## [0.1.0-rc1]

### Added
    - Feature: add unique key `device_uuid` to `config.yaml` to recognize the device
    - Feature: store backup-excluded unique key `perrsistence_uuid` to data folder to see when backups are restored
    - Feature: announce the OctoPrint device automatically using OpenID Connect with `client_credentials` as auth flow.
    - Feature: add settings and navbar templates to OctoPrint
