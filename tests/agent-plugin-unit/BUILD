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
    name = "agent-plugin-unit",
    # https://bazel.build/reference/be/common-definitions#test.size
    size = "small",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--random-order-bucket=global",
    ],
    data = glob(["datasets/**"]),
    main = ":__test__.py",
    tags = ["legacy-python"],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        requirement("pytest-mock"),
        requirement("pytest-asyncio"),
        requirement("pytest-random-order"),
        requirement("pymongo"),
        requirement("marshmallow"),
        "//agents/plugins:agent-plugins-python",
    ],
)
