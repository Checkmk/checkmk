# VSCode & Bazel: Local vs CI Parity

## Goal

Achieve the same outcome locally in the IDE as with Bazel in CI.

## Parity Legend

| Status         | Meaning                                                                                            |
| -------------- | -------------------------------------------------------------------------------------------------- |
| Match          | Local tool produces the same result as CI                                                          |
| Version risk   | Same tool, but VSCode extension may bundle a different version than Bazel's pinned hermetic binary |
| Partial        | Mostly works but with known gaps or workarounds needed                                             |
| Broken         | Configured but not working correctly                                                               |
| Not configured | No local IDE integration; only caught in CI                                                        |
| Not evaluated  | No experience yet; needs investigation                                                             |

## Python (.py)

| Task            | CI (Bazel)                          | Local (VSCode)                                | Parity           | Notes                                                                                                                                                                                                         |
| --------------- | ----------------------------------- | --------------------------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Formatting      | ruff (`@multitool_hub`)             | ruff extension (`charliermarsh.ruff`) on save | Match            | Extension uses venv ruff binary (`ruff.path`), same version as CI. Both read `pyproject.toml`.                                                                                                                |
| Linting         | ruff (bazel lint aspect)            | ruff extension on save                        | Match            | Same binary, same config.                                                                                                                                                                                     |
| Import sorting  | ruff isort rules                    | ruff `source.organizeImports` on save         | Match            | Same binary, same rules.                                                                                                                                                                                      |
| Type checking   | mypy (`--config=mypy` bazel aspect) | mypy via dmypy (`matangover.mypy`)            | Partial          | Local runs dmypy with auto-generated `.vscode/.mypy.ini` (from `pyproject.toml`, unsupported options stripped). Uses `--follow-imports=normal` (CI uses `silent`). May show additional errors not seen in CI. |
| Intellisense    | N/A                                 | Pylance (`ms-python.vscode-pylance`)          | Known limitation | Auto-import suggests only one path per symbol; does not prefer `__init__.py` / barrel exports. mypy catches wrong re-exports via `no_implicit_reexport`.                                                      |
| Security        | bandit (bazel lint aspect)          | Not configured                                | Not configured   |                                                                                                                                                                                                               |
| Import cycles   | `py_import_cycles` (custom aspect)  | Not configured                                | Not configured   |                                                                                                                                                                                                               |
| License headers | custom aspect                       | Not configured                                | Not configured   |                                                                                                                                                                                                               |
| Testing         | pytest via bazel                    | pytest via VSCode test explorer               | Partial          | VSCode runs pytest directly (not hermetic). Tests importing bazel-generated packages (`cmk.shared_typing`) require building the venv first.                                                                   |

## TypeScript / JavaScript (.ts, .js, .tsx, .jsx)

| Task           | CI (Bazel)                                       | Local (VSCode)                                        | Parity  | Notes                                                                                                                                                                   |
| -------------- | ------------------------------------------------ | ----------------------------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Formatting     | prettier (npm, via bazel format)                 | prettier extension (`esbenp.prettier-vscode`) on save | Match   | Auto-generated `.vscode/.prettier.config.cjs` from `bazel/tools/prettier.config.cjs`, replacing `require()` with string-based plugin loading. Same config, same output. |
| Linting        | eslint (bazel lint aspect, `eslint.config.mjs`)  | eslint extension (`dbaeumer.vscode-eslint`)           | Match   | Flat config enabled (`eslint.useFlatConfig`). Root `eslint.config.mjs` dynamically loads package configs. Auto-fix on save via `source.fixAll.eslint`.                  |
| Import sorting | prettier `@trivago/prettier-plugin-sort-imports` | Same via prettier extension                           | Match   |                                                                                                                                                                         |
| Type checking  | `ts_project` / `vue-tsc` via bazel               | VSCode TS server with workspace SDK                   | Match   | `js/ts.tsdk.path` points to workspace `node_modules/typescript/lib`. Same version as Bazel.                                                                             |
| Intellisense   | N/A                                              | VSCode TS server + Volar                              | Match   | Works after building shared-typing to generate types.                                                                                                                   |
| Testing        | vitest via bazel                                 | vitest extension (`vitest.explorer`)                  | Partial | Follows `bazel-*` symlinks during discovery. Mitigated by `vitest.configSearchPatternExclude`. Requires building Vitest dependencies first.                             |

## Vue (.vue)

