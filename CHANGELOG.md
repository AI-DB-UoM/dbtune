# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

## [0.1.3] - 2026-05-14

### Added
- Added CI coverage for CoLSE extension build (`make -C dbtune_pg_colse_extension clean all`).
- Added CI Docker verification for the combined PostgreSQL image (`docker/postgres-with-extensions.Dockerfile`).
- Added CI checks to create both `dbtune_mab` and `dbtune_colse` extensions in PostgreSQL.

### Changed
- Upgraded C-extension CI to validate both extension modules instead of only `dbtune_mab`.
- Extended README with hmab + CoLSE dual-enable workflow and verification commands.

## [0.1.2] - 2026-05-14

### Added
- Added `colse_service/` FastAPI service scaffold for CoLSE estimate endpoint integration.
- Added `dbtune_pg_colse_extension/` PostgreSQL C extension with query hook and `dbtune_colse_estimate(text)` bridge function.
- Added `docker/postgres-with-extensions.Dockerfile` to build a PostgreSQL image that preloads both `dbtune_mab` and `dbtune_colse`.

### Changed
- Updated `docker-compose.yml` to build PostgreSQL from the combined extension image context.
- Added `colse_api` service on port `5060` with health checks to the default compose stack.

### Notes
- CoLSE service behavior is currently a stub estimator for integration flow validation.

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
