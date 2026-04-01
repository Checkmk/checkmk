load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["**/*.py"]) + [":__test__.py"],
    args = [
        "--random-order",
        "--random-order-bucket=global",
        "--disable-socket",
        "--allow-unix-socket",
        "--durations=5",
        "-W",
        "error",
    ],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":unit_testlib",
        "//packages/cmk-agent-receiver",
        "//packages/cmk-agent-receiver:testlib",
        requirement("cryptography"),
        requirement("fastapi"),
        requirement("pytest"),
        requirement("httpx"),
        requirement("pytest-asyncio"),
        requirement("pytest-xdist"),
        requirement("pytest-socket"),
        requirement("pytest-random-order"),
        requirement("pytest-mock"),
        requirement("requests"),
        requirement("starlette"),
        requirement("time-machine"),
        requirement("python-dateutil"),
    ],
)

py_pytest_main(
    name = "__testlib_test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "unit_testlib",
    srcs = glob(["testlib/**/*.py"]) + [":__testlib_test__.py"],
    args = [
        "--random-order",
        "--random-order-bucket=global",
        "--durations=5",
    ],
    main = "__testlib_test__.py",
    deps = [
        ":__testlib_test__",
        "//packages/cmk-agent-receiver:testlib",
        requirement("pytest"),
        requirement("pytest-xdist"),
        requirement("httpx"),
        requirement("pytest-random-order"),
    ],
)
