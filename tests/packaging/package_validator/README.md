# Package Validator

A Rust tool for validating `RPATH`/`RUNPATH` settings in `DEB`, `RPM`, and `CMA` packages.

## Overview

`package_validator` analyzes Linux package files (`.deb`, `.rpm`, and `.cma`) to validate that `ELF` binaries and shared libraries have correctly configured `RPATH` or `RUNPATH` settings. It extracts packages, identifies `ELF` files, checks their dynamic dependencies, and verifies that all required shared libraries can be resolved through the configured `RPATH`/`RUNPATH` entries.

## Features

- **Package Extraction**: Supports `DEB`, `RPM`, and `CMA` package formats
- **ELF Analysis**: Automatically finds and analyzes all `ELF` file types:
  - Executable binaries
  - Shared libraries (.so files)
  - Relocatable object files (.o files)
  - Core dump files
  - Other ELF file types
- **RPATH Validation**: Validates `RPATH` and `RUNPATH` settings for proper dependency resolution
- **Dependency Checking**: Verifies that all required shared libraries can be found via `RPATH`/`RUNPATH` or system paths
- **Dependency Classification**: Classifies dependencies as:
  - **System**: Dependencies provided by the operating system (matched via exact dependency names)
  - **Package**: Dependencies found within the package itself
  - **Unknown**: Dependencies not found and not classified as system dependencies
- **System Dependency Configuration**: Supports configuration file for identifying system dependencies using exact dependency names
- **JSON Reports**: Generates detailed JSON reports with validation results and statistics
- **Symlink Handling**: Properly handles symlinks, resolves their targets, and detects symlink cycles
- **$ORIGIN Support**: Supports `$ORIGIN`and`${ORIGIN}`substitution in`RPATH` entries
- **Path Normalization**: Handles paths with `..` components and relative paths
- **Parallel Processing**: Uses parallel processing for efficient analysis of large packages

## Installation

### Building from Source

```bash
cargo build --release
```

The binary will be available at `target/release/package_validator`.

### System Dependencies

The tool requires system utilities for package extraction:

- **For DEB packages**: `dpkg-deb` (usually provided by `dpkg` package)
- **For RPM packages**: `rpm2cpio` and `cpio` (usually provided by `rpm` package)
- **For CMA packages**: `tar` (usually pre-installed)

On Debian/Ubuntu:

```bash
sudo apt-get install dpkg rpm
```

## Usage

### Basic Usage

```bash
package_validator <PACKAGE> <REPORT>
```

Where:

- `<PACKAGE>`: Path to the package file (`.deb`, `.rpm`, or `.cma`) to validate
- `<REPORT>`: Path to the file where the JSON report will be written

### Options

- `--system-dependencies <FILE>`: Path to a text file containing exact dependency names for known system dependencies. Each line contains an exact dependency name. Empty lines and lines starting with `#` are ignored. Dependencies matching these names exactly will be classified as system dependencies rather than missing.

### Examples

**Validate a DEB package:**

```bash
package_validator check-mk-community-2.5.0.deb report.json
```

**Validate an RPM package:**

```bash
package_validator check-mk-ultimatemt-2.5.0.rpm report.json
```

**Validate a CMA package:**

```bash
package_validator check-mk-pro-2.5.0-4-x86_64.cma report.json
```

**Validate with system dependencies file:**

```bash
package_validator mypackage.deb report.json --system-dependencies system-dependencies.txt
```

The system dependencies file format:

```
# System libraries provided by the OS
libc.so.6
libm.so.6
libpthread.so.0
libdl.so.2
```

### Output

The tool provides two types of output:

1. **Console Output**: Summary tables showing ELF file statistics, dependency classifications, and any missing dependencies

