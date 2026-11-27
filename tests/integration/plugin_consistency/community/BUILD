load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "community",
    # rules_py only collects tests from the directories of srcs.
    srcs = ["//tests/integration/plugin_consistency/common:tests"],
    deps = [
        # These tests check every plug-in the edition ships.
        # Do not trim this down to individual plug-in packages.
        "//cmk/editions:community",
        "//:pyproject-toml",
        "//tests/integration/plugin_consistency:conftest",
        requirement("pytest-mock"),
    ],
)
