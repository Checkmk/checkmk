load("@agent_plugins_requirements_3_10//:requirements.bzl", req_3_10 = "requirement")
load("@agent_plugins_requirements_3_11//:requirements.bzl", req_3_11 = "requirement")
load("@agent_plugins_requirements_3_12//:requirements.bzl", req_3_12 = "requirement")
load("@agent_plugins_requirements_3_13//:requirements.bzl", req_3_13 = "requirement")
load("@agent_plugins_requirements_3_8//:requirements.bzl", req_3_8 = "requirement")
load("@agent_plugins_requirements_3_9//:requirements.bzl", req_3_9 = "requirement")
load("@rules_uv//uv:pip.bzl", "pip_compile")
load("//bazel/rules:py_tests_for_python_versions.bzl", "py_tests_for_python_versions")

RUNTIME_REQUIREMENTS = [
    "pytest-mock",
    "requests",
    "pymongo",
]

pip_compile(
    name = "requirements_3_8",
    py3_runtime = "@python_3_8//:py3_runtime",
    requirements_in = ":requirements-in",
    requirements_txt = ":requirements_3_8.txt",
)

pip_compile(
    name = "requirements_3_9",
    py3_runtime = "@python_3_9//:py3_runtime",
    requirements_in = ":requirements-in",
    requirements_txt = ":requirements_3_9.txt",
)

pip_compile(
    name = "requirements_3_10",
    py3_runtime = "@python_3_10//:py3_runtime",
    requirements_in = ":requirements-in",
    requirements_txt = ":requirements_3_10.txt",
)

pip_compile(
    name = "requirements_3_11",
    py3_runtime = "@python_3_11//:py3_runtime",
    requirements_in = ":requirements-in",
    requirements_txt = ":requirements_3_11.txt",
)

pip_compile(
    name = "requirements_3_12",
    py3_runtime = "@python_3_12//:py3_runtime",
    requirements_in = ":requirements-in",
    requirements_txt = ":requirements_3_12.txt",
)

pip_compile(
    name = "requirements_3_13",
    py3_runtime = "@python_3_13//:py3_runtime",
    requirements_in = ":requirements-in",
    requirements_txt = ":requirements_3_13.txt",
)

py_tests_for_python_versions(
    name = "supported_python_versions",
    srcs = glob(["test_*.py"]),
    data = glob(["datasets/**/*"]),
    python_versions = [
        "3.8",
        "3.9",
        "3.10",
        "3.11",
        "3.12",
        "3.13",
    ],
    requirements = {
        "3.8": [req_3_8(req) for req in RUNTIME_REQUIREMENTS],
        "3.9": [req_3_9(req) for req in RUNTIME_REQUIREMENTS],
        "3.10": [req_3_10(req) for req in RUNTIME_REQUIREMENTS],
        "3.11": [req_3_11(req) for req in RUNTIME_REQUIREMENTS],
        "3.12": [req_3_12(req) for req in RUNTIME_REQUIREMENTS],
        "3.13": [req_3_13(req) for req in RUNTIME_REQUIREMENTS],
    },
    deps = ["//agents/plugins:agent-plugins"],
)
