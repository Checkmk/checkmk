load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-agent-receiver",
    srcs = [
        "cmk/agent_receiver/__init__.py",
        "cmk/agent_receiver/agent_receiver/app.py",
        "cmk/agent_receiver/agent_receiver/checkmk_rest_api.py",
        "cmk/agent_receiver/agent_receiver/decompression.py",
        "cmk/agent_receiver/agent_receiver/endpoints.py",
        "cmk/agent_receiver/agent_receiver/models.py",
        "cmk/agent_receiver/agent_receiver/utils.py",
        "cmk/agent_receiver/lib/__init__.py",
        "cmk/agent_receiver/lib/auth.py",
        "cmk/agent_receiver/lib/certs.py",
        "cmk/agent_receiver/lib/config.py",
        "cmk/agent_receiver/lib/log.py",
        "cmk/agent_receiver/lib/middleware.py",
        "cmk/agent_receiver/lib/mtls_auth_validator.py",
        "cmk/agent_receiver/main.py",
        "cmk/agent_receiver/relay/__init__.py",
        "cmk/agent_receiver/relay/api/__init__.py",
        "cmk/agent_receiver/relay/api/dependencies/relays_repository.py",
        "cmk/agent_receiver/relay/api/routers/__init__.py",
        "cmk/agent_receiver/relay/api/routers/relays/__init__.py",
        "cmk/agent_receiver/relay/api/routers/relays/dependencies.py",
        "cmk/agent_receiver/relay/api/routers/relays/endpoints.py",
        "cmk/agent_receiver/relay/api/routers/relays/handlers/__init__.py",
        "cmk/agent_receiver/relay/api/routers/relays/handlers/cert_retriever.py",
        "cmk/agent_receiver/relay/api/routers/relays/handlers/forward_monitoring_data.py",
        "cmk/agent_receiver/relay/api/routers/relays/handlers/register_relay.py",
        "cmk/agent_receiver/relay/api/routers/tasks/__init__.py",
        "cmk/agent_receiver/relay/api/routers/tasks/dependencies.py",
        "cmk/agent_receiver/relay/api/routers/tasks/endpoints.py",
        "cmk/agent_receiver/relay/api/routers/tasks/handlers/__init__.py",
        "cmk/agent_receiver/relay/api/routers/tasks/handlers/activate_config.py",
        "cmk/agent_receiver/relay/api/routers/tasks/handlers/create_task.py",
        "cmk/agent_receiver/relay/api/routers/tasks/handlers/get_tasks.py",
        "cmk/agent_receiver/relay/api/routers/tasks/handlers/get_version.py",
        "cmk/agent_receiver/relay/api/routers/tasks/handlers/update_task.py",
        "cmk/agent_receiver/relay/api/routers/tasks/libs/config_task_factory.py",
        "cmk/agent_receiver/relay/api/routers/tasks/libs/localhost_authorization.py",
        "cmk/agent_receiver/relay/api/routers/tasks/libs/retrieve_config_serial.py",
        "cmk/agent_receiver/relay/api/routers/tasks/libs/site_cn_authorization.py",
        "cmk/agent_receiver/relay/api/routers/tasks/libs/tasks_repository.py",
        "cmk/agent_receiver/relay/api/routers/tasks/serializers.py",
        "cmk/agent_receiver/relay/app.py",
        "cmk/agent_receiver/relay/lib/relays_repository.py",
        "cmk/agent_receiver/relay/lib/shared_types.py",
        "cmk/agent_receiver/relay/lib/site_auth.py",
        "cmk/agent_receiver/worker.py",
    ],
    data = [
        "cmk/agent_receiver/py.typed",
    ],
    imports = ["."],
    visibility = ["//cmk:__pkg__"],
    deps = [
        "//packages/cmk-ccc:version",
        "//packages/cmk-relay-protocols",
        requirement("cryptography"),
        requirement("fastapi"),
        requirement("gunicorn"),
        requirement("h11"),
        requirement("httpx"),
        requirement("python-dateutil"),
        requirement("python-multipart"),
        requirement("requests"),
        requirement("tenacity"),
        requirement("starlette"),
        requirement("uvicorn"),
        requirement("uvicorn-worker"),
    ],
)

py_library(
    name = "testlib",
    srcs = glob(["cmk/testlib/agent_receiver/**/*.py"]),
    imports = ["."],
    deps = [
        ":cmk-agent-receiver",
        requirement("cryptography"),
        requirement("fastapi"),
        requirement("httpx"),
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
    srcs = glob(["tests/unit/agent_receiver/**/*.py"]) + [":__test__.py"],
    args = [
        "--random-order",
        "--random-order-bucket=global",
        "--disable-socket",
        "--allow-unix-socket",
        "--durations=5",
        "-W",
        "error",
    ],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":cmk-agent-receiver",
        ":testlib",
        ":unit_testlib",
        requirement("cryptography"),
        requirement("fastapi"),
        requirement("pytest"),
        requirement("httpx"),
        requirement("pytest-asyncio"),
        requirement("pytest-xdist"),
        requirement("pytest-socket"),
        requirement("pytest-random-order"),
        requirement("pytest-mock"),
        requirement("requests"),
        requirement("starlette"),
        requirement("time-machine"),
        requirement("python-dateutil"),
    ],
)

py_pytest_main(
    name = "__testlib_test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "unit_testlib",
    size = "medium",
    srcs = glob(["tests/unit/testlib/**/*.py"]) + [":__testlib_test__.py"],
    args = [
        "--random-order",
        "--random-order-bucket=global",
        "--durations=5",
    ],
    main = "__testlib_test__.py",
    deps = [
        ":__testlib_test__",
        ":testlib",
        requirement("pytest"),
        requirement("pytest-xdist"),
        requirement("httpx"),
        requirement("pytest-random-order"),
    ],
)

py_pytest_main(
    name = "__component_test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "component",
    size = "medium",
    srcs = glob(["tests/component/**/*.py"]) + [":__component_test__.py"],
    args = [
        "--random-order",
        "--random-order-bucket=global",
        "--durations=5",
    ],
    main = "__component_test__.py",
    tags = ["component"],
    deps = [
        ":__component_test__",
        ":cmk-agent-receiver",
        ":testlib",
        requirement("pytest"),
        requirement("pytest-xdist"),
        requirement("pytest-socket"),
        requirement("pytest-random-order"),
        requirement("fastapi"),
        requirement("starlette"),
        requirement("httpx"),
        requirement("python-dateutil"),
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