| Task          | CI (Bazel)                    | Local (VSCode)                                     | Parity | Notes                                                                            |
| ------------- | ----------------------------- | -------------------------------------------------- | ------ | -------------------------------------------------------------------------------- |
| Formatting    | prettier (via bazel format)   | prettier extension on save                         | Match  | Same auto-generated config as TS/JS.                                             |
| Linting (JS)  | eslint (bazel lint aspect)    | eslint extension                                   | Match  | Same flat config as TS/JS. Auto-fix on save.                                     |
| Linting (CSS) | stylelint (bazel lint aspect) | stylelint extension (`stylelint.vscode-stylelint`) | Match  | Both read `.stylelintrc.mjs`.                                                    |
| Type checking | `vue-tsc` via bazel           | Volar extension (`Vue.volar`)                      | Match  | Volar uses workspace TypeScript via `typescript.tsdk`. Same TS version as Bazel. |
| Intellisense  | N/A                           | Volar                                              | Match  |                                                                                  |

## CSS / SCSS (.css, .scss)

| Task       | CI (Bazel)                    | Local (VSCode)             | Parity | Notes                         |
| ---------- | ----------------------------- | -------------------------- | ------ | ----------------------------- |
| Formatting | prettier (via bazel format)   | prettier extension on save | Match  |                               |
| Linting    | stylelint (bazel lint aspect) | stylelint extension        | Match  | Both read `.stylelintrc.mjs`. |

## Rust (.rs)

| Task         | CI (Bazel)                                        | Local (VSCode)               | Parity       | Notes                                                                                                                                                                                                                               |
| ------------ | ------------------------------------------------- | ---------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Formatting   | rustfmt via `rules_rust` 0.68.1 (hermetic 1.90.0) | rust-analyzer format on save | Version risk | Both use default config (no `.rustfmt.toml`). Bazel pins rustfmt to Rust 1.90.0; local uses per-package `rust-toolchain.toml` (1.87 for check-cert/check-http, 1.90.0 for others). Different rustfmt versions can differ in output. |
| Linting      | clippy via `aspect_rules_lint` v2.0.0             | rust-analyzer + clippy       | Version risk | Both read `.clippy.toml` (effectively empty, defaults). Same version mismatch as formatting. CI fails on violations (patched `clippy_fail_on_violation`); locally they appear as warnings only.                                     |
| Intellisense | N/A                                               | rust-analyzer                | Match        | Configured via `rust-analyzer.linkedProjects` (check-cert, check-http, cmk-agent-ctl, mk-oracle, mk-sql). Requires matching toolchains (1.87 / 1.90.0) installed via `rustup`.                                                      |

## Starlark / BUILD (.bzl, BUILD)

| Task         | CI (Bazel)                    | Local (VSCode)                              | Parity | Notes |
| ------------ | ----------------------------- | ------------------------------------------- | ------ | ----- |
| Formatting   | buildifier (via bazel format) | bazel extension (`BazelBuild.vscode-bazel`) | Match  |       |
| Linting      | buildifier warnings           | bazel extension                             | Match  |       |
| Intellisense | N/A                           | bazel extension (Starlark LSP)              | Match  |       |

## C / C++ (.cc, .h, .cpp)

| Task         | CI (Bazel)                     | Local (VSCode) | Parity        | Notes                                              |
| ------------ | ------------------------------ | -------------- | ------------- | -------------------------------------------------- |
| Formatting   | clang-format                   | Not configured | Not evaluated | Needs clangd extension.                            |
| Linting      | clang-tidy (bazel lint aspect) | Not configured | Not evaluated | Needs clangd + `compile_commands.json` from Bazel. |
| IWYU         | `--config=iwyu` (bazel)        | Not configured | Not evaluated |                                                    |
| Intellisense | N/A                            | Not configured | Not evaluated | Needs clangd + `compile_commands.json`.            |

## Shell (.sh)

| Task       | CI (Bazel)                     | Local (VSCode) | Parity         | Notes                                            |
| ---------- | ------------------------------ | -------------- | -------------- | ------------------------------------------------ |
| Formatting | shfmt (via bazel format)       | Not configured | Not configured | Could add `foxundermoon.shell-format` extension. |
| Linting    | shellcheck (bazel lint aspect) | Not configured | Not configured | Could add `timonwong.shellcheck` extension.      |

## Groovy (.groovy)

| Task       | CI (Bazel)                   | Local (VSCode) | Parity         | Notes |
| ---------- | ---------------------------- | -------------- | -------------- | ----- |
| Formatting | npm-groovy-lint (via bazel)  | Not configured | Not configured |       |
| Linting    | groovy linter (bazel aspect) | Not configured | Not configured |       |

## TOML (.toml)

