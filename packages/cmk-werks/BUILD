load("@aspect_rules_js//js:defs.bzl", "js_binary")
load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
    "package.json",
])

npm_link_all_packages(name = "node_modules")

js_binary(
    name = "vnu",
    data = [":node_modules/vnu-jar"],
    entry_point = "js/vnu.js",
    tags = ["manual"],
)

py_library(
    name = "tool",
    srcs = [
        # compatibility shim for venv entry points
        "cmk/werks/cli.py",
        "cmk/werks/tool/__init__.py",
        "cmk/werks/tool/__main__.py",
        "cmk/werks/tool/cli.py",
        "cmk/werks/tool/collect.py",
        "cmk/werks/tool/config.py",
        "cmk/werks/tool/constants.py",
        "cmk/werks/tool/convert.py",
        "cmk/werks/tool/error.py",
        "cmk/werks/tool/format.py",
        "cmk/werks/tool/id_pool.py",
        "cmk/werks/tool/in_out_elements.py",
        "cmk/werks/tool/load.py",
        "cmk/werks/tool/markup.py",
        "cmk/werks/tool/models.py",
        "cmk/werks/tool/parse.py",
        "cmk/werks/tool/schemas/__init__.py",
        "cmk/werks/tool/schemas/werk.py",
        "cmk/werks/tool/utils/__init__.py",
        "cmk/werks/tool/utils/__main__.py",
        "cmk/werks/tool/utils/collect.py",
        "cmk/werks/tool/validate.py",
    ],
    data = ["cmk/werks/py.typed"],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//omd:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:version",
        requirement("gitpython"),
        requirement("lxml"),
        requirement("markdown"),
        requirement("pydantic"),
        requirement("requests"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["tool"],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]),
    deps = [
        ":cmk-werk-ids-server",
        ":tool",
        requirement("flask"),
        requirement("gitpython"),
        requirement("requests"),
        requirement("vcrpy"),
        requirement("pytest-recording"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-werks",
    strip_path_prefixes = ["packages/cmk-werks"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":site",
        ":tool",
        ":web",
    ],
)

py_library(
    name = "site",
    srcs = [
        "cmk/werks/site/__init__.py",
        "cmk/werks/site/acknowledgement.py",
    ],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//omd:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":tool",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:store",
    ],
)

py_library(
    name = "web",
    srcs = [
        "cmk/werks/web/__init__.py",
        "cmk/werks/web/_pages.py",
    ],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//omd:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":site",
        ":tool",
        "//cmk/utils:man_pages",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-web",
    ],
)

py_library(
    name = "cmk-werk-ids-server",
    srcs = [
        "cmk/werk_ids_server/__init__.py",
        "cmk/werk_ids_server/__main__.py",
        "cmk/werk_ids_server/_db.py",
        "cmk/werk_ids_server/server.py",
    ],
    imports = ["."],
    deps = [
        requirement("flask"),
        requirement("gunicorn"),
        requirement("werkzeug"),
    ],
)

py_wheel(
    name = "wheel_server",
    distribution = "cmk-werk-ids-server",
    requires = [
        "flask",
        "gunicorn",
        "werkzeug",
    ],
    strip_path_prefixes = ["packages/cmk-werks"],
    version = "1.0.0",
    deps = [":cmk-werk-ids-server"],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/werks/py.typed"],
)

# This wheel is only used for providing the entry point "werk" from the .venv under .venv/bin
# We explicitly need to *not* add dependencies here because venv/IDE would take the static wheels
# and not the editable sources from the repo which are included via sitecustomize.py
py_wheel(
    name = "wheel_entrypoint_only",
    distribution = "cmk-werks-entrypoint",
    entry_points = {"console_scripts": ["werk = cmk.werks.tool.cli:main"]},
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [],
)

build_test(
    name = "build_test",
    targets = ["wheel_entrypoint_only"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

sh_library(
    name = "helpers",
    srcs = [
        ".f12",
        "run",
    ],
)

py_binary(
    name = "werk",
    srcs = ["cmk/werks/tool/__main__.py"],
    imports = ["."],
    main = "cmk/werks/tool/__main__.py",
    visibility = ["//visibility:public"],
    deps = [":tool"],
)

py_binary(
    name = "utils-bin",
    srcs = ["cmk/werks/tool/utils/__main__.py"],
    imports = ["."],
    main = "cmk/werks/tool/utils/__main__.py",
    visibility = ["//visibility:public"],
    deps = [":tool"],
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":site",
        ":tool",
        ":utils-bin",
        ":web",
        ":werk",
        ":werk-ids-server-deploy",
    ],
    requirements_in = "requirements.in",
)

py_binary(
    name = "werk-ids-server-deploy",
    srcs = ["scripts/werk_ids_server.py"],
    main = "scripts/werk_ids_server.py",
    visibility = ["//visibility:public"],
    deps = [],
)
