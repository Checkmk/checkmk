load("@aspect_bazel_lib//lib:copy_file.bzl", "copy_file")
load("@aspect_bazel_lib//lib:copy_to_bin.bzl", "copy_to_bin")
load("@aspect_rules_js//js:defs.bzl", "js_library")
load("@aspect_rules_ts//ts:defs.bzl", "ts_project")
load("@aspect_rules_webpack//webpack:defs.bzl", "webpack_bundle")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@npm//packages/cmk-frontend:webpack-cli/package_json.bzl", webpack_cli_bin = "bin")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:py_test.bzl", "py_test")
load("//bazel/rules:css_library.bzl", "css_library")
load("//bazel/rules:dependency_info.bzl", "dependency_info")

exports_files(["package.json"])

npm_link_all_packages(name = "node_modules")

# The import resolver needs the path aliases, but ts_project already writes
# tsconfig.json to this package's bin directory, so lint gets it under its own
# name rather than a second copy of the same output.
copy_file(
    name = "eslint_tsconfig",
    src = "tsconfig.json",
    out = "tsconfig.eslint.json",
)

js_library(
    name = "eslintrc",
    srcs = [
        # import-x/no-unused-modules enumerates the sources itself and insists on
        # an eslintrc next to them, see eslint.config.mjs.
        ".eslintrc.json",
        "eslint.config.mjs",
        "package.json",
        ":eslint_tsconfig",
    ],
    tags = ["no-lint"],
    visibility = ["//visibility:public"],
    deps = [
        ":node_modules/eslint-import-resolver-typescript",
        ":node_modules/eslint-plugin-import-x",
        ":node_modules/eslint-plugin-no-unsanitized",
    ],
)

dependency_info(
    name = "redoc_dependency_info",
    package_name = "redoc",
    license_kind = "@package_metadata//licenses/spdx:MIT",
    license_text = "src/openapi/redoc.standalone.js.LICENSE.txt",
    purl_namespace = None,
    purl_type = "npm",
    version = "2.5.3",
)

copy_to_bin(
    name = "redoc",
    srcs = [
        "src/openapi/redoc.standalone.js",
        "src/openapi/redoc.standalone.js.LICENSE.txt",
    ],
    package_metadata = [":redoc_dependency_info"],
)

dependency_info(
    name = "colorpicker_dependency_info",
    package_name = "FlexiColorPicker",
    license_kind = "@package_metadata//licenses/spdx:MIT",
    purl_namespace = "DavidDurman",
    purl_type = "github",
    version = "ec614a74e808a39b51a9f6883476aad6e77066f8",
)

copy_to_bin(
    name = "colorpicker",
    srcs = ["src/js/modules/colorpicker.js"],
    package_metadata = [":colorpicker_dependency_info"],
)

SRCS = glob(
    [
        # TODO: tsconfig.json is missing
        "src/css/*",  # just for the directory
        "src/js/**/*.js",
        "src/js/**/*.ts",
        "src/openapi/**/*.*",
        "src/sounds/**/*.*",
        "src/themes/**/*.*",
    ],
    exclude = [
        "src/js/modules/colorpicker.js",
        "src/openapi/redoc.standalone.js",
        "src/openapi/redoc.standalone.js.LICENSE.txt",
    ],
) + [
    ":colorpicker",
    ":redoc",
    "//packages/cmk-frontend/src/images:nuvola-icons",
    "//packages/cmk-frontend/src/jquery",
    "//packages/cmk-frontend/src/openapi/swagger-ui-5.20.6:swagger-ui",
    "//packages/cmk-frontend/src/themes/facelift/fonts/inter",
]

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
    visibility = [
        "//packages/cmk-frontend-vue:__pkg__",
        "//packages/cmk-ui-library:__pkg__",
    ],
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

css_library(
    name = "themes_css",
    srcs = glob(["src/themes/**/*.scss"]),
)

py_test(
    name = "scss_content",
    srcs = ["tests/test_scss_content.py"],
    data = [":themes_css"],
    main = "tests/test_scss_content.py",
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

sh_library(
    name = "helpers",
    srcs = [
        ".f12",
        "run",
        "src/openapi/.f12",
    ],
)