```bash
Package: /path/to/check-mk-community-2.5.0.deb
Total files: 1234

┌──────────────────┬───────┐
│ ELF Type         │ Count │
├──────────────────┼───────┤
│ Binaries         │ 12    │
│ Shared libraries │ 33    │
│ Relocatable      │ 0     │
│ Core             │ 0     │
│ None             │ 0     │
│ Total            │ 45    │
└──────────────────┴───────┘

┌──────────────────┬───────┐
│ Dependency Type  │ Count │
├──────────────────┼───────┤
│ System           │ 150   │
│ Package          │ 200   │
│ Unknown          │ 2     │
│ Total            │ 352   │
└──────────────────┴───────┘

┌──────────────────┬───────┐
│ Dependency Status│ Count │
├──────────────────┼───────┤
│ Missing          │ 2     │
│ Found            │ 350   │
│ Error            │ 0     │
│ Total            │ 352   │
└──────────────────┴───────┘

┌──────────────────────────────────────────┬───────────────────────┐
│ ELF File                                 │ Missing Dependencies  │
├──────────────────────────────────────────┼───────────────────────┤
│ /opt/omd/versions/2.5.0/bin/check_mk     │ libssl.so.3           │
│ /opt/omd/versions/2.5.0/lib/libcrypto.so │ libz.so.1             │
└──────────────────────────────────────────┴───────────────────────┘

Total: 2 ELF file(s) with missing dependencies
```

Progress messages are written to stderr, while the summary tables are written to stdout.

2. **JSON Report**: Detailed validation results written to the specified JSON file

### Exit Codes

The tool exits with:

- `0`: Success - all dependencies resolved or no errors found
- Non-zero: Error occurred or missing dependencies found

### JSON Report Format

The JSON report structure:

```json
{
  "package": "/absolute/path/to/check-mk-community-2.5.0.deb",
  "totals": {
    "files": 1234,
    "elfs": {
      "none": 0,
      "binaries": 12,
      "shared_libraries": 33,
      "relocatable": 0,
      "core": 0,
      "total": 45
    },
    "dependencies": {
      "missing": 2,
      "missing_unique": 2,
      "found": 350,
      "found_unique": 180,
      "error": 0,
      "system": 150,
      "package": 200,
      "unknown": 2,
      "total": 352,
      "total_unique": 182
    }
  },
  "errors": [],
  "dependencies": {
    "/opt/omd/versions/2.5.0/bin/check_mk": {
      "libssl.so.3": {
        "status": "Missing",
        "type": "Unknown",
        "searched_paths": [
          "/opt/omd/versions/2.5.0/lib",
          "/usr/lib/x86_64-linux-gnu",
          "/usr/local/lib",
          "/lib",
          "/lib64",
          "/usr/lib",
          "/usr/lib64"
        ]
      },
      "libcrypto.so.3": {
        "status": "Found",
        "type": "Package",
        "path": "/opt/omd/versions/2.5.0/lib/libcrypto.so.3"
      },
      "libc.so.6": {
        "status": "Found",
        "type": "System",
        "path": "/lib/x86_64-linux-gnu/libc.so.6"
      }
    }
  },
  "files": {
    "/opt/omd/versions/2.5.0/bin/check_mk": {
      "kind": "Executable",
      "dependencies": ["libc.so.6", "libssl.so.3", "libcrypto.so.3"],
      "rpath": [],
      "runpath": ["$ORIGIN/../lib"]
    }
  }
}
```

**Field Descriptions:**

- `package`: Absolute path to the package file that was analyzed
- `totals.files`: Total number of files in the package
- `totals.elfs`: Breakdown of ELF file types:
  - `none`: ELF files with no type
  - `binaries`: Executable binaries
  - `shared_libraries`: Shared library files (.so)
  - `relocatable`: Relocatable object files (.o)
  - `core`: Core dump files
  - `total`: Total ELF files found
- `totals.dependencies`: Dependency statistics:
  - `missing`: Total number of missing dependencies
  - `missing_unique`: Number of unique missing dependencies
  - `found`: Total number of found dependencies
  - `found_unique`: Number of unique found dependencies
  - `error`: Number of dependencies with resolution errors
  - `system`: Dependencies classified as system dependencies
  - `package`: Dependencies found in the package
  - `unknown`: Dependencies not found and not classified as system
  - `total`: Total dependencies analyzed
  - `total_unique`: Total unique dependencies
