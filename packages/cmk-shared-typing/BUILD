load("@aspect_rules_js//js:defs.bzl", "js_library")
load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@aspect_rules_ts//ts:defs.bzl", "ts_project")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@bazel_skylib//rules:copy_file.bzl", "copy_file")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@npm//bazel/tools:prettier/package_json.bzl", prettier_bin = "bin")
load(
    "@npm//packages/cmk-shared-typing:openapi-typescript/package_json.bzl",
    openapi_typescript = "bin",
)
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:shared_typing_generators.bzl", "json2python", "json2typescript")

exports_files([
    "requirements.in",
    "package.json",
])

npm_link_all_packages(name = "node_modules")

SOURCES_COMMON = [
    "ai_button.json",
    "configuration_entity.json",
    "create_relay.json",
    "dialog.json",
    "loading_transition.json",
    "main_menu.json",
    "mode_host.json",
    "mode_oauth2_connection.json",
    "notifications.json",
    "setup.json",
    "icon.json",
    "sidebar.json",
    "unified_search.json",
    "user_frontend_config.json",
    "vue_formspec_components.json",
    "welcome.json",
    "agent_slideout.json",
    "product_telemetry.json",
    "two_factor_auth.json",
]

SOURCES_SPECIAL_DATACLASSES = [
    "graph_designer.json",
    "service_graphs.json",
]

json2typescript(
    name = "generated_ts_files",
    srcs = SOURCES_COMMON + SOURCES_SPECIAL_DATACLASSES,
    chdir = package_name(),
    data = glob(["source/**/*.json"]),
    header_txt = """/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/* eslint-disable */
/**
 * This file is auto-generated via the cmk-shared-typing package.
 * Do not edit manually.
 */
""",
    source_dir = "source",
    target_dir = "typescript",
)

write_file(
    name = "empty_index_ts",
    out = "typescript/index.ts",
)

openapi_typescript.openapi_typescript(
    name = "openapi_internal_ts_file",
    srcs = ["source/openapi_spec_internal.yaml"],
    outs = ["typescript/openapi_internal.d.ts"],
    args = [
        "$(rootpath source/openapi_spec_internal.yaml)",
        "-o",
        "$(rootpath typescript/openapi_internal.d.ts)",
    ],
)

js_library(
    name = "cmk_shared_typing_ts",
    srcs = [
        "package.json",
        "tsconfig.json",
        ":cmk_shared_typing_ts_lib",
        ":empty_index_ts",
        ":generated_ts_files",
        ":openapi_internal_ts_file",
    ],
    visibility = ["//packages:__subpackages__"],
)

ts_project(
    name = "cmk_shared_typing_ts_lib",
    srcs = [
        "package.json",
        "tsconfig.json",
        ":generated_ts_files",
    ],
    declaration = True,
    declaration_map = True,
    emit_declaration_only = True,
    source_map = True,
    tags = ["manual"],
    transpiler = "tsc",
    visibility = ["//packages:__subpackages__"],
)

py_library(
    name = "cmk_shared_typing_formatter",
    srcs = [
        "utils/__init__.py",
        "utils/format.py",
        "utils/postprocess.py",
    ],
    imports = ["."],
    deps = [
        requirement("black"),
        requirement("datamodel_code_generator"),
        requirement("libcst"),
    ],
)

json2python(
    name = "generated_py_files_special_dataclasses",
    srcs = SOURCES_SPECIAL_DATACLASSES,
    data = glob(["source/**/*.json"]) + ["header_py.txt"],
    extra_args = [
        "--use-field-description",
        "--use-title-as-name",
        "--use-double-quotes",
        "--use-default",
        "--use-one-literal-as-default",
        "--custom-file-header-path=$(location :header_py.txt)",
        "--custom-formatters=utils.format",
        "--output-model-type=dataclasses.dataclass",
        "--collapse-root-models",
        "--enum-field-as-literal=all",
        "--use-generic-container-types",
        "--frozen-dataclasses",
        "--keyword-only",
        "--use-union-operator",
    ],
    formatter = ":cmk_shared_typing_formatter",
    source_dir = "source",
    target_dir = "cmk/shared_typing",
)

json2python(
    name = "generated_py_files_common",
    srcs = SOURCES_COMMON,
    data = glob(["source/**/*.json"]) + ["header_py.txt"],
    extra_args = [
        "--use-field-description",
        "--use-title-as-name",
        "--use-double-quotes",
        "--use-default",
        "--use-one-literal-as-default",
        "--custom-file-header-path=$(location :header_py.txt)",
        "--custom-formatters=utils.format",
        "--output-model-type=dataclasses.dataclass",
        "--use-generic-container-types",
        "--frozen-dataclasses",
        "--keyword-only",
        "--use-subclass-enum",
    ],
    formatter = ":cmk_shared_typing_formatter",
    source_dir = "source",
    target_dir = "cmk/shared_typing",
)

copy_file(
    name = "j2py_init",
    src = "header_py.txt",
    out = "cmk/shared_typing/__init__.py",
    allow_symlink = True,
)

py_library(
    name = "cmk_shared_typing_py",
    srcs = [
        ":cmk/shared_typing/__init__.py",
        ":generated_py_files_common",
        ":generated_py_files_special_dataclasses",
    ],
    imports = ["."],
    visibility = ["//cmk:__pkg__"],
)

write_file(
    name = "py_typed",
    out = "cmk/shared_typing/py.typed",
)

filegroup(
    name = "cmk_shared_typing_extra_files",
    srcs = [":cmk/shared_typing/py.typed"],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-shared-typing",
    strip_path_prefixes = ["packages/cmk-shared-typing"],
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":cmk_shared_typing_extra_files",
        ":cmk_shared_typing_py",
    ],
)

build_test(
    name = "build_test",
    targets = [
        ":wheel",
        ":cmk_shared_typing_ts",
    ],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

prettier_bin.prettier_binary(
    name = "prettier",
    data = ["//bazel/tools:prettierrc"],
    env = {"BAZEL_BINDIR": "."},
    fixed_args = [
        '--config="$$JS_BINARY__RUNFILES"/$(rlocationpath //bazel/tools:prettierrc)',
        "--log-level=warn",
    ],
)

alias(
    name = "format",
    actual = "//bazel/tools/format",
)

alias(
    name = "format.check",
    actual = "//bazel/tools/format:check",
)
