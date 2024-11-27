load("@aspect_rules_lint//lint:ruff.bzl", "lint_ruff_aspect")
load("@rules_mypy//mypy:mypy.bzl", "mypy")

mypy_aspect = mypy(
    mypy_cli = "@@//bazel/tools:mypy_cli",
    mypy_ini = "@@//:pyproject.toml",
    suppression_tags = ["no-mypy"],
)

ruff = lint_ruff_aspect(
    binary = "@multitool//tools/ruff",
    configs = [
        "@@//:pyproject.toml",
    ],
)

ruff_isort = lint_ruff_aspect(
    binary = "@multitool//tools/ruff",
    configs = [
        "@@//bazel/tools:pyproject.isort.toml",
    ],
)
