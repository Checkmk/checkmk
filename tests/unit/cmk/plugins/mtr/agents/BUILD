load("@aspect_rules_py//py:defs.bzl", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "agents",
    # https://bazel.build/reference/be/common-definitions#test.size
    size = "small",
    srcs = [
        "__test__.py",
        "test_mtr.py",
    ],
    main = ":__test__.py",
    tags = ["legacy-python"],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        requirement("marshmallow"),
        requirement("pytest"),
        "//cmk/plugins/mtr/agents",
    ],
)
