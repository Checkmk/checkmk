load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "all_requirements", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:requirements_mapping.bzl", "requirements_mapping")

py_library(
    name = "requirements_utils",
    srcs = ["utils.py"],
    data = ["//:defines.make"],
    imports = ["../../.."],
    visibility = ["//visibility:public"],
    deps = [
        "//tests/code_quality:bazel_utils",
        requirement("isort"),
        requirement("requirements-parser"),
    ],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "requirements_files",
    size = "small",
    srcs = ["__test__.py"] + ["test_requirements_files.py"],
    data = [
        "//:constraints.txt",
        "//:requirements.txt",
        "//:runtime-requirements.txt",
        "//agents/plugins:dev-requirements.in",
        "//cmk:requirements.in",
        "//packages:dev_python_requirements",
        "//packages:python_requirements",
        "//scripts:requirements.in",
        "//tests:dev-requirements.in",
    ] + select({
        "@//:gpl+nonfree_repo": [
            "//non-free/packages:dev_python_requirements",
            "//non-free/packages:python_requirements",
        ],
        "@//:gpl_repo": [],
    }),
    env_inherit = ["GERRIT_BRANCH"],
    main = ":__test__.py",
    tags = ["requirements"],
    deps = [
        ":__test__",
        ":requirements_utils",
        requirement("pytest"),
        requirement("requirements-parser"),
    ],
)

py_binary(
    name = "generate_requirements_mapping",
    srcs = ["generate_requirements_mapping.py"],
    main = "generate_requirements_mapping.py",
    deps = [
        ":requirements_utils",
    ],
)

requirements_mapping(
    name = "mapping",
    dist_infos = [req.replace(":pkg", ":dist_info") for req in all_requirements],
    tool = ":generate_requirements_mapping",
    visibility = ["//visibility:public"],
)
