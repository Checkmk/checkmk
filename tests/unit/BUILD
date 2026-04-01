load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "conftest",
    testonly = True,
    srcs = [
        "conftest.py",
        "mocks_and_helpers.py",
    ],
    visibility = [
        ":__subpackages__",
        "//non-free/packages/cmk-bakery:__pkg__",
        "//non-free/packages/cmk-robotmk:__pkg__",
    ],
    deps = [
        "//cmk/base",
        "//cmk/checkengine",
        "//cmk/utils",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//packages/cmk-plugin-apis:agent_based",
        "//tests/testlib/common:repo",
        requirement("fakeredis"),
        requirement("pytest_metadata"),
    ],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
        # pytest-xdist for `--numprocesses=NPROC`
        requirement("pytest-xdist"),
    ],
)

write_file(
    name = "cannot_fail",
    out = "test_cannot_fail.py",
    content = [
        "def test_cannot_fail() -> None:",
        "    assert True",
    ],
)

py_test(
    # Start the collection and load the conftests.  The complexity
    # of those warrants this target.
    name = "smoke",
    size = "small",
    srcs = [
        "__test__.py",
        "test_cannot_fail.py",
    ],
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
    ],
    data = ["@//:pyproject.toml"],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":conftest",
        "//tests:testlib",
    ],
)

py_test(
    name = "repo_community",
    size = "small",
    # This is the "catch all" target. Don't add new stuff here.
    srcs = [
        "__init__.py",
        "__test__.py",
        "agents/plugins/test_user_agent.py",
    ] + glob(
        include = [
            "cmk/*.py",
            "cmk/automations/**/*.py",
            "cmk/bi/**/*.py",
            "cmk/checkengine/**/*.py",
            "cmk/diagnostics/**/*.py",
            "cmk/diskspace/**/*.py",
            "cmk/fields/**/*.py",
            "cmk/inventory/**/*.py",
            "cmk/notifications/**/*.py",
            "cmk/piggyback_hub/**/*.py",
            "cmk/piggyback/**/*.py",
            "cmk/product_usage/**/*.py",
            "cmk/server_side_calls_backend/**/*.py",
            "cmk/snmplib/**/*.py",
            "cmk/special_agents/**/*.py",
            "livestatus/**/*.py",
        ],
        exclude = ["**/nonfree/**"],
    ),
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
        "--random-order-bucket=global",
        "--dist=loadfile",
        "--numprocesses=4",
    ],
    data = ["@//:pyproject.toml"] + glob(
        include = [
            # canned data
            "**/tree_test_data/**",
            "**/*.json",
        ],
        exclude = ["**/*.py"],
    ),
    main = ":__test__.py",
    visibility = ["//tests:__subpackages__"],
    deps = [
        ":__test__",
        ":conftest",
        "//agents/plugins:apache_status",
        "//agents/plugins:nginx_status",
        "//cmk:cmkpasswd",
        "//cmk/legacy_includes",
        "//cmk/product_usage:product_usage_cli",
        "//cmk/special_agents",
        "//packages/cmk-ccc:observer",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugins:lib",
        requirement("exchangelib"),
        requirement("fakeredis"),
        requirement("feedparser"),
        requirement("google-cloud-monitoring"),
        requirement("marshmallow"),
        requirement("polyfactory"),
        requirement("pysmb"),
        requirement("pytest-asyncio"),
        requirement("pytest-mock"),
        requirement("pytest-random-order"),
        requirement("python-snap7"),
        requirement("requests"),
        requirement("responses"),
        requirement("time-machine"),
        requirement("vcrpy"),
        requirement("werkzeug"),
        "//tests/testlib/unit",
    ],
)
