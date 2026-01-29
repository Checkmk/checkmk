load("@aspect_rules_js//js:defs.bzl", "js_run_binary", "js_run_devserver")
load("@aspect_rules_js//npm:defs.bzl", "npm_link_package")
load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@npm//:eslint/package_json.bzl", eslint_bin = "bin")
load("@npm//:stylelint/package_json.bzl", stylelint_bin = "bin")
load("@npm//:vitest/package_json.bzl", vitest_bin = "bin")
load("@npm//:vue-tsc/package_json.bzl", vue_tsc_bin = "bin")
load("@npm//:vue3-gettext/package_json.bzl", vue_gettext_bin = "bin")
load("@npm//packages/cmk-frontend-vue:vite/package_json.bzl", vite_bin = "bin")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exports_files(["package.json"])

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

js_run_binary(
    name = "extract_pot_file",
    srcs = glob([
        "src/**/*.ts",
        "src/**/*.vue",
        "demo/**/*.ts",
        "demo/**/*.vue",
    ]) + [
        "gettext.config.js",
        ":node_modules/vue3-gettext",
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
    "//packages/cmk-frontend:dist",
    "env.d.ts",
    "weaki18nString.d.ts",
    ".stylelintrc.js",
    "scripts/stylelint-vue-bem-naming-convention.js",
    "eslint.config.js",
    "index.html",
    "package.json",
    "tsconfig.app.json",
    "tsconfig.json",
    "tsconfig.demo.json",
    "tsconfig.node.json",
    "tsconfig.test.json",
    "vite.config.demo.ts",
    "vite.config.ts",
    "demo/index.html",
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
    ":node_modules/radix-vue",
    ":node_modules/rollup",
    ":node_modules/sanitize-html",
    ":node_modules/uuid",
    ":node_modules/vite",
    ":node_modules/vite-plugin-vue-devtools",
    ":node_modules/vue-component-type-helpers",
    ":node_modules/vue-router",
] + LOCALE_OUTS + glob([
    "src/**/*.ts",
    "src/**/*.vue",
    "src/**/*.css",
    "src/**/*.svg",
    "demo/**/*.ts",
    "demo/**/*.vue",
    "demo/**/*.css",
    "demo/public/*",
])

SRCS_AND_TESTS = SRCS + glob([
    "tests/**/*.ts",
    "tests/**/*.vue",
])

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

vite_bin.vite(
    name = "dist-demo-hosted",
    srcs = TOOLING + SRCS,
    # The --base argument needs to match the hosting web server config
    # (e.g. http://localhost/frontend-demo/)
    args = [
        "build",
        "--config",
        "vite.config.demo.ts",
        "--base",
        "/frontend-demo/",
    ],
    chdir = package_name(),
    out_dirs = ["demo/dist"],
)

vitest_bin.vitest_test(
    name = "unit-test",
    args = ["run"],
    chdir = package_name(),
    data = TOOLING + SRCS_AND_TESTS,
)

vue_tsc_bin.vue_tsc_test(
    name = "type-check",
    args = [
        "--build",
        "--force",
    ],
    chdir = package_name(),
    data = TOOLING + SRCS_AND_TESTS,
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
    data = TOOLING + SRCS_AND_TESTS,
)

alias(
    name = "format",
    actual = "//bazel/tools/format",
)

alias(
    name = "format.check",
    actual = "//bazel/tools/format:check",
)

# Note: this is not done via lint_eslint_aspect + lint_test intentionally.
#       While that would be the superior approach I (frans) was not able to
#       build the test target as demonstrated here:
#       https://github.com/aspect-build/rules_lint/blob/main/docs/eslint.md
eslint_bin.eslint_test(
    name = "eslint",
    args = [
        "--max-warnings=0",
        ".",
    ],
    chdir = package_name(),
    data = TOOLING + SRCS_AND_TESTS,
)

stylelint_bin.stylelint_test(
    name = "stylelint",
    args = [
        "**/*.{vue,css}",
    ],
    chdir = package_name(),
    data = TOOLING + SRCS,
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
