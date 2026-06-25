load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "validation",
    srcs = ["test_validate_werks.py"],
    data = [
        "//:defines.make",
        "//.werks",
        "//.werks:werks_config",
    ],
    deps = [
        "//cmk/utils",
        "//cmk/utils:werks",
        "//packages/cmk-werks",
        "//tests/code_quality:bazel_utils",
    ],
)

py_cmk_test(
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
    tags = [
        "no-sandbox",
        "requires-git",
    ],
    deps = [
        requirement("gitpython"),
        "//:pyproject-toml",
        "//cmk/utils",
        "//cmk/utils:werks",
        "//packages/cmk-ccc:version",
        "//packages/cmk-werks",
        "//tests/code_quality:bazel_utils",
    ],
)
