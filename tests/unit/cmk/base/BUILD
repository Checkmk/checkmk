load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

filegroup(
    name = "bakery_test_files",
    srcs = glob(["plugins/bakery/test_*.py"]),
    visibility = ["//tests/unit/cmk/base/nonfree/pro:__pkg__"],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
        # pytest-xdist for `--numprocesses=NPROC`
        requirement("pytest-xdist"),
    ],
)

py_test(
    name = "base",
    size = "small",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
        "--random-order-bucket=global",
        "--dist=loadfile",
        "--numprocesses=4",
    ],
    data = ["@//:pyproject.toml"],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        "//tests/unit:conftest",
        "//tests/testlib/common:empty_config",
        "//tests/testlib/common:utils",
        "//tests/testlib/unit",
        # -----------------------------------------
        # TODO: some base tests rely on plugins
        # being discoverable.
        # As long as these tests are not cleaned
        # up (== work with dedicated plugins)
        # we need to add the required plugins here.
        "//cmk/plugins",
        "//cmk/legacy_checks",
        "//packages/cmk-plugins:graylog",
        "//packages/cmk-logwatch:plugins",
        # -----------------------------------------
        requirement("pytest-mock"),
        requirement("pytest-asyncio"),
        requirement("pytest-random-order"),
        requirement("fakeredis"),
        requirement("fastapi"),
        requirement("starlette"),
        requirement("time-machine"),
        requirement("requests"),
        requirement("watchdog"),
    ],
)
