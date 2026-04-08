load("@aspect_rules_js//js:defs.bzl", "js_library", "js_run_binary", "js_run_devserver")
load("@aspect_rules_js//npm:defs.bzl", "npm_link_package")
load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@npm//:vitest/package_json.bzl", vitest_bin = "bin")
load("@npm//:vue-tsc/package_json.bzl", vue_tsc_bin = "bin")
load("@npm//:vue3-gettext/package_json.bzl", vue_gettext_bin = "bin")
load("@npm//packages/cmk-frontend-vue:vite/package_json.bzl", vite_bin = "bin")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:css_library.bzl", "css_library")
load("//bazel/rules:git_hash_file.bzl", "git_hash_file")
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
    srcs = glob(["src/**/*.css"]),
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
        ":demo_ts",
        ":demo_vue",
        ":node_modules/vue3-gettext",
        ":src_ts",
        ":src_vue",
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

TOOLING = [
    "//:node_modules/@eslint/js",
    "//:node_modules/@typescript-eslint/parser",
    "//:node_modules/@vue/compiler-dom",
    "//:node_modules/@vue/eslint-config-prettier",
    "//:node_modules/@vue/eslint-config-typescript",
    "//:node_modules/@vue/server-renderer",
    "//:node_modules/@vue/test-utils",
    "//:node_modules/eslint",
    "//:node_modules/eslint-plugin-vue",
    "//:node_modules/jsdom",
    "//:node_modules/postcss-html",
    "//:node_modules/sass-embedded",
    "//:node_modules/stylelint",
    "//:node_modules/stylelint-config-standard",
    "//:node_modules/typescript-eslint",
    "//:node_modules/vitest",
    "//:node_modules/vitest-fail-on-console",
    "//:node_modules/vue",
    "//:node_modules/vue-tsc",
    "//:node_modules/vue3-gettext",
]

SRCS = [
    "//:eslintrc",
    "//packages/cmk-frontend:dist",
    "env.d.ts",
    "weaki18nString.d.ts",
    "scripts/stylelint-vue-bem-naming-convention.js",
    "index.html",
    "package.json",
    "vite.config.ucl.ts",
    "vite.config.ts",
    "ui-component-library/index.html",
    ":demo_ts",
    ":demo_vue",
    ":demo_css",
    ":src_ts",
    ":src_vue",
    ":src_css",
    ":compile_i18n",
    ":node_modules/@testing-library",
    ":node_modules/@tsconfig",
    ":node_modules/@vitejs",
    ":node_modules/@types",
    ":node_modules/axios",
    ":node_modules/class-variance-authority",
    ":node_modules/cmk-shared-typing-bzl",
    ":node_modules/grid-layout-plus",
    ":node_modules/lucide-vue-next",
    ":node_modules/marked",
    ":node_modules/msw",
    ":node_modules/openapi-fetch",
    ":node_modules/reka-ui",
    ":node_modules/rollup",
    ":node_modules/sanitize-html",
    ":node_modules/uuid",
    ":node_modules/vite",
    ":node_modules/vite-plugin-vue-devtools",
    ":node_modules/vue-component-type-helpers",
    ":node_modules/vue-router",
] + LOCALE_OUTS + glob([
    "src/**/*.svg",
    "ui-component-library/**/*.png",
    "ui-component-library/**/*.svg",
    "ui-component-library/public/*",
])

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

SRCS_AND_TESTS = SRCS + [":test_ts"]

npm_link_package(
    name = "node_modules/cmk-shared-typing-bzl",
    src = "//packages/cmk-shared-typing:cmk_shared_typing_ts",
    package = "cmk-shared-typing",
    root_package = "packages/cmk-frontend-vue",
    visibility = ["//packages:__subpackages__"],
)

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

vitest_bin.vitest_test(
    name = "unit-test",
    args = [
        "--configLoader=runner",
        "run",
    ],
    chdir = package_name(),
    data = TOOLING + SRCS_AND_TESTS + [":test_vue"],
)

vue_tsc_bin.vue_tsc_test(
    name = "type-check",
    args = [
        "--build",
        "--force",
    ],
    chdir = package_name(),
    data = TOOLING + SRCS_AND_TESTS + [":test_vue"],
    include_types = True,
)

vite_bin.vite_binary(name = "vite_server")

js_run_devserver(
    name = "vite",
    chdir = package_name(),
    data = TOOLING + SRCS,
    tool = ":vite_server",
)

# this rule exposes the `vitest` binary - for development purposes only
vitest_bin.vitest_binary(
    name = "vitest",
    chdir = package_name(),
    data = TOOLING + SRCS_AND_TESTS + [":test_vue"],
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

py_test(
    name = "test-license-headers",
    srcs = ["scripts/test_license_headers.py"],
    data = glob(["**"]),
    pytest_main = True,
    deps = [requirement("pytest")],
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
