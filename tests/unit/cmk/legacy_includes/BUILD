load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "legacy_includes",
    # https://bazel.build/reference/be/common-definitions#test.size
    size = "small",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
        "--random-order-bucket=global",
    ],
    data = ["@//:pyproject.toml"],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        "//cmk/legacy_includes",
        "//tests/unit:conftest",
        requirement("marshmallow"),
        requirement("pytest-asyncio"),
        requirement("pytest-mock"),
        requirement("pytest-random-order"),
        requirement("time-machine"),
    ],
)
