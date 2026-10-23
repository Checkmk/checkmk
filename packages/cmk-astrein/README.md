# Astrein

**Astrein** is a code quality checker for Checkmk, built on Python's `ast` module and integrated with Bazel.
It was introduced as replacement for pylint. It's current core functionality is the layer checker.

## What It Does

Astrein enforces code quality rules through specialized checkers.
Run `bazel run //packages/cmk-astrein:astrein -- --help` for the current list.

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
bazel lint //cmk/...

# Only run astrein linter
bazel build --aspects //bazel/tools:aspects.bzl%astrein //cmk/...

# Machine-readable output (SARIF format)
bazel lint --machine //cmk/...
```

## Suppressing Violations

Add inline comments to suppress specific violations:

```python
# astrein: disable=localization
translated = _(variable_text)

result = _(dynamic_string)  # astrein: disable=localization
```

The id is the one shown in brackets in the error message.
A suppression that does not suppress anything is reported as `unused-suppression`, so stale suppressions get removed.
Suppressions for checkers that did not run (`--checker <name>`) are not judged.

## LSP Server

Astrein provides an LSP server for real-time linting diagnostics in editors.

### Running the LSP Server

```bash
bazel run //packages/cmk-astrein:astrein-lsp
```

Options:

- `--repo-root`: Override the workspace root (optional, uses client workspace by default)
- `--log-file`: Log file path for debugging
- `--log-level`: Log level (DEBUG, INFO, WARNING, ERROR)

### Editor Integration

#### Neovim

Create `~/.config/nvim/lsp/astrein.lua`:

```lua
return {
    cmd = {
        "bazel",
        "run",
        "//packages/cmk-astrein:astrein-lsp",
        "--",
    },
    filetypes = { "python" },
    root_markers = { ".git", "pyproject.toml" },
}
```

Then enable it in your LSP config:

```lua
vim.lsp.enable({ "astrein" })
```

#### VSCode

Install the "Generic LSP Client (v2)" extension and add to your `settings.json`:

```json
{
  "glspc.server.command": "bazel",
  "glspc.server.commandArguments": ["run", "//packages/cmk-astrein:astrein-lsp", "--"],
  "glspc.server.languageId": ["python"]
}
```

#### PyCharm

Unfortunately we haven't found a way to integrate Astrein as LSP server in PyCharm yet.
So, the best way is to configure it's command line interface as an
[external tool](https://www.jetbrains.com/help/pycharm/configuring-third-party-tools.html).

Program: `scripts/run-uvenv`
Arguments: `bazel run //packages/cmk-astrein:astrein -- --checker all $FilePath$ --repo-root $ContentRoot$`
Working directory: `$ProjectFileDir$`

If you have a better approach, please reach out!

## Architecture

```
cmk/astrein/
  checkers/        one module or package per checker
  framework.py     checker base class and the finding type
  suppressions.py  parses # astrein: disable=<id> comments
  engine.py        runs the checkers and applies suppressions
  registry.py      discovers all checkers
  output/          gcc and SARIF formats
  cli.py           command line frontend, used by the Bazel aspect
  lsp.py           LSP frontend for editors
```

Checkers import only `framework.py` and each other, and nothing imports the frontends `cli.py` and `lsp.py`.

### Adding a checker

1. Add `checkers/<name>.py` with a subclass of `ASTVisitorChecker` that sets `checker_id` and `summary`.
2. Add `tests/checkers/test_<name>.py`.

Astrein, every time.
