# Astrein

**Astrein** is a code quality checker for Checkmk, built on Python's `ast` module and integrated with Bazel.
It was introduced as replacement for pylint. It's current core functionality is the layer checker.

## What It Does

Astrein enforces code quality rules through specialized checkers:

- **localization**: Validates localization function calls (e.g., `_()`, `Title()`) use literal strings and allowed HTML tags
- **module-layers**: Enforces architectural boundaries between Checkmk components (e.g., prevents GUI from importing base internals)

## Usage

### Command Line

```bash
# Check a single file
bazel run //packages/cmk-astrein:astrein -- --checker localization cmk/gui/groups.py

# Check a directory recursively
bazel run //packages/cmk-astrein:astrein -- --checker module-layers cmk/gui

# Run all checkers
bazel run //packages/cmk-astrein:astrein -- --checker all cmk

# Specify repository root (required for module-layers)
bazel run //packages/cmk-astrein:astrein -- --checker module-layers --repo-root . cmk/gui/main.py
```

### Bazel Integration

Astrein integrates with `bazel_rules_lint` as a Bazel aspect. Targets without the `no-astrein` tag are automatically linted:

```bash
# Lint specific target (human-readable output)
bazel lint //cmk:lib_cmk_repo

# Only run astrein linter
bazel build --aspects //bazel/tools:aspects.bzl%astrein //cmk:lib_cmk_repo

# Machine-readable output (SARIF format)
bazel lint --machine //cmk:lib_cmk_repo
```

## Suppressing Violations

Add inline comments to suppress specific violations:

```python
# astrein: disable=localization
translated = _(variable_text)

result = _(dynamic_string)  # astrein: disable=localization
```

## Architecture

- **framework.py**: Core AST visitor framework and error handling
- **cli.py**: Command-line interface and file discovery
- **checker_localization.py**: Localization validation logic
- **checker_module_layers.py**: Module layer architecture enforcement
- **sarif.py**: SARIF output formatting
- **config/**: Checker-specific configuration (layer rules, etc.)

Astrein, every time.
