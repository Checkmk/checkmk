load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "plugins",
    srcs = glob(["**/*.py"]),
    args = [
        "--random-order-bucket=global",
    ],
    data = glob(
        include = [
            "**/_check_form_submit_response",
            "**/*.json",
            "**/*.yaml",
        ],
    ),
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/legacy_checks",
        "//cmk/plugins",
        "//packages/cmk-plugins:azure_deprecated",
        "//tests/testlib/common:repo",
        "//tests/testlib/unit",
        requirement("exchangelib"),
        requirement("feedparser"),
        requirement("polyfactory"),
        requirement("pysmb"),
        requirement("pytest-mock"),
        requirement("pytest-asyncio"),
        requirement("pytest-random-order"),
        requirement("python-snap7"),
        requirement("requests"),
        requirement("responses"),
        requirement("time-machine"),
        requirement("vcrpy"),
    ],
)
