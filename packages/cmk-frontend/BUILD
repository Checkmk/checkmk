load("@aspect_rules_ts//ts:defs.bzl", "ts_project")
load("@aspect_rules_webpack//webpack:defs.bzl", "webpack_bundle")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@npm//:eslint/package_json.bzl", eslint_bin = "bin")
load("@npm//packages/cmk-frontend:webpack-cli/package_json.bzl", webpack_cli_bin = "bin")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:py_test.bzl", "py_test")

exports_files(["package.json"])

npm_link_all_packages(name = "node_modules")

SRCS = glob([
    # TODO: tsconfig.json is missing
    "src/css/*",  # just for the directory
    "src/images/**/*.*",
    "src/jquery/**/*.*",
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

webpack_bundle(
    name = "dist",
    srcs = SRCS,
    chdir = package_name(),
    node_modules = ":node_modules",
    output_dir = True,
    # TODO: This is only done for the theme.css and icons.
    # cmk-frontend-vue should not access files that belong to cmk-frontend
    visibility = ["//packages/cmk-frontend-vue:__pkg__"],
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
    name = "build_test",
    targets = [":dist"],
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
    stamp = 1,
    visibility = ["//omd:__pkg__"],
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
    data = SRCS + BUILD_DEPS + ["eslint.config.js"],
)
