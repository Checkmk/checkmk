load("@aspect_rules_js//js:defs.bzl", "js_binary", "js_library", "js_run_binary", "js_run_devserver")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@npm//:vitest/package_json.bzl", vitest_bin = "bin")
load("@npm//:vue-tsc/package_json.bzl", vue_tsc_bin = "bin")
load("@npm//:vue3-gettext/package_json.bzl", vue_gettext_bin = "bin")
load("@npm//packages/cmk-frontend-vue:vite/package_json.bzl", vite_bin = "bin")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:css_library.bzl", "css_library")
load("//bazel/rules:git_hash_file.bzl", "git_hash_file")
load("//bazel/rules:link_shared_typing.bzl", "link_shared_typing")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:vitest_test.bzl", "vitest_test")
load("//bazel/rules:vue_library.bzl", "vue_library")

exports_files([
    "package.json",
    "scripts/stylelint-vue-bem-naming-convention.js",
])

js_library(
    name = "stylelint_plugin",
    srcs = ["scripts/stylelint-vue-bem-naming-convention.js"],
    visibility = ["//visibility:public"],
    deps = ["//:node_modules/stylelint"],
)

js_library(
    name = "eslintrc",
    srcs = [
        "eslint.config.mjs",
        "//:node_modules/eslint",
    ],
    tags = ["no-lint"],
    visibility = ["//visibility:public"],
    deps = [
        # eslint.config.mjs builds on cmk-ui-library's shared eslint config, and the
        # tsconfig chain used by type-aware rules extends
        # cmk-ui-library/tsconfig.vue-base.json, resolved via this node_modules link.
        ":node_modules/cmk-ui-library",
        "//packages/cmk-ui-library:eslintrc",
    ],
)

npm_link_all_packages(name = "node_modules")

vue_gettext_bin.vue_gettext_extract_binary(
    name = "gettext-extract",
    chdir = package_name(),
)

vue_gettext_bin.vue_gettext_compile_binary(
    name = "gettext-compile",
    chdir = package_name(),
)

WEBLATE_PO_FILES = [
    "locale/de.po",
    "locale/es.po",
    "locale/fr.po",
    "locale/it.po",
    "locale/ja.po",
    "locale/nl.po",
    "locale/pt_PT.po",
    "locale/ro.po",
]

LOCALE_OUTS = [
    "src/assets/locale/de.json",
    "src/assets/locale/es.json",
    "src/assets/locale/fr.json",
    "src/assets/locale/it.json",
    "src/assets/locale/ja.json",
    "src/assets/locale/nl.json",
    "src/assets/locale/pt_PT.json",
    "src/assets/locale/ro.json",
]

filegroup(
    name = "tsconfig",
    srcs = [
        "tsconfig.app.json",
        "tsconfig.json",
        "tsconfig.node.json",
        "tsconfig.test.json",
        "tsconfig.ucl.json",
    ],
)

vue_library(
    name = "src_vue",
    srcs = glob(["src/**/*.vue"]),
    data = [":tsconfig"],
    deps = [
        ":src_ts",
        "//:node_modules/vue",
    ],
)

js_library(
    name = "src_ts",
    srcs = glob(["src/**/*.ts"]) + [":tsconfig"],
)

css_library(
    name = "src_css",
    srcs = glob([
        "src/**/*.css",
        "src/**/*.scss",
    ]),
)

vue_library(
    name = "demo_vue",
    srcs = glob(["ui-component-library/**/*.vue"]),
    data = [":tsconfig"],
    deps = [
        ":demo_ts",
        "//:node_modules/vue",
    ],
)

css_library(
    name = "demo_css",
    srcs = glob(["ui-component-library/**/*.css"]),
)

js_library(
    name = "demo_ts",
    srcs = glob(["ui-component-library/**/*.ts"]) + [":tsconfig"],
)

js_run_binary(
    name = "extract_pot_file",
    srcs = [
        "gettext.config.js",
        ":node_modules/vue3-gettext",
        ":src_ts",
        ":src_vue",
        "//packages/cmk-ui-library:pkg",
    ],
    outs = ["locale/messages.pot"],
    tool = ":gettext-extract",
    visibility = ["//locale:__pkg__"],
    # TODO: depends on non-hermetic gettext
)

genrule(
    name = "weblate_po_files",
    srcs = [
        "//locale:po_files",
        ":extract_pot_file",
    ],
    outs = WEBLATE_PO_FILES,
    cmd = """
        mkdir -p $(RULEDIR)/locale
        vue_pot_file=$(location :extract_pot_file)
        for po_file in $(locations //locale:po_files); do
            lang_code=$$(echo $$po_file | rev | cut -d'/' -f3 | rev)
            msgcomm $$po_file $$vue_pot_file $$po_file > $(RULEDIR)/locale/$$lang_code.po
        done
    """,
)

