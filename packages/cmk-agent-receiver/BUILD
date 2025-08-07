load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-agent-receiver",
    srcs = [
        "cmk/agent_receiver/__init__.py",
        "cmk/agent_receiver/apps_and_routers.py",
        "cmk/agent_receiver/certs.py",
        "cmk/agent_receiver/checkmk_rest_api.py",
        "cmk/agent_receiver/decompression.py",
        "cmk/agent_receiver/endpoints.py",
        "cmk/agent_receiver/log.py",
        "cmk/agent_receiver/main.py",
        "cmk/agent_receiver/models.py",
        "cmk/agent_receiver/site_context.py",
        "cmk/agent_receiver/utils.py",
        "cmk/agent_receiver/worker.py",
    ],
    data = [
        "cmk/agent_receiver/py.typed",
    ],
    imports = ["."],
    visibility = ["//cmk:__pkg__"],
    deps = [
        requirement("cryptography"),
        requirement("fastapi"),
        requirement("gunicorn"),
        requirement("h11"),
        requirement("python-dateutil"),
        requirement("python-multipart"),
        requirement("requests"),
        requirement("starlette"),
        requirement("uvicorn"),
        requirement("uvicorn-worker"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-agent-receiver"],
    tags = ["no-mypy"],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":cmk-agent-receiver",
        requirement("cryptography"),
        requirement("fastapi"),
        requirement("httpx"),
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("requests"),
        requirement("starlette"),
    ],
)

py_pytest_main(
    name = "__component_test__",
    deps = [
        requirement("pytest"),
        requirement("pytest-xdist"),
    ],
)

py_test(
    name = "component",
    size = "medium",
    srcs = glob(["tests/component/**/*.py"]) + [":__component_test__.py"],
    main = "__component_test__.py",
    deps = [
        ":__component_test__",
        ":cmk-agent-receiver",
        requirement("pytest"),
        requirement("fastapi"),
        requirement("starlette"),
        requirement("httpx"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-agent-receiver",
    requires = [
        "cryptography",
        "fastapi",
        "gunicorn",
        "h11",
        "python-dateutil",
        "python-multipart",
        "requests",
        "starlette",
        "uvicorn",
        "uvicorn-worker",
    ],
    strip_path_prefixes = ["packages/cmk-agent-receiver"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":cmk-agent-receiver",
        ":py_typed",
    ],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/agent_receiver/py.typed"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
