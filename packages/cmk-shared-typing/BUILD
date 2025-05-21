load("@aspect_rules_js//js:defs.bzl", "js_library")
load("@aspect_rules_lint//format:defs.bzl", "format_multirun")
load("@aspect_rules_ts//ts:defs.bzl", "ts_project")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@npm_cmk_frontend//packages/cmk-frontend:prettier/package_json.bzl", prettier_bin = "bin")
load("@npm_cmk_shared_typing//:defs.bzl", "npm_link_all_packages")
load("//bazel/rules:shared_typing_generators.bzl", "json2typescript")

npm_link_all_packages(name = "node_modules")

TYPE_DEFINITION_FILES = [
    "graph_designer.json",
    "configuration_entity.json",
    "mode_host.json",
    "notifications.json",
    "setup.json",
    "user_frontend_config.json",
    "vue_formspec_components.json",
]

json2typescript(
    name = "generated_ts_files",
    srcs = TYPE_DEFINITION_FILES,
    chdir = package_name(),
    data = glob([
        "source/**/*.json",
        "header*_ts.txt",
    ]),
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

js_library(
    name = "cmk_shared_typing_ts",
    srcs = [
        "package.json",
        "tsconfig.json",
        ":cmk_shared_typing_ts_lib",
        ":empty_index_ts",
        ":generated_ts_files",
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

prettier_bin.prettier_binary(
    name = "prettier",
    env = {"BAZEL_BINDIR": "."},
    fixed_args = [
        "--log-level=warn",
    ],
)

format_multirun(
    name = "format",
    javascript = ":prettier",
    python = "@aspect_rules_lint//format:ruff",
    visibility = ["//:__subpackages__"],
)