| Task       | CI (Bazel)               | Local (VSCode) | Parity         | Notes                                           |
| ---------- | ------------------------ | -------------- | -------------- | ----------------------------------------------- |
| Formatting | taplo (via bazel format) | Not configured | Not configured | Could add `tamasfe.even-better-toml` extension. |

## HTML / Jinja (.html, .jinja2)

| Task       | CI (Bazel)                | Local (VSCode)                               | Parity | Notes                                                                                                             |
| ---------- | ------------------------- | -------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------- |
| Formatting | djlint (via bazel format) | djlint extension (`monosans.djlint`) on save | Match  | Extension uses venv djlint binary (`djlint.useVenv`), same version (1.36.4) as CI. Both use defaults (no config). |

## Markdown (.md)

| Task       | CI (Bazel)                  | Local (VSCode)             | Parity | Notes |
| ---------- | --------------------------- | -------------------------- | ------ | ----- |
| Formatting | prettier (via bazel format) | prettier extension on save | Match  |       |

## JSON / JSONC (.json, .jsonc)

| Task               | CI (Bazel)                  | Local (VSCode)                 | Parity | Notes |
| ------------------ | --------------------------- | ------------------------------ | ------ | ----- |
| Formatting (JSON)  | prettier (via bazel format) | prettier extension on save     | Match  |       |
| Formatting (JSONC) | —                           | VSCode built-in JSON formatter | Match  |       |

## Summary: Root Causes of Divergence

| Cause                                 | Impact                                                                                                                                                                   | Mitigation                                                                                                                                                                                                     |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ~~ESLint `bazel-*` symlink scanning~~ | Resolved. Flat config mode (`eslint.useFlatConfig`) with root `eslint.config.mjs` works correctly.                                                                       | No action needed. ESLint validates JS, TS, and Vue files; auto-fixes on save.                                                                                                                                  |
| **Pylance single import suggestion**  | Shows only one auto-import source per symbol; does not prefer barrel exports.                                                                                            | mypy catches `no_implicit_reexport` violations. Manual correction when accepting wrong suggestions.                                                                                                            |
| **Bazel-generated packages**          | `cmk-shared-typing`, `cmk-frontend` don't exist until built. Breaks import resolution, test discovery, type checking.                                                    | Build and symlink before working locally. Status bar auto-detects stale targets.                                                                                                                               |
| **Version drift**                     | VSCode extensions may bundle their own tool binaries.                                                                                                                    | Mitigated: ruff uses venv binary (`ruff.path`), buildifier uses explicit path, TypeScript pinned via `js/ts.tsdk.path`, prettier/mypy configs auto-generated. Remaining risk: Rust toolchain (rustfmt/clippy). |
| **mypy `follow_imports` override**    | Local dmypy requires `--follow-imports=normal` (CI uses `silent`). May surface additional errors.                                                                        | Accept as extra strictness locally, or filter known false positives.                                                                                                                                           |
| **mypy config generation**            | `pyproject.toml` may contain options unsupported by the local mypy version.                                                                                              | Auto-generated `.vscode/.mypy.ini` strips unsupported options. Regenerates on `pyproject.toml` change.                                                                                                         |
| **Prettier config generation**        | Bazel's `prettier.config.cjs` uses `require()` which VSCode extension doesn't support.                                                                                   | Auto-generated `.vscode/.prettier.config.cjs` replaces `require()` with string-based loading. Regenerates on source change.                                                                                    |
| **Rust toolchain mismatch**           | Bazel pins Rust 1.90.0 hermetically; `rust-toolchain.toml` pins 1.87 for check-cert/check-http. Different versions produce different rustfmt output and clippy warnings. | Install both toolchains via `rustup`. Note: `rust-toolchain.toml` says "must be in sync with MODULE.bazel" but check-cert/check-http are currently out of sync.                                                |
| **Rust clippy CI strictness**         | CI patches `clippy_fail_on_violation` so clippy warnings fail the build. Locally they appear as warnings only.                                                           | Review rust-analyzer Problems panel before pushing. No local equivalent of fail-on-violation.                                                                                                                  |
| **Missing integrations**              | Shell, C++, Groovy, TOML have no VSCode tooling configured.                                                                                                              | Add extensions or accept CI-only coverage.                                                                                                                                                                     |

## Recommended Workflow

1. Use VSCode formatting/linting on save for fast feedback.
2. Before committing, run `bazel run //:format <changed-paths>` to ensure CI-identical formatting.
3. Run `bazel lint --fix` to catch lint issues that VSCode extensions might miss.
4. For Python type checking, run `bazel build --config=mypy //path:target` for CI-identical results.
