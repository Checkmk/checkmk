load("@aspect_bazel_lib//lib:copy_to_bin.bzl", "copy_to_bin")
load("@aspect_rules_lint//format:defs.bzl", "format_multirun")
load("@aspect_rules_ts//ts:defs.bzl", "ts_project")
load("@aspect_rules_webpack//webpack:defs.bzl", "webpack_bundle")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@npm_cmk_frontend//:defs.bzl", "npm_link_all_packages")
load("@npm_cmk_frontend//packages/cmk-frontend:eslint/package_json.bzl", eslint_bin = "bin")
load("@npm_cmk_frontend//packages/cmk-frontend:prettier/package_json.bzl", prettier_bin = "bin")
load("@npm_cmk_frontend//packages/cmk-frontend:webpack-cli/package_json.bzl", webpack_cli_bin = "bin")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:py_test.bzl", "py_test")

npm_link_all_packages(name = "node_modules")

SRCS = glob([
    "src/css/*",  # just for the directory
    "src/images/**/*.*",
    "src/jquery/**/*.js",
    "src/js/**/*.js",
    "src/js/**/*.ts",
    "src/openapi/**/*.*",
    "src/sounds/**/*.*",
    "src/themes/**/*.*",
])

BUILD_DEPS = [
    ":node_modules/@babel",
    ":node_modules/@yaireo",
    ":node_modules/@zxcvbn-ts",
    ":node_modules/@types",
    ":node_modules/@jest",
    ":node_modules/babel-loader",
    ":node_modules/core-js",
    ":node_modules/crossfilter2",
    ":node_modules/css-loader",
    ":node_modules/d3",
    ":node_modules/d3-flextree",
    ":node_modules/d3-hexbin",
    ":node_modules/d3-sankey",
    ":node_modules/element-closest-polyfill",
    ":node_modules/extract-loader",
    ":node_modules/file-loader",
    ":node_modules/filemanager-webpack-plugin",
    ":node_modules/jquery",
    ":node_modules/postcss-loader",
    ":node_modules/qrcode",
    ":node_modules/sass-loader",
    ":node_modules/script-loader",
    ":node_modules/select2",
    ":node_modules/simplebar",
    ":node_modules/sweetalert2",
    ":node_modules/terser-webpack-plugin",
    ":node_modules/webpack-remove-empty-scripts",
]

# FIXME(frans): this is a dirty hack - cmk-frontend-vue should
# not access files that belong to cmk-frontend
copy_to_bin(
    name = "src",
    srcs = glob(
        [
            "**/*.svg",
            "**/*.png",
        ],
        exclude = ["node_modules/**/*.svg"],
    ),
    visibility = ["//packages/cmk-frontend-vue:__pkg__"],
)

webpack_bundle(
    name = "dist",
    srcs = SRCS,
    chdir = package_name(),
    node_modules = ":node_modules",
    output_dir = True,
    webpack_config = ":webpack.config.js",
    deps = BUILD_DEPS,
)

webpack_cli_bin.webpack_cli_binary(
    name = "dist-watch",
    args = [
        "--mode=development",
        "--watch",
    ],
    chdir = package_name(),
    data = SRCS + BUILD_DEPS + [
        "webpack.config.js",
        ":dist",
    ],
)

py_test(
    name = "scss_content",
    srcs = ["scripts/test_scss_content.py"],
    data = glob(["src/themes/**/*.scss"]),
    main = "test_scss_content.py",
)

ts_project(
    name = "cmk-frontend-ts",
    srcs = glob(["src/js/**/*.ts"]),
    no_emit = True,
    transpiler = "tsc",
    visibility = ["//packages:__subpackages__"],
    deps = BUILD_DEPS,
)

build_test(
    name = "type-check",
    targets = [":cmk-frontend-ts"],
)

pkg_files(
    name = "frontend_dist_pkg",
    srcs = [":dist"],
    prefix = "share/check_mk/web/htdocs",
    strip_prefix = "dist",
)

pkg_tar(
    name = "cmk-frontend",
    srcs = [":frontend_dist_pkg"],
    visibility = ["//omd:__pkg__"],
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
    data = [":.prettierrc"],
    # Allow the binary to be run outside bazel
    env = {"BAZEL_BINDIR": "."},
    # chdir="\"$$(BUILD_WORKSPACE_DIRECTORY)\"/" + package_name(),
    fixed_args = [
        # `require` statements in the config file will be resolved relative to its location
        # Therefore to make it hermetic, prettier must be pointed at the copy of the config file
        # in the runfiles folder rather than the one in the source folder.
        "--config=\"$$JS_BINARY__RUNFILES\"/$(rlocationpath :.prettierrc)",
        # it looks like .prettierignore from the SOURCE has to be provided in order to make
        # specified (relative) directories match the actually checked files
        "--ignore-path=\"$$BUILD_WORKSPACE_DIRECTORY/" + package_name() + "/.prettierignore\"",
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
    # fixme(frans): for some reasons no .js files are found despite there are some on toplevel
    # javascript = ":prettier",
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
    data = SRCS + BUILD_DEPS + ["eslint.config.js"],
)