js_run_binary(
    name = "compile_i18n",
    srcs = [
        "gettext.config.js",
        ":node_modules/vue3-gettext",
    ] + WEBLATE_PO_FILES,
    outs = LOCALE_OUTS,
    tool = ":gettext-compile",
    visibility = ["//visibility:private"],
)

TEST_TOOLING = [
    "//:node_modules/@vue/test-utils",
    "//:node_modules/jsdom",
    "//:node_modules/vitest",
    "//:node_modules/vitest-fail-on-console",
    "//:node_modules/vue",
]

TOOLING = TEST_TOOLING + [
    "//:node_modules/@eslint/js",
    "//:node_modules/@typescript-eslint/parser",
    "//:node_modules/@vue/compiler-dom",
    "//:node_modules/@vue/eslint-config-prettier",
    "//:node_modules/@vue/eslint-config-typescript",
    "//:node_modules/@vue/server-renderer",
    "//:node_modules/eslint",
    "//:node_modules/eslint-plugin-vue",
    "//:node_modules/postcss-html",
    "//:node_modules/sass-embedded",
    "//:node_modules/stylelint",
    "//:node_modules/stylelint-config-standard",
    "//:node_modules/typescript-eslint",
    "//:node_modules/vue-tsc",
    "//:node_modules/vue3-gettext",
]

VITE_SRCS = [
    ":node_modules/cmk-ui-library",
    "package.json",
    "vite.config.ts",
    ":demo_ts",
    ":demo_vue",
    ":demo_css",
    ":src_ts",
    ":src_vue",
    ":src_css",
    ":node_modules/@tanstack",
    ":node_modules/@testing-library",
    ":node_modules/@tsconfig",
    ":node_modules/@vitejs",
    ":node_modules/@internationalized",
    ":node_modules/@types",
    ":node_modules/acorn",
    ":node_modules/axios",
    ":node_modules/class-variance-authority",
    ":node_modules/cmk-shared-typing-bzl",
    ":node_modules/d3-array",
    ":node_modules/d3-axis",
    ":node_modules/d3-drag",
    ":node_modules/d3-ease",
    ":node_modules/d3-force",
    ":node_modules/d3-hierarchy",
    ":node_modules/d3-interpolate",
    ":node_modules/d3-scale",
    ":node_modules/d3-selection",
    ":node_modules/d3-shape",
    ":node_modules/d3-time-format",
    ":node_modules/d3-transition",
    ":node_modules/d3-zoom",
    ":node_modules/grid-layout-plus",
    ":node_modules/leaflet",
    ":node_modules/marked",
    ":node_modules/msw",
    ":node_modules/openapi-fetch",
    ":node_modules/reka-ui",
    ":node_modules/rollup",
    ":node_modules/sanitize-html",
    ":node_modules/uuid",
    ":node_modules/vite",
    ":node_modules/vite-plugin-vue-devtools",
    ":node_modules/typescript",
    ":node_modules/vue-component-type-helpers",
    ":node_modules/vue-router",
] + glob([
    "ui-component-library/**/*.png",
    "ui-component-library/**/*.svg",
])

TYPE_CHECK_SRCS = VITE_SRCS + [
    "//:eslintrc",
    "env.d.ts",
    "weaki18nString.d.ts",
    "scripts/stylelint-vue-bem-naming-convention.js",
    "ui-component-library/_ucl/vite-plugin-ucl-mcp.ts",
    "ui-component-library/_ucl/ucl-mcp-runtime.mjs",
    "index.html",
    "vite.config.ucl.ts",
    "ui-component-library/index.html",
] + glob(["ui-component-library/public/*"])

# The dev server serves no translations and falls back to English: compiling the
# catalogs re-extracts them from all sources, which takes seconds per rebuild.
DEV_SERVER_SRCS = TYPE_CHECK_SRCS + ["//packages/cmk-frontend:dist"]

SRCS = DEV_SERVER_SRCS + LOCALE_OUTS

vue_library(
    name = "test_vue",
    srcs = glob(["tests/**/*.vue"]),
    data = [":tsconfig"],
    deps = [
        ":src_ts",
        ":test_ts",
        "//:node_modules/vue",
    ],
)

js_library(
    name = "test_ts",
    srcs = glob(["tests/**/*.ts"]) + [":tsconfig"],
)

TYPE_CHECK_DATA = TOOLING + TYPE_CHECK_SRCS

TEST_DATA = TEST_TOOLING + VITE_SRCS + [
    ":test_ts",
    ":test_vue",
    "//packages/cmk-frontend:theme_images",
]

link_shared_typing()

vite_bin.vite(
    name = "dist",
    srcs = TOOLING + SRCS,
    args = ["build"],
    chdir = package_name(),
    out_dirs = ["dist"],
)

