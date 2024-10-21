load("@aspect_rules_lint//lint:ruff.bzl", "lint_ruff_aspect")

ruff = lint_ruff_aspect(
    binary = "@multitool//tools/ruff",
    configs = [
        "@@//packages/cmk-agent-based:pyproject.toml",
    ],
)

ruff_isort = lint_ruff_aspect(
    binary = "@multitool//tools/ruff",
    configs = [
        "@@//packages/cmk-agent-based:ruff.toml",
    ],
)
