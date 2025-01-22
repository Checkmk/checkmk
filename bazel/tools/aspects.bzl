load("@aspect_rules_lint//lint:ruff.bzl", "lint_ruff_aspect")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@cmk_types//:types.bzl", "types")
load("@rules_mypy//mypy:mypy.bzl", "mypy")

mypy_aspect = mypy(
    mypy_cli = "@@//bazel/tools:mypy_cli",
    mypy_ini = "@@//:pyproject.toml",
    suppression_tags = ["no-mypy"],
    # `rules_mypy//mypy:types.bzl` mostly takes care of this but needs help with some packages.
    types = {
        pkg: types_pkg
        for pkg, types_pkg in types.items()
        if pkg not in [
            # The types for these are pulled transitively but we don't have/need
            # the corresponding packages.
            requirement("awscrt"),
            requirement("html5lib"),
            requirement("pika-ts"),
            requirement("simplejson"),
        ]
    } | {
        # `types-pika-ts` wrongfully resolves `pika-ts` instead of `pika`.
        requirement("pika"): types[requirement("pika-ts")],
    },
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
