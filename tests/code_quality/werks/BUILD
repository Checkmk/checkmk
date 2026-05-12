load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "validation",
    srcs = ["test_validate_werks.py"],
    data = [
        "//:defines.make",
        "//.werks",
        "//.werks:werks_config",
    ],
    pytest_main = True,
    deps = [
        requirement("pytest"),
        "//cmk/utils",
        "//packages/cmk-werks",
        "//tests/code_quality:bazel_utils",
    ],
)

py_test(
    name = "werks",
    srcs = [
        "test_werks.py",
        "test_werks_commands.py",
    ],
    data = [
        "//:defines.make",
        "//.werks",
        "//.werks:werks_config",
    ],
    imports = ["../../.."],
    # This test requires git, however, adding git as a dependency
    # would constantly invalidate the cache, forgoing most advantages
    # of running in Bazel.  Instead, we depend on `//.werks` and run
    # outside of the sandbox.
    pytest_main = True,
    tags = [
        "manual",
        "no-sandbox",
    ],
    deps = [
        requirement("gitpython"),
        requirement("pytest"),
        "//:pyproject-toml",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        "//packages/cmk-werks",
        "//tests/code_quality:bazel_utils",
    ],
)
