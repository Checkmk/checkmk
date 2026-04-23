load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
    "skel.permissions",
])

pkg_files(
    name = "skel",
    srcs = glob(
        ["skel/**/*"],
        exclude = ["skel/etc/init.d/*"],
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_files(
    name = "skel_755",
    srcs = glob(["skel/etc/init.d/*"]),
    attributes = pkg_attributes(mode = "0755"),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_mklink(
    name = "10-agent-receiver",
    link_name = "skel/etc/rc.d/10-agent-receiver",
    target = "../init.d/agent-receiver",
)

pkg_tar(
    name = "omd_skel_tar",
    srcs = [
        ":10-agent-receiver",
        ":skel",
        ":skel_755",
    ],
    visibility = ["//omd:__pkg__"],
)

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
        "cmk/agent_receiver/relay/api/dependencies/__init__.py",
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
        "cmk/agent_receiver/relay/api/routers/tasks/libs/__init__.py",
        "cmk/agent_receiver/relay/api/routers/tasks/libs/config_task_factory.py",
        "cmk/agent_receiver/relay/api/routers/tasks/libs/localhost_authorization.py",
        "cmk/agent_receiver/relay/api/routers/tasks/libs/retrieve_config_serial.py",
        "cmk/agent_receiver/relay/api/routers/tasks/libs/site_cn_authorization.py",
        "cmk/agent_receiver/relay/api/routers/tasks/libs/tasks_repository.py",
        "cmk/agent_receiver/relay/api/routers/tasks/serializers.py",
        "cmk/agent_receiver/relay/app.py",
        "cmk/agent_receiver/relay/lib/__init__.py",
        "cmk/agent_receiver/relay/lib/relays_repository.py",
        "cmk/agent_receiver/relay/lib/shared_types.py",
        "cmk/agent_receiver/relay/lib/site_auth.py",
        "cmk/agent_receiver/worker.py",
    ],
    data = [
        "cmk/agent_receiver/py.typed",
    ],
    imports = ["."],
    visibility = [
        "//cmk:__pkg__",
        "//packages/cmk-agent-receiver/tests:__subpackages__",
        "//tests:__subpackages__",
    ],
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
    data = [
        "@wiremock_standalone//file",
    ],
    imports = ["."],
    visibility = ["//packages/cmk-agent-receiver/tests:__subpackages__"],
    deps = [
        ":cmk-agent-receiver",
        "//packages/cmk-crypto",
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

build_test(
    name = "build_test",
    targets = ["wheel"],
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

py_binary(
    name = "gunicorn_conf",
    srcs = ["skel/etc/agent-receiver/gunicorn.conf.py"],
    main = "skel/etc/agent-receiver/gunicorn.conf.py",
)

sh_library(
    name = "helpers",
    srcs = [
        ".f12",
        "skel/etc/init.d/agent-receiver",
    ],
)

py_requirements_test(
    name = "requirements-test",
    known_unused = [
        "gunicorn",  # deploys the agent receiver via a bash script, not a Python import
        "python-multipart",  # needed by fastapi but not imported directly
    ],
    libs = ":cmk-agent-receiver",
    requirements_in = "requirements.in",
)
