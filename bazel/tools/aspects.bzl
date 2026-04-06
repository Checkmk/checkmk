"""Lint aspect definitions for mypy, bandit, ruff, clang-tidy, astrein, and groovy."""

load("@aspect_rules_lint//lint:bandit.bzl", "lint_bandit_aspect")
load("@aspect_rules_lint//lint:clang_tidy.bzl", "lint_clang_tidy_aspect")
load("@aspect_rules_lint//lint:clippy.bzl", "lint_clippy_aspect")
load("@aspect_rules_lint//lint:eslint.bzl", "lint_eslint_aspect")
load("@aspect_rules_lint//lint:groovy.bzl", "lint_groovy_aspect")
load("@aspect_rules_lint//lint:ruff.bzl", "lint_ruff_aspect")
load("@aspect_rules_lint//lint:shellcheck.bzl", "lint_shellcheck_aspect")
load("@aspect_rules_lint//lint:stylelint.bzl", "lint_stylelint_aspect")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@cmk_types//:types.bzl", "types")
load("@rules_mypy//mypy:mypy.bzl", "mypy")
load("//bazel/tools:lint_astrein.bzl", "lint_astrein_aspect")
load("//bazel/tools:lint_license_header.bzl", "lint_license_header_aspect")
load("//bazel/tools:lint_py_import_cycles.bzl", "lint_py_import_cycles_aspect")

eslint = lint_eslint_aspect(
    binary = Label(":eslint"),
    configs = [Label("//:eslintrc")],
    rule_kinds = ["js_library", "ts_project", "ts_project_rule", "js_run_binary"],
)

clippy = lint_clippy_aspect(
    config = Label("//:.clippy.toml"),
)

mypy_aspect = mypy(
    mypy_cli = Label("@//bazel/tools:mypy_cli"),
    mypy_ini = Label("@//:pyproject.toml"),
    # TODO: Re-enable as soon as we have a solution regarding huge execroot folders
    # Reference: https://tribe29.slack.com/archives/C01UJKY2D7Y/p1773328309307479
    cache = False,
    suppression_tags = ["no-mypy"],
    color = False,
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
        ]
    } | {
        # `types-pika-ts` wrongfully resolves `pika-ts` instead of `pika`.
        requirement("pika"): types[requirement("pika-ts")],
        # Add stubs for 3rd party packages we use
        requirement("marshmallow-oneofschema"): Label("@//tests/typeshed:marshmallow-oneofschema-stubs"),
        requirement("pyprof2calltree"): Label("@//tests/typeshed:pyprof2calltree-stubs"),
    },
)

bandit = lint_bandit_aspect(
    binary = Label(":bandit"),
    config = Label("//:pyproject.toml"),
    args = ["--severity-level=medium"],
)

ruff = lint_ruff_aspect(
    binary = Label("@multitool_hub//tools/ruff"),
    configs = [Label("@//:pyproject.toml")],
)

clang_tidy = lint_clang_tidy_aspect(
    binary = Label("//bazel/tools:clang_tidy"),
    global_config = [Label("//:.clang-tidy")],
    gcc_install_dir = [Label("@gcc-linux-x86_64//:x86_64-buildroot-linux-gnu")],
    deps = [Label("@gcc-linux-x86_64//:x86_64-buildroot-linux-gnu")],
)

astrein = lint_astrein_aspect(
    binary = Label("//packages/cmk-astrein:astrein"),
)

py_import_cycles = lint_py_import_cycles_aspect(
    binary = Label("//bazel/tools:py-import-cycles"),
    options = ["--strategy", "johnson", "--threshold", "0"],
)

groovy = lint_groovy_aspect(
    binary = Label("//bazel/tools:groovy-lint"),
    config = Label("//bazel/tools:.groovylintrc.json"),
)

shellcheck = lint_shellcheck_aspect(
    binary = Label("@aspect_rules_lint//lint:shellcheck_bin"),
    config = Label("@//:.shellcheckrc"),
)

stylelint = lint_stylelint_aspect(
    binary = Label(":stylelint"),
    config = Label("//:stylelintrc"),
    filegroup_tags = ["stylelint"],
)

license_header_checker = lint_license_header_aspect(
    binary = Label("//bazel/tools:license_header_checker"),
)
