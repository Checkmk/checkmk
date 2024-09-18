load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@omd_packages//omd/packages/rules:package_wheel.bzl", "package_wheel")

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
        "cmk/agent_receiver/py.typed",
        "cmk/agent_receiver/site_context.py",
        "cmk/agent_receiver/utils.py",
        "cmk/agent_receiver/worker.py",
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-agent-receiver",
    strip_path_prefixes = ["packages/cmk-agent-receiver"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":cmk-agent-receiver",
    ],
)

package_wheel(wheel_target = "wheel")
