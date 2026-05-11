# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog, and this project follows Semantic Versioning.

## [0.1.0] - 2026-05-11

### Added
- Added project release baseline with `VERSION` file.
- Added health endpoint `GET /health` for API service readiness checks.
- Added `CHANGELOG.md` and release tracking process in repository.
- Added pytest marker configuration for integration tests.

### Changed
- Updated Docker API image default command from `main:app` to `app:app`.
- Improved Docker Compose with health checks for PostgreSQL, Redis, and API.
- Stabilized test suite behavior by converting return-based tests to assert/skip style.
- Guarded API query endpoints against empty `query` payloads.
- Made SQL blacklist file loading robust to working directory differences.

### Fixed
- Fixed service startup blocker in `TuneManager` (`BanditTuner` unresolved reference during API init).
- Fixed backward-compatibility for `PgIndexRead`/`PgIndexWrite` imports.
- Removed pytest warning flood from non-standard test return values.

### Notes
- This version is a baseline release focused on environment stability and development workflow.
- External dependencies (local PostgreSQL, Redis, async worker) may still be skipped in tests when unavailable.