- `errors`: Array of error messages encountered during analysis (e.g., system dependencies found in package)
- `dependencies`: Map keyed by ELF file path, containing maps of dependency names to resolution results:
  - `status`: `"Found"`, `"Missing"`, or `{"Error": "error message"}` (enum serialized as object for Error variant)
  - `type`: `"System"`, `"Package"`, or `"Unknown"`
  - `path`: Path where dependency was found (only present if `status` is `"Found"`)
  - `searched_paths`: Array of paths that were searched (only present if `status` is `"Missing"`)
- `files`: Map keyed by ELF file path, containing ELF file metadata:
  - `kind`: ELF file type (`"None"`, `"Relocatable"`, `"Executable"`, `"SharedObject"`, or `"Core"`)
  - `dependencies`: Array of dependency names (DT_NEEDED entries)
  - `rpath`: Array of RPATH entries
  - `runpath`: Array of RUNPATH entries

## Development

### Project Structure

```
package_validator/
├── src/
│   ├── main.rs          # CLI entry point
│   ├── lib.rs           # Library root
│   ├── args.rs          # CLI argument parsing
│   ├── package/         # Package extraction and analysis
│   │   ├── mod.rs       # Package struct and public API
│   │   ├── cma.rs       # CMA package extraction
│   │   ├── deb.rs       # DEB package extraction
│   │   ├── rpm.rs       # RPM package extraction
│   │   ├── extractor.rs # Package extraction trait
│   │   ├── elf.rs       # ELF file parsing and analysis
│   │   └── files.rs     # Package file type definitions
│   └── report/                    # Report generation
│       ├── mod.rs                 # Report struct and public API
│       ├── console.rs             # Console output formatting
│       ├── dependency_resolver.rs # Dependency resolution logic
│       ├── errors.rs              # Error types for report validation
│       ├── symlink_resolver.rs    # Symlink resolution logic
│       ├── system_dependencies.rs # System dependency resolver
│       ├── validate.rs            # Report validation
│       ├── utils.rs               # Utility functions
│       └── totals/                # Statistics calculations
│           ├── mod.rs             # Totals struct combining stats
│           ├── dependencies.rs    # Dependency statistics
│           └── elf.rs             # ELF file statistics
├── tests/
│   └── integration_test.rs  # Integration tests
├── fixtures/                # Test fixture files (checked in)
└── Cargo.toml               # Rust project configuration
```

### Running Tests

```bash
# Run all tests
cargo test

# Run with output
cargo test -- --nocapture

# Run specific test
cargo test test_package_integration_report
```

## Technical Details

### How RPATH Validation Works

1. **Package Extraction**: The package is extracted to a temporary directory using system tools (`dpkg-deb` for DEB, `rpm2cpio`/`cpio` for RPM, `tar` for CMA). The temporary directory is cleaned up after analysis.

2. **ELF Discovery**: All files are scanned in parallel to identify ELF files of all types (executables, shared libraries, relocatable objects, core files, etc.).

3. **Dependency Analysis**: For each ELF file, the tool extracts:
   - Dynamic dependencies (DT_NEEDED entries)
   - RPATH entries (DT_RPATH)
   - RUNPATH entries (DT_RUNPATH)

4. **Path Resolution**: For each dependency, the tool determines search paths:
   - First checks if the dependency name is in the system dependencies list (if provided)
   - If found in system dependencies, immediately classifies as **System** dependency (no path searching needed)
   - Otherwise, extracts RPATH/RUNPATH entries from the ELF file (RUNPATH takes precedence over RPATH if both are present)
   - For each RPATH/RUNPATH entry:
     - Validates that the path is either absolute or starts with `$ORIGIN`/`${ORIGIN}`
     - Rejects relative paths without `$ORIGIN` (e.g., `../lib`, `./lib`) as invalid for security reasons
     - Substitutes `$ORIGIN` or `${ORIGIN}` with the directory containing the ELF file
     - Normalizes paths to handle `..` components and resolve to absolute paths

