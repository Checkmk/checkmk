load("@aspect_rules_py//py:defs.bzl", "py_library", "py_test")
load("@cmk_requirements//:requirements.bzl", "all_requirements", "requirement")
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

py_test(
    name = "requirements_files",
    size = "small",
    srcs = ["test_requirements_files.py"],
    args = [
        "--import-mode=importlib",
    ],
    data = [
        "//:constraints.txt",
        "//.github/skills:dev-requirements.in",
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
    pytest_main = True,
    tags = ["requirements"],
    deps = [
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
