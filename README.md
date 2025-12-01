# TeaTapestryBackend

> Currently provides endpoints for retrieving tea profile data for the Tea Tapestry app.

# Purpose

> Provides endpoints for retrieving data on teas and manages user sessions.

# Stack

> Python, FastAPI, PostgreSQL, SQLAlchemy, Pandas, Pytest, Ruff, PowerShell.

# Features

- TeaProfile model schema for describing teas.
- Seeding and ingestion pipeline for tea profiles utilizing SQLAlchemy ORM, Pandas, and PostgreSQL.
- PowerShell scripts for seeding, ingestion, testing, linting, and general development.
- Linting with Ruff.
- 100% testing coverage with Pytest.

# Installation and Setup

	git clone https://github.com/mroman48389/TeaTapestryBackend.git
	Set-Location TeaTapestryBackend
	pip install -r requirements.txt
	
# Testing

> Currently done via SQLite databases along with mock tests to cover Postgres branches.

# Versioning

- **Major** (`v2`, `v3`, etc.): Breaking changes.
- **Minor** (`v1.1`, `v1.2`, etc.): New features and minor updates.
- **Patch** (`v1.0.1`, `v1.0.2`, etc.): Bug fixes.

# Upgrade Instructions

- Clients using `/api/v1/` will remain supported until deprecated.
- To upgrade, switch your base URL to `/api/v2/`, and review the changelog below.

# Changelog

> **v1.0.0**
> - Initial release.
> - `/version` endpoint added.