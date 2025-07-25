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
    deps = [
        "//cmk:lib_cmk",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//tests:testlib",
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
        "def test_cannot_fail():",
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
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":conftest",
        "//cmk:lib_cmk",
        "//tests:testlib",
    ],
)

py_test(
    name = "repo",
    # https://bazel.build/reference/be/common-definitions#test.size
    size = "large",
    srcs = ["__test__.py"] + glob(
        include = ["**/*.py"],
        exclude = [
            "omdlib/**/*.py",
            "**/*pylint*.py",
            "**/*pylint*/**/*.py",
        ],
    ),
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
            "**/test-files/**",
            "**/tree_test_data/**",
            "**/*.json",
            "**/*.log",
        ],
        exclude = ["**/*.py"],
    ) + select({
        "@//:gpl_repo": [],
        "@//:gpl+enterprise_repo": glob(
            [
                "**/*.xml",
                "**/*.pem",
            ],
            allow_empty = True,
        ),
    }),
    main = ":__test__.py",
    deps = [
        ":__test__",
        requirement("astroid"),
        requirement("fastapi"),
        requirement("httpx"),
        requirement("mypy-boto3-logs"),
        requirement("mypy-extensions"),
        requirement("pika"),
        requirement("polyfactory"),
        requirement("pylint"),
        requirement("pytest-asyncio"),
        requirement("pytest-mock"),
        requirement("pytest-random-order"),
        requirement("responses"),
        requirement("time-machine"),
        "//cmk:lib_cmk_repo",
        "//tests:testlib",
        "//tests/unit:conftest",
    ] + select({
        "@//:gpl_repo": [],
        "@//:gpl+enterprise_repo": [
            requirement("python-multipart"),
            "//non-free/packages/cmk-mknotifyd",
        ],
    }),
)
