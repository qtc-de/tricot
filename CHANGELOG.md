# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [1.13.0] - Jun 26, 2024

### Added

* Resource based requirements ([docs](/docs/README.md#external-requirements))

### Changed

* Expand `~` in file based validators
* Refactor CI pipeline
* Switch to `pyproject.toml`


## [1.12.0] - Dec 31, 2022

### Changed

* Add support for [inline includes](https://github.com/qtc-de/tricot/tree/main/docs#inline-includes)
* Improved error handling


## [1.11.0] - Aug 07, 2022

### Changed

* Add `cleanup` option to [file_contains validator](https://github.com/qtc-de/tricot/tree/main/docs/validators#filecontainsvalidator)
* Fixed a bug when using *docker volumes* with relative paths
* Improved the error handling of uncaught validator exceptions


## [1.10.2] - Jun 07, 2022

### Changed

* Improve error handling of the [http_listener plugin](/docs/plugins/#httplistenerplugin)
* Improve error handling for yaml related scan errors
* Fix some bugs in the [tempfile plugin](/docs/plugins/#tempfileplugin)


## [1.10.1] - May 25, 2022

### Changed

* Fixed a selection bug when running selective tests (e.g. by using `--groups`). The bug caused unrelated
  tests to run anyway.
* The `--continue-from` and `--skip-until` options can now be used with test identifiers enclosed in brackets
  (as they are displayed during a test run)


## [1.10.0] - Mar 03, 2022

### Added

* Add [tar_contains validator](/docs/validators/#tarcontainsvalidator) to validate contents of a tar file
* Add [zip_contains validator](/docs/validators/#zipcontainsvalidator) to validate contents of a zip file
* Add [tempfile plugin](/docs/plugins/#tempfileplugin) to create temporary files for a test
* Add `init` field for containers. Containers can use it to specify a custom initialization time (default=2)


## [1.9.0] - Dec 26, 2021

### Added

* Testers can now specify [external requirements](https://github.com/qtc-de/tricot/tree/develop/docs#external-requirements)
* Requirements are checked before the tester is run and can contain:
  * Required files (including checksums verification)
  * Required operating system commands
  * Required tricot version
   
### Changed

* Improved the selective test functionalities (`--skip-until`, `--continue-from`, `--ids`, `--groups`, `--exclude`, `--exclude-groups`).
  Skipped tests are now skipped completely and they neither appear in the output nor start their associated containers.
* Fix bug related to KeyboardInterrupts 
* Update test cases to make them more compatible among different distributions


## [1.8.0] - Dec 04, 2021

### Changed

* Variables used in the ``command`` key are now allowed to be lists
* Process timeouts are now implemented using process groups (more compatible)
* When using globs to specify testers, the testers are now executed in id-order
* Improved exception handling


## [1.7.0] - Oct 26, 2021

### Added

* Add ``id_pattern`` attribute (see https://github.com/qtc-de/tricot/tree/main/docs#selective-testing)
* Add ``--skip-until`` and ``--continue-from`` options (see https://github.com/qtc-de/tricot/tree/main/docs#selective-testing)

### Changed

* The ``name`` attribute of testers is no longer parsed. The ``title`` attribute is now
  used as a replacement.


## [1.6.0] - Oct 09, 2021

### Added

* Add test / tester *IDs* (see https://github.com/qtc-de/tricot/tree/main/docs#selective-testing)
* Add *test groups* (see https://github.com/qtc-de/tricot/tree/main/docs#selective-testing)

### Changed

* Full help menu is now always displayed on argparse errors
* Small bugfixes and formatting changes

### Removed

* The `--tester`, `--exclude` and `--number` options were removed.
  They are replaced by the `--ids`, `--groups`, `--exclude-ids` and
  `--exclude-groups` options.


## [1.5.0] - Sep 11, 2021

### Added

* Add [Extractors](/docs/extractors)
* Add ``network_mode`` support for docker containers
* Add additional tests (extractors + network_mode)

### Changed

* Changed the log output format for docker containers
* Changed exception handling of AttributeException in OsCommandPlugin
* Small bug fixes

### Removed

* Removed six dependency (closes #4)
* Removed short version for most options


## [1.4.2] - June 11, 2021

### Changed

* Fix typo within ``tricot.py`` that caused an error when using the ``--tester`` option


## [1.4.1] - May 28, 2021

### Changed

* Fix display bug when commands are run in shell mode
* Add debug information on OsCommand plugins


## [1.4.0] - May 27, 2021

### Added

* Add support for running commands in [shell mode](/docs/README.md#worth-knowing)
* Add logfile attribute for [tests and testers](/docs/README.md#logging)
* Add support for custom [success and error strings](/docs/README.md##custom-strings)


## [1.3.2] - May 24, 2021

### Changed

* Add six dependency to ``setup.py`` file (see #4 for details)


## [1.3.1] - May 24, 2021

### Changed

* Add six dependency to ``requirements.txt`` file (see #4 for details)


## [1.3.0] - May 24, 2021

### Added

* Add support for environment variables within testers
* Add support for nested variables

### Changed

* Small refactroing of runtime variables
* Fix variable inheritance bug
* Add *stream* key to the expected validator keys


## [1.2.0] - May 22, 2021

### Added

* Add *LineCountValidator*
* Add *CleanupCommandPlugin*

### Changed

* Add PyPi istallation instructions
* Some minor bug fixes


## [1.1.0] - May 09, 2021

### Added

* Add PyPi release workflow
* Add support for conditionals
* Add some more documentation

### Changed

* Update completion script
* Fix bug that ``--numbers`` was not working


## [1.0.0] - May 05, 2021

Initial release :)
