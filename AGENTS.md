# AI Agent Instructions

This file provides guidance to AI agents when working with code in this repository.

## Architecture Overview

Checkmk follows a modular architecture with several key components:

### Core Components

- **cmk/base/**: Core monitoring engine, configuration handling, and host management
- **cmk/gui/**: Web interface and user interaction components
- **cmk/checkengine/**: Check execution framework and result processing
- **cmk/fetchers/**: Data fetching mechanisms (SNMP, agent, piggyback, etc.)
- **cmk/plugins/**: Monitoring plugins and check implementations
- **cmk/utils/**: Shared utilities and helper functions
- **cmk/piggyback/**: Piggyback data handling for host relationships
- **cmk/rrd/**: RRD database interactions for metrics storage
- **cmk/ec/**: Event Console for log monitoring and correlation
- ...

### Supporting Components

- **agents/**: Monitoring agents for various platforms (Linux, Windows, etc.)
- **active_checks/**: Active check implementations
- **notifications/**: Notification plugins and handling
- **packages/**: Modular subprojects with individual build systems (see Package Architecture below)
- **omd/**: OMD (Open Monitoring Distribution) packaging and integration
- **tests/**: Comprehensive test suite including unit, integration, and GUI tests

### Package Architecture

The `packages/` directory contains independent subprojects, each with its own `run` script and Bazel targets:

#### Core Python Packages

- **cmk-ccc/**: Core common components (daemon, debugging, site management)
- **cmk-crypto/**: Cryptographic utilities (certificates, passwords, TOTP)
- **cmk-trace/**: OpenTelemetry tracing integration
- **cmk-messaging/**: RabbitMQ messaging infrastructure
- **cmk-werks/**: Work changelog management and CLI tools
- **cmk-mkp-tool/**: MKP (Monitoring Knowledge Package) management
- **cmk-events/**: Event processing and notification handling
- **cmk-plugin-apis/**: API definitions for plugin development

#### Frontend Packages

- **cmk-frontend-vue/**: Modern Vue.js 3 frontend framework
- **cmk-frontend/**: Legacy frontend assets and webpack build
- **cmk-shared-typing/**: TypeScript type definitions shared between vue frontend and backend

#### Infrastructure Packages

- **cmk-agent-receiver/**: FastAPI service for receiving agent data
- **cmk-agent-ctl/**: Rust-based agent controller
- **cmk-livestatus-client/**: Python client for Livestatus queries
- **cmk-relay-protocols/**: Protocol definitions for relay communication

#### Native/Compiled Packages

- **livestatus/**: C++ Livestatus query interface
- **neb/**: Nagios Event Broker module (C++)
- **unixcat/**: Unix socket communication utility (C++)
- **check-cert/**: SSL/TLS certificate checker (Rust)
- **check-http/**: HTTP/HTTPS checker (Rust)
- **mk-oracle/**: Oracle database monitoring (Rust)
- **mk-sql/**: SQL Server monitoring (Rust)

### Build System

Uses Bazel as the primary build system with Make for legacy compatibility. Each package has individual run scripts with standardized interfaces.

## Common Development Commands

### Python Testing

```bash
# Unit tests
make -C tests test-unit
make -C tests test-unit-all  # Include slow tests

# Code quality and formatting
make -C tests test-ruff
make -C tests test-bandit
make -C tests test-format
make -C tests test-mypy

# Integration and system tests
make -C tests test-integration
make -C tests test-composition
make -C tests test-gui-e2e
make -C tests test-plugins
```

### Package-Specific Development

Each package in `packages/` has its own `run` script with standardized options:

```bash
./run -t                # Run (unit) tests
./run -F                # Check formatting
./run -f                # Format code
./run --lint=all        # Run all linters (mypy,ruff,bandit,semgrep)
./run --all             # Run everything
./run -h                # Get all available commands (might be different per package)
```

## Testing Strategy

### Test Categories

1. **Unit tests**: Fast, isolated component testing (`tests/unit/`)
2. **Integration tests**: Component interaction testing (`tests/integration/`)
3. **Composition tests**: Multi-service integration (`tests/composition/`)
4. **GUI E2E tests**: End-to-end web interface testing (`tests/gui_e2e/`)
5. **Plugin tests**: Monitoring plugin validation (`tests/plugins_*/`)
6. **Agent plugin tests**: Cross-platform agent functionality (`tests/agent-plugin-unit/`)

### Running Tests

- All test commands are prefixed with `make -C tests`
- Docker variants available by adding `-docker` suffix
- Use `PYTEST_ADDOPTS` for additional pytest arguments
- Test results stored in `results/` directory

## Code Structure and Conventions

### Module Organization

- **cmk.base**: Core monitoring functionality, not GUI-dependent
- **cmk.gui**: Web interface and user-facing components
- **cmk.utils**: Shared utilities accessible across components
- **cmk.ec**: Event Console functionality
- Component isolation enforced - GUI cannot import base internals

### Python Standards

- Python 3.12 for main codebase
- Agent plugins: Python 3.4+ compatible, with Python 2.7 auto-conversion
- Type hints required (mypy enforcement)
- Ruff for formatting and linting
- pathlib for file operations
- Context managers for resource handling

## Key Configuration Files

- **pyproject.toml**: Python project configuration, ruff, mypy, pytest settings
- **MODULE.bazel**: Bazel module dependencies and configuration
- **defines.make**: Version and build variable definitions
- **package_versions.bzl**: Centralized version management
- **.bazelrc**: Bazel build configuration
- **constraints.txt**: Python dependency constraints

## Multi-Edition Support

The codebase supports multiple Checkmk editions:

- **CRE** (Raw): Open source base edition
- **CEE** (Enterprise): Commercial with advanced features
- **CCE** (Cloud): Cloud-native monitoring
- **CME** (Managed): Multi-tenant MSP edition
- **CSE** (SaaS): Hosted solution

## Important Development Notes

- Always format, lint and test your code when you are done with a task

## Agent Helper Commands

The following tools should be present in $PATH. If not, prompt the user
to follow the setup at https://wiki.lan.checkmk.net/x/4zBSCQ

### Gerrit Review Comments

To fetch input from Gerrit changes:

```bash
# Fetch unresolved comments from a Gerrit change (latest revision)
gerrit-change-log <change_number>
# Fetch all infos from a Gerrit change (latest revision)
gerrit-change-log [--full] <change_number>

# Examples:
gerrit-change-log 107941
gerrit-change-log https://review.lan.tribe29.com/c/check_mk/+/107941
gerrit-change-log https://review.lan.tribe29.com/c/check_mk/+/107941/2  # specific revision
```

### Jenkins build data

To retrieve CI results

```bash
# usage:
jenkins_build_data.py [-h] [--include INCLUDE] [--download SPEC] [--download-dir DOWNLOAD_DIR] [--json] [-q] url

# Examples:
jenkins_build_data.py https://ci.lan.tribe29.com/job/master/job/test/123
jenkins_build_data.py <url> --include=console,tests --json
jenkins_build_data.py <url> --download=results/python-extensions.txt
```
