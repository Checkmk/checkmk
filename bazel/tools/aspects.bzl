load("@aspect_rules_lint//lint:clang_tidy.bzl", "lint_clang_tidy_aspect")
load("@aspect_rules_lint//lint:ruff.bzl", "lint_ruff_aspect")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@cmk_types//:types.bzl", "types")
load("@rules_mypy//mypy:mypy.bzl", "mypy")
load("//bazel/tools:lint_astrein.bzl", "lint_astrein_aspect")

mypy_aspect = mypy(
    mypy_cli = Label("@//bazel/tools:mypy_cli"),
    mypy_ini = Label("@//:pyproject.toml"),
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
