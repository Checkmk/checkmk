load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

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
        "cmk/dev_deploy/core/diagnostics.py",
        "cmk/dev_deploy/core/output.py",
        "cmk/dev_deploy/core/preflight.py",
        "cmk/dev_deploy/core/subprocess_utils.py",
        "cmk/dev_deploy/core/timeouts.py",
        "cmk/dev_deploy/deployers/__init__.py",
        "cmk/dev_deploy/deployers/_distribution_info.py",
        "cmk/dev_deploy/deployers/_site_python.py",
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
        "cmk/dev_deploy/site/edition_filter.py",
        "cmk/dev_deploy/site/overlay.py",
        "cmk/dev_deploy/site/privilege.py",
        "cmk/dev_deploy/site/site_config.py",
        "cmk/dev_deploy/site/site_resolver.py",
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

py_binary(
    name = "cmk-dev-deploy-bin",
    srcs = ["cmk/dev_deploy/__main__.py"],
    main = "cmk/dev_deploy/__main__.py",
    visibility = ["//visibility:public"],
    deps = [":cmk-dev-deploy"],
)

py_pytest_main(
    name = "__test__",
    tags = ["no-mypy"],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":cmk-dev-deploy",
        requirement("pytest"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-dev-deploy",
    strip_path_prefixes = ["packages/cmk-dev-deploy"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [":cmk-dev-deploy"],
)

py_wheel(
    name = "wheel_entrypoint_only",
    console_scripts = {
        "cmk-dev-deploy": "cmk.dev_deploy.__main__:main",
    },
    distribution = "cmk-dev-deploy-entrypoint",
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

build_test(
    name = "build_test",
    targets = [
        ":wheel",
        ":wheel_entrypoint_only",
    ],
)
