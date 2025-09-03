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
        "cmk/agent_receiver/relay/__init__.py",
        "cmk/agent_receiver/relay/api/__init__.py",
        "cmk/agent_receiver/relay/api/dependencies/relays_repository.py",
        "cmk/agent_receiver/relay/api/routers/__init__.py",
        "cmk/agent_receiver/relay/api/routers/base_router.py",
        "cmk/agent_receiver/relay/api/routers/relays/__init__.py",
        "cmk/agent_receiver/relay/api/routers/relays/dependencies.py",
        "cmk/agent_receiver/relay/api/routers/relays/endpoints.py",
        "cmk/agent_receiver/relay/api/routers/relays/handlers/__init__.py",
        "cmk/agent_receiver/relay/api/routers/relays/handlers/register_relay.py",
        "cmk/agent_receiver/relay/api/routers/relays/handlers/unregister_relay.py",
        "cmk/agent_receiver/relay/api/routers/tasks/__init__.py",
        "cmk/agent_receiver/relay/api/routers/tasks/dependencies.py",
        "cmk/agent_receiver/relay/api/routers/tasks/endpoints.py",
        "cmk/agent_receiver/relay/api/routers/tasks/handlers/__init__.py",
        "cmk/agent_receiver/relay/api/routers/tasks/handlers/create_task.py",
        "cmk/agent_receiver/relay/api/routers/tasks/handlers/get_tasks.py",
        "cmk/agent_receiver/relay/api/routers/tasks/handlers/update_task.py",
        "cmk/agent_receiver/relay/api/routers/tasks/libs/tasks_repository.py",
        "cmk/agent_receiver/relay/api/routers/tasks/serializers.py",
        "cmk/agent_receiver/relay/lib/relay_config.py",
        "cmk/agent_receiver/relay/lib/relays_repository.py",
        "cmk/agent_receiver/relay/lib/shared_types.py",
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
        "//packages/cmk-relay-protocols",
        requirement("cryptography"),
        requirement("fastapi"),
        requirement("gunicorn"),
        requirement("h11"),
        requirement("httpx"),
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
    srcs = glob(["tests/unit/**/*.py"]) + [":__test__.py"],
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
