load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "utils",
    srcs = glob(["cmk/backup/utils/**/*.py"]),
    data = ["cmk/backup/py.typed"],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free:__subpackages__",
        "//packages/cmk-backup:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
        requirement("azure-identity"),
        requirement("azure-storage-blob"),
        requirement("boto3"),
        requirement("pydantic"),
    ],
)

py_library(
    name = "gui",
    srcs = glob(["cmk/backup/gui/**/*.py"]),
    data = ["cmk/backup/py.typed"],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":utils",
        "//cmk/gui:breadcrumb",
        "//cmk/gui:config",
        "//cmk/gui:exceptions",
        "//cmk/gui:forms",
        "//cmk/gui:header",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:key_mgmt",
        "//cmk/gui:logged_in",
        "//cmk/gui:main_menu",
        "//cmk/gui:page_menu",
        "//cmk/gui:pages",
        "//cmk/gui:table",
        "//cmk/gui:type_defs",
        "//cmk/gui/form_specs",
        "//cmk/gui/htmllib:generator",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/utils:csrf_token",
        "//cmk/gui/utils:flashed_messages",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/utils:transaction_manager",
        "//cmk/gui/utils:urls",
        "//cmk/gui/utils:user_errors",
        "//cmk/gui/valuespec",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
    ],
)

py_library(
    name = "mkbackup",
    srcs = glob(["cmk/backup/mkbackup/**/*.py"]),
    data = ["cmk/backup/py.typed"],
    imports = ["."],
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
    ],
    deps = [
        ":utils",
        "//cmk/utils",
        "//packages/cmk-ccc:daemon",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:version",
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-backup",
    strip_path_prefixes = ["packages/cmk-backup"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":gui",
        ":mkbackup",
        ":utils",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

pkg_files(
    name = "mkbackup_bin",
    srcs = ["cmk/backup/mkbackup/__init__.py"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    renames = {"cmk/backup/mkbackup/__init__.py": "bin/mkbackup"},
)

package_wheel(
    name = "pkg_tar",
    additional_files = [":mkbackup_bin"],
    visibility = ["//visibility:public"],
    whl = "wheel",
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]) + [":__test__.py"],
    args = ["--import-mode=importlib"],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:store",
        "//packages/cmk-crypto",
        requirement("pytest"),
    ],
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":gui",
        ":mkbackup",
        ":utils",
    ],
    requirements_in = "requirements.in",
)

sh_library(
    name = "helpers",
    srcs = [
        ".f12",
    ],
)
