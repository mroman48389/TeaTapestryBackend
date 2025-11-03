# TeaTapestryBackend
Backend for Tea Tapestry app

Current version: `v1.0.0`

### Versioning Strategy
- All breaking changes will trigger a new major version (`v2`, `v3`, etc.)
- Minor updates and new features will increment the minor version (`v1.1`, `v1.2`, etc.)
- Bug fixes will increment the patch version (`v1.0.1`, `v1.0.2`, etc.)

### Upgrade Instructions
- Clients using `/api/v1/` will remain supported until deprecated
- To upgrade, switch your base URL to `/api/v2/` and review the changelog below

### Changelog
#### v1.0.0
- Initial release
- `/version` endpoint added
<!-- - `/api/v1/teas` returns static list of teas -->