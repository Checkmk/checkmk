load("@aspect_rules_lint//lint:ruff.bzl", "lint_ruff_aspect")
load("@aspect_rules_lint//lint:lint_test.bzl", "lint_test")

ruff = lint_ruff_aspect(
    binary = "@multitool//tools/ruff",
    configs = [
        "@@//packages/cmk-agent-based:pyproject.toml",
    ],
)

ruff_test = lint_test(aspect = ruff)
