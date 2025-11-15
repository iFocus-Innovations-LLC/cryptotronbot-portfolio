# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-22

### Added
- **API Integration Tests**: Comprehensive test suite for authentication and portfolio endpoints
- **Security Scanning**: 
  - GitHub Dependabot configuration for automated dependency updates
  - CodeQL security analysis workflow
  - Bandit security linter integration
  - Secret scanning with TruffleHog
- **DeFi API Endpoints**:
  - `/api/defi/stablecoins` - List supported stablecoins
  - `/api/defi/stablecoins/{symbol}` - Stablecoin details
  - `/api/defi/stablecoins/{symbol}/stability` - Stability analysis
  - `/api/defi/yield/opportunities` - All yield opportunities
  - `/api/defi/yield/recommendations` - Personalized recommendations
  - `/api/defi/portfolio/yield-potential` - Portfolio yield calculation
- **MVP Release Plan**: Comprehensive roadmap for secure DeFi pipeline MVP
- **Security Policy**: SECURITY.md with vulnerability reporting process
- **Environment Variables**: Support for JWT_SECRET_KEY and DATABASE_URL via environment

### Changed
- **Dependencies**: Pinned versions for security in requirements.txt and requirements_test.txt
- **Configuration**: Updated app.py to use environment variables for sensitive configuration
- **Test Infrastructure**: Added requirements_test.txt with pytest dependencies

### Fixed
- Test import paths and database setup for API integration tests
- Test fixtures for proper Flask app context handling

### Security
- Environment variable support for JWT_SECRET_KEY (prevents hardcoded secrets)
- Automated vulnerability scanning in CI/CD pipeline
- Dependency version pinning to prevent security vulnerabilities

## [0.1.0] - 2025-01-20

### Added
- Initial release
- Portfolio tracking functionality
- JWT authentication
- CoinGecko API integration
- DeFi stablecoin utilities
- Yield aggregator infrastructure
- Docker and Kubernetes deployment configurations
- Frontend with Sinatra/Ruby
- Backend with Flask/Python

---

[0.2.0]: https://github.com/iFocus-Innovations-LLC/cryptotronbot-portfolio/releases/tag/v0.2.0
[0.1.0]: https://github.com/iFocus-Innovations-LLC/cryptotronbot-portfolio/releases/tag/v0.1.0

