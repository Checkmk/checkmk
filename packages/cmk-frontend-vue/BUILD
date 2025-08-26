load("@aspect_rules_js//js:defs.bzl", "js_run_binary", "js_run_devserver")
load("@aspect_rules_js//npm:defs.bzl", "npm_link_package")
load("@aspect_rules_lint//format:defs.bzl", "format_multirun")
load("@npm_cmk_frontend_vue//:defs.bzl", "npm_link_all_packages")
load("@npm_cmk_frontend_vue//packages/cmk-frontend-vue:eslint/package_json.bzl", eslint_bin = "bin")
load("@npm_cmk_frontend_vue//packages/cmk-frontend-vue:prettier/package_json.bzl", prettier_bin = "bin")
load("@npm_cmk_frontend_vue//packages/cmk-frontend-vue:stylelint/package_json.bzl", stylelint_bin = "bin")
load("@npm_cmk_frontend_vue//packages/cmk-frontend-vue:vite/package_json.bzl", vite_bin = "bin")
load("@npm_cmk_frontend_vue//packages/cmk-frontend-vue:vitest/package_json.bzl", vitest_bin = "bin")
load("@npm_cmk_frontend_vue//packages/cmk-frontend-vue:vue-tsc/package_json.bzl", vue_tsc_bin = "bin")
load("@npm_cmk_frontend_vue//packages/cmk-frontend-vue:vue3-gettext/package_json.bzl", vue_gettext_bin = "bin")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

npm_link_all_packages(name = "node_modules")

vue_gettext_bin.vue_gettext_extract_binary(
    name = "gettext-extract",
    chdir = package_name(),
)

vue_gettext_bin.vue_gettext_compile_binary(
    name = "gettext-compile",
    chdir = package_name(),
)

EXTRACTED_LOCALE_OUTS = [
    "locale/messages.pot",
    "locale/en.po",
    "locale/de.po",
    "locale/fr.po",
]

LOCALE_OUTS = [
    "src/assets/locale/en.json",
    "src/assets/locale/de.json",
    "src/assets/locale/fr.json",
]

js_run_binary(
    name = "extract_i18n",
    srcs = glob([
        "src/**/*.ts",
        "src/**/*.vue",
        "demo/**/*.ts",
        "demo/**/*.vue",
    ]) + [
        "gettext.config.js",
        ":node_modules/vue3-gettext",
    ],
    outs = EXTRACTED_LOCALE_OUTS,
    tool = ":gettext-extract",
    visibility = ["//visibility:private"],
)

js_run_binary(
    name = "compile_i18n",
    srcs = [
        "gettext.config.js",
        ":extract_i18n",
        ":node_modules/vue3-gettext",
    ],
    outs = LOCALE_OUTS,
    tool = ":gettext-compile",
    visibility = ["//visibility:private"],
)

SRCS = [
    ".prettierrc.json",
    "env.d.ts",
    "weaki18nString.d.ts",
    ".stylelintrc.js",
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
    "//packages/cmk-frontend:dist",
    ":compile_i18n",
    ":node_modules/stylelint",
    ":node_modules/postcss-html",
    ":node_modules/stylelint-config-standard",
    ":node_modules/@eslint",
    ":node_modules/@testing-library",
    ":node_modules/@trivago/prettier-plugin-sort-imports",
    ":node_modules/@tsconfig",
    ":node_modules/@typescript-eslint",
    ":node_modules/@vitejs",
    ":node_modules/@vue",
    ":node_modules/@types",
    ":node_modules/axios",
    ":node_modules/class-variance-authority",
    ":node_modules/cmk-shared-typing-bzl",
    ":node_modules/eslint-plugin-vue",
    ":node_modules/grid-layout-plus",
    ":node_modules/lucide-vue-next",
    ":node_modules/msw",
    ":node_modules/prettier",
    ":node_modules/radix-vue",
    ":node_modules/rollup",
    ":node_modules/sanitize-html",
    ":node_modules/typescript-eslint",
    ":node_modules/vite",
    ":node_modules/vite-plugin-vue-devtools",
    ":node_modules/vitest",
    ":node_modules/vitest-fail-on-console",
    ":node_modules/vue",
    ":node_modules/vue-component-type-helpers",
    ":node_modules/vue-router",
    ":node_modules/vue3-gettext",
] + LOCALE_OUTS + glob([
    "src/**/*.ts",
    "src/**/*.vue",
    "src/**/*.css",
    "src/**/*.svg",
    "demo/**/*.ts",
    "demo/**/*.vue",
    "demo/**/*.css",
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
    srcs = SRCS,
    args = ["build"],
    chdir = package_name(),
    out_dirs = ["dist"],
)

vitest_bin.vitest_test(
    name = "unit-test",
    args = ["run"],
    chdir = package_name(),
    data = SRCS_AND_TESTS,
)

vue_tsc_bin.vue_tsc_test(
    name = "type-check",
    args = [
        "--build",
        "--force",
    ],
    chdir = package_name(),
    data = SRCS_AND_TESTS,
    include_types = True,
)

vite_bin.vite_binary(name = "vite_server")

js_run_devserver(
    name = "vite",
    chdir = package_name(),
    data = SRCS,
    tool = ":vite_server",
)

# this rule exposes the `vitest` binary - for development purposes only
vitest_bin.vitest_binary(
    name = "vitest",
    chdir = package_name(),
    data = SRCS_AND_TESTS,
)

# This should be done as shown
# [here](https://github.com/aspect-build/rules_lint/blob/main/example/tools/format/BUILD.bazel)
# and would shrink the whole check-format and formatting stuff to
#
#  alias(name = "format", actual = "//bazel/tools/format")
#
# but it then had to be done similarly for all packages

prettier_bin.prettier_binary(
    name = "prettier",
    data = [
        ":.prettierrc.json",
        ":node_modules/@trivago/prettier-plugin-sort-imports",
    ],
    # Allow the binary to be run outside bazel
    env = {"BAZEL_BINDIR": "."},
    fixed_args = [
        # `require` statements in the config file will be resolved relative to its location
        # Therefore to make it hermetic, prettier must be pointed at the copy of the config file
        # in the runfiles folder rather than the one in the source folder.
        '--config="$$JS_BINARY__RUNFILES"/$(rlocationpath :.prettierrc.json)',
        # it looks like .prettierignore from the SOURCE has to be provided in order to make
        # specified (relative) directories match the actually checked files
        '--ignore-path="$$BUILD_WORKSPACE_DIRECTORY/' + package_name() + '/.prettierignore"',
        # default log level is "log" which spams on success
        # https://prettier.io/docs/en/cli.html#--log-level
        "--log-level=warn",
    ],
)

# This produces a `:format` and a `:format.check` run-target. Both operate on the actual
# source tree but `:format.check` does not modify any files but returns non-zero if there
# are files which have to be re-formatted.
# Also both targets accept (workspace-absolute) files and directories on which is operated.
# Note that while `:format.check` can be used as some sort of "test" but it's NOT an actual
# Bazel-test in terms of `bazel test` - this has to be implemented using `format_test()` instead.
# see https://github.com/aspect-build/rules_lint/blob/main/docs/formatting.md
format_multirun(
    name = "format",
    css = ":prettier",
    html = ":prettier",
    javascript = ":prettier",
    python = "@aspect_rules_lint//format:ruff",
    visibility = ["//:__subpackages__"],
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
    data = SRCS_AND_TESTS,
)

stylelint_bin.stylelint_test(
    name = "stylelint",
    args = [
        "**/*.{vue,css}",
    ],
    chdir = package_name(),
    data = SRCS,
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
    visibility = ["//omd:__pkg__"],
)
