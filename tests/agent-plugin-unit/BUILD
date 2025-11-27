load("@agent_plugins_requirements_3_10//:requirements.bzl", req_3_10 = "requirement")
load("@agent_plugins_requirements_3_11//:requirements.bzl", req_3_11 = "requirement")
load("@agent_plugins_requirements_3_12//:requirements.bzl", req_3_12 = "requirement")
load("@agent_plugins_requirements_3_13//:requirements.bzl", req_3_13 = "requirement")
load("@agent_plugins_requirements_3_8//:requirements.bzl", req_3_8 = "requirement")
load("@agent_plugins_requirements_3_9//:requirements.bzl", req_3_9 = "requirement")
load("@rules_uv//uv:pip.bzl", "pip_compile")
load("//bazel/rules:py_test_under_py_version_macro.bzl", "py_test_under_py_version")

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

py_test_under_py_version(
    name = "py-3.8",
    srcs = glob(["test_*.py"]),
    data = glob(["datasets/**/*"]),
    python_version = "3.8",
    deps = [
        req_3_8(req)
        for req in RUNTIME_REQUIREMENTS
    ] + [
        "//agents/plugins:agent-plugins",
    ],
)

py_test_under_py_version(
    name = "py-3.9",
    srcs = glob(["test_*.py"]),
    data = glob(["datasets/**/*"]),
    python_version = "3.9",
    deps = [
        req_3_9(req)
        for req in RUNTIME_REQUIREMENTS
    ] + [
        "//agents/plugins:agent-plugins",
    ],
)

py_test_under_py_version(
    name = "py-3.10",
    srcs = glob(["test_*.py"]),
    data = glob(["datasets/**/*"]),
    python_version = "3.10",
    deps = [
        req_3_10(req)
        for req in RUNTIME_REQUIREMENTS
    ] + [
        "//agents/plugins:agent-plugins",
    ],
)

py_test_under_py_version(
    name = "py-3.11",
    srcs = glob(["test_*.py"]),
    data = glob(["datasets/**/*"]),
    python_version = "3.11",
    deps = [
        req_3_11(req)
        for req in RUNTIME_REQUIREMENTS
    ] + [
        "//agents/plugins:agent-plugins",
    ],
)

py_test_under_py_version(
    name = "py-3.12",
    srcs = glob(["test_*.py"]),
    data = glob(["datasets/**/*"]),
    python_version = "3.12",
    deps = [
        req_3_12(req)
        for req in RUNTIME_REQUIREMENTS
    ] + [
        "//agents/plugins:agent-plugins",
    ],
)

py_test_under_py_version(
    name = "py-3.13",
    srcs = glob(["test_*.py"]),
    data = glob(["datasets/**/*"]),
    python_version = "3.13",
    deps = [
        req_3_13(req)
        for req in RUNTIME_REQUIREMENTS
    ] + [
        "//agents/plugins:agent-plugins",
    ],
)

test_suite(
    name = "supported_python_versions",
    tests = [
        ":py-3.10",
        ":py-3.11",
        ":py-3.12",
        ":py-3.13",
        ":py-3.8",
        ":py-3.9",
    ],
)