5. **Dependency Resolution**: For each dependency not classified as system:
   - Searches RPATH/RUNPATH paths in order
   - For each search path, checks if the dependency exists in the extracted package files (as a regular file or symlink)
   - If found as a symlink, recursively resolves the symlink chain (detecting cycles)
   - If the resolved target is an ELF file in the package, classifies as **Package** dependency
   - If not found in any search path, marks as **Missing** with type **Unknown**

6. **Symlink Handling**: Symlinks are resolved recursively to find their final targets. The tool detects and reports symlink cycles.

7. **Error Handling**: Errors encountered during extraction or analysis are collected and reported. The tool exits with a non-zero exit code if errors are found or if dependencies are missing.

### $ORIGIN Substitution

The tool supports both `$ORIGIN` and `${ORIGIN}` syntax. The `$ORIGIN` is replaced with the directory containing the ELF file being validated.

Example:

- ELF file: `/opt/app/bin/myapp`
- RPATH: `$ORIGIN/../lib`
- Resolved: `/opt/app/bin/../lib` → `/opt/app/lib`

### Path Normalization

Paths are normalized after `$ORIGIN` substitution to handle `..` components. This ensures that paths like `/opt/app/bin/../lib/../../lib` are correctly resolved to `/opt/lib`.

**Important**: Relative paths without `$ORIGIN` (e.g., `../lib`, `./lib`, `lib`) are **rejected as invalid** and not included in the search paths. This is a security measure, as such paths would be resolved relative to the process's current working directory at runtime, which is unknown at analysis time and creates security risks (binary planting attacks).

## Examples

### Successful Validation

```bash
$ package_validator mypackage.deb report.json
Package: /absolute/path/to/mypackage.deb
Total files: 500

┌──────────────────┬───────┐
│ ELF Type         │ Count │
├──────────────────┼───────┤
│ Binaries         │ 5     │
│ Shared libraries │ 20    │
│ Relocatable      │ 0     │
│ Core             │ 0     │
│ None             │ 0     │
│ Total            │ 25    │
└──────────────────┴───────┘

┌──────────────────┬───────┐
│ Dependency Type  │ Count │
├──────────────────┼───────┤
│ System           │ 50    │
│ Package          │ 100   │
│ Unknown          │ 0     │
│ Total            │ 150   │
└──────────────────┴───────┘

┌──────────────────┬───────┐
│ Dependency Status│ Count │
├──────────────────┼───────┤
│ Missing          │ 0     │
│ Found            │ 150   │
│ Error            │ 0     │
│ Total            │ 150   │
└──────────────────┴───────┘
```

### Validation with Issues

```bash
$ package_validator mypackage.deb report.json
Package: /absolute/path/to/mypackage.deb
Total files: 500

┌──────────────────┬───────┐
│ ELF Type         │ Count │
├──────────────────┼───────┤
│ Binaries         │ 5     │
│ Shared libraries │ 20    │
│ Relocatable      │ 0     │
│ Core             │ 0     │
│ None             │ 0     │
│ Total            │ 25    │
└──────────────────┴───────┘

┌──────────────────┬───────┐
│ Dependency Type  │ Count │
├──────────────────┼───────┤
│ System           │ 50    │
│ Package          │ 98    │
│ Unknown          │ 2     │
│ Total            │ 150   │
└──────────────────┴───────┘

┌──────────────────┬───────┐
│ Dependency Status│ Count │
├──────────────────┼───────┤
│ Missing          │ 2     │
│ Found            │ 148   │
│ Error            │ 0     │
│ Total            │ 150   │
└──────────────────┴───────┘

┌──────────────────────────────────────────┬───────────────────────┐
│ ELF File                                 │ Missing Dependencies  │
├──────────────────────────────────────────┼───────────────────────┤
│ /usr/local/bin/myapp                     │ libmissing.so.1       │
│ /usr/local/lib/libhelper.so              │ libdep.so.2           │
└──────────────────────────────────────────┴───────────────────────┘

Total: 2 ELF file(s) with missing dependencies
```

The tool will exit with a non-zero exit code when missing dependencies are found.
