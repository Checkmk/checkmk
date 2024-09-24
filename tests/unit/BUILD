load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@cmk_py//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    deps = [
        "//cmk:lib_cmk",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//tests:conftest",
        "//tests:testlib",
        requirement("fakeredis"),
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
    name = "smoke_test",
    out = "test_smoke.py",
    content = [
        "def test_smoke_and_run():",
        "    assert True",
    ],
)

py_test(
    # Start the collection and load the conftests.  The complexity
    # of those warrants this target.
    name = "smoke",
    srcs = [
        ":__test__.py",
        ":smoke_test",
    ],
    args = [
        "--config-file=$(location @//:pyproject.toml)",
    ],
    data = ["@//:pyproject.toml"],
    main = ":__test__.py",
    package_collisions = "ignore",  # "warning"
    deps = [
        ":__test__",
        ":conftest",
        "//cmk:lib_cmk",
        "//tests:conftest",
        "//tests:testlib",
    ],
)

py_test(
    name = "repo",
    # https://bazel.build/reference/be/common-definitions#test.size
    size = "large",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "omdlib/**/*.py",
            "testlib/cse/**/*.py",
            "unit/cmk/cse/**/*.py",
            "**/*pylint*.py",
            "**/*pylint*/**/*.py",
        ],
    ) + ["__test__.py"],
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
        "--random-order-bucket=global",
        "--dist=loadfile",
    ],
    data = ["@//:pyproject.toml"] + glob(
        include = [
            # canned data
            "**/_check_form_submit_response",
            "**/_innovaphone_vcrtrace",
            "**/test-files/**",
            "**/tree_test_data/**",
            "**/*.json",
            "**/*.log",
            "**/*.pem",
            "**/*.xml",
        ],
        exclude = ["**/*.py"],
    ),
    main = ":__test__.py",
    package_collisions = "ignore",  # "warning"
    tags = [
        # TODO:  *Shouldn't* be required in unit tests!
        # `test_diagnostics_element_hw_info_content` and
        # `test_wsgi_router::test_wsgi_app` require "local"
        "local",
    ],
    deps = [
        ":__test__",
        requirement("astroid"),
        requirement("fastapi"),
        requirement("httpx"),
        requirement("hypothesis"),
        requirement("mypy-boto3-logs"),
        requirement("mypy-extensions"),
        requirement("pika"),
        requirement("polyfactory"),
        requirement("pylint"),
        requirement("pytest-mock"),
        requirement("pytest-random-order"),
        requirement("responses"),
        requirement("time-machine"),
        requirement("webtest"),
        "//cmk:lib_cmk_repo",
        "//tests:conftest",
        "//tests:testlib",
        "//tests/unit:conftest",
    ],
)