# The next endpoints are used to build the "UI Component Library". This is not
# shipped with Checkmk but always built from the master branch and published on
# an internal webserver so UX and product can access it. Do not call those
# entrypoints in a general Checkmk build.

git_hash_file(
    name = "hash_file",
    out = "current-git-commit",
    tags = ["manual"],
)

genrule(
    name = "ucl_generate_env",
    srcs = [":hash_file"],
    outs = ["ui-component-library/.env"],
    cmd = """
        echo "VITE_BUILD_COMMIT=\\"$$(cat $(execpath hash_file))\\"" >> $@
    """,
    tags = ["manual"],
)

vite_bin.vite(
    name = "dist-ucl-hosted",
    srcs = TOOLING + SRCS + ["ucl_generate_env"],
    # The --base argument needs to match the hosting web server config
    # (e.g. http://localhost/ui-component-library/)
    args = [
        "build",
        "--config",
        "vite.config.ucl.ts",
        "--base",
        "/ui-component-library/",
    ],
    chdir = package_name(),
    out_dirs = ["ui-component-library/dist"],
    tags = ["manual"],
)

# "UI Component Library" end

vitest_test(
    name = "unit-test",
    timeout = "long",
    data = TEST_DATA,
    shard_count = 2,
    workers = 3,
)

# One target per tsconfig project: they have no cross-references, so a single
# `--build` only ran them serially. Mirrors //bazel/rules:vue_package.bzl. Only
# the tests project needs tests/ in its sandbox.
vue_tsc_bin.vue_tsc_test(
    name = "type-check",
    timeout = "moderate",
    args = [
        "-p",
        "tsconfig.app.json",
    ],
    chdir = package_name(),
    data = TYPE_CHECK_DATA,
    include_types = True,
)

vue_tsc_bin.vue_tsc_test(
    name = "type-check-node",
    timeout = "short",
    args = [
        "-p",
        "tsconfig.node.json",
    ],
    chdir = package_name(),
    data = TYPE_CHECK_DATA,
    include_types = True,
)

# Covers the same files as tsconfig.test.json but without the vitest and jest-dom
# ambient types, so a test global leaking into the demo app is still an error.
vue_tsc_bin.vue_tsc_test(
    name = "type-check-ucl",
    timeout = "moderate",
    args = [
        "-p",
        "tsconfig.ucl.json",
    ],
    chdir = package_name(),
    data = TYPE_CHECK_DATA,
    include_types = True,
)

vue_tsc_bin.vue_tsc_test(
    name = "type-check-tests",
    timeout = "moderate",
    args = [
        "-p",
        "tsconfig.test.json",
    ],
    chdir = package_name(),
    data = TYPE_CHECK_DATA + [
        ":test_ts",
        ":test_vue",
    ],
    include_types = True,
)

vite_bin.vite_binary(name = "vite_server")

js_run_devserver(
    name = "vite",
    chdir = package_name(),
    data = TOOLING + DEV_SERVER_SRCS,
    tool = ":vite_server",
)

# this rule exposes the `vitest` binary - for development purposes only
vitest_bin.vitest_binary(
    name = "vitest",
    chdir = package_name(),
    data = TEST_DATA,
)

alias(
    name = "format",
    actual = "//bazel/tools/format",
)

alias(
    name = "format.check",
    actual = "//bazel/tools/format:check",
)

pkg_files(
    name = "frontend_vue_dist_pkg",
    srcs = [":dist"],
    prefix = "share/check_mk/web/htdocs/cmk-frontend-vue",
    strip_prefix = "dist",
)

pkg_tar(
    name = "cmk-frontend-vue",
    srcs = [":frontend_vue_dist_pkg"],
    stamp = 1,
    visibility = ["//omd:__pkg__"],
)

genrule(
    name = "ucl-mcp-server-data",
    srcs = [":dist-ucl-hosted"],
    outs = ["ucl-components.json"],
    cmd = "cp $(execpath :dist-ucl-hosted)/api/ucl-components.json $(OUTS)",
    tags = ["manual"],
)

js_binary(
    name = "ucl-mcp-server",
    data = [":ucl-mcp-server-data"],
    entry_point = "ui-component-library/_ucl/ucl-mcp-runtime.mjs",
    tags = ["manual"],
)

py_cmk_test(
    name = "test-code-integrity",
    srcs = [
        "scripts/test_license_headers.py",
        "scripts/test_ucl_parity.py",
    ],
    data = glob(["**"]) + ["//packages/cmk-ui-library:srcs"],
)

build_test(
    name = "build_test",
    targets = [":dist"],
)

sh_library(
    name = "helpers",
    srcs = [
        ".f12",
        "run",
    ],
)
