load("@aspect_rules_py//py:defs.bzl", "py_library")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-dev-deploy",
    srcs = [
        "cmk/dev_deploy/__init__.py",
        "cmk/dev_deploy/__main__.py",
        "cmk/dev_deploy/cli.py",
        "cmk/dev_deploy/core/__init__.py",
        "cmk/dev_deploy/core/bazel.py",
        "cmk/dev_deploy/core/diagnostics.py",
        "cmk/dev_deploy/core/git.py",
        "cmk/dev_deploy/core/output.py",
        "cmk/dev_deploy/core/subprocess_utils.py",
        "cmk/dev_deploy/core/timeouts.py",
        "cmk/dev_deploy/deployers/__init__.py",
        "cmk/dev_deploy/deployers/bazel_builder.py",
        "cmk/dev_deploy/deployers/config_deployer.py",
        "cmk/dev_deploy/deployers/wheel_deployer.py",
        "cmk/dev_deploy/errors.py",
        "cmk/dev_deploy/execution/__init__.py",
        "cmk/dev_deploy/execution/bazel_resolver.py",
        "cmk/dev_deploy/execution/parallel.py",
        "cmk/dev_deploy/execution/service_manager.py",
        "cmk/dev_deploy/execution/source_paths.py",
        "cmk/dev_deploy/execution/step_registry.py",
        "cmk/dev_deploy/frontend/__init__.py",
        "cmk/dev_deploy/frontend/frontend_supervisor.py",
        "cmk/dev_deploy/frontend/ibazel_manager.py",
        "cmk/dev_deploy/manifest/__init__.py",
        "cmk/dev_deploy/manifest/deps.py",
        "cmk/dev_deploy/manifest/reader.py",
        "cmk/dev_deploy/manifest/registry.py",
        "cmk/dev_deploy/manifest/staleness.py",
        "cmk/dev_deploy/manifest/update.py",
        "cmk/dev_deploy/site/__init__.py",
        "cmk/dev_deploy/site/preparation.py",
        "cmk/dev_deploy/site/privilege.py",
        "cmk/dev_deploy/site/site_config.py",
        "cmk/dev_deploy/site/site_resolver.py",
        "cmk/dev_deploy/site/sudoers.py",
        "cmk/dev_deploy/site/version_clone.py",
        "cmk/dev_deploy/site/warnings.py",
        "cmk/dev_deploy/state/__init__.py",
        "cmk/dev_deploy/state/change_detector.py",
        "cmk/dev_deploy/state/deploy_state.py",
        "cmk/dev_deploy/state/path_skip.py",
        "cmk/dev_deploy/types.py",
        "cmk/dev_deploy/watcher.py",
    ],
    data = [
        "cmk/dev_deploy/manifest/deploy_specs.toml",
        "cmk/dev_deploy/py.typed",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]),
    data = ["//scripts:cmk-dev-deploy.py"],
    deps = [
        ":cmk-dev-deploy",
    ],
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":cmk-dev-deploy",
    ],
    requirements_in = "requirements.in",
)
