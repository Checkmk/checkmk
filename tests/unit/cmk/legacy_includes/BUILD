load("@aspect_rules_py//py:defs.bzl", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

package(default_visibility = [":__subpackages__"])

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "legacy_includes",
    # https://bazel.build/reference/be/common-definitions#test.size
    size = "small",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--random-order-bucket=global",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    use_project_pytest_config = True,
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
