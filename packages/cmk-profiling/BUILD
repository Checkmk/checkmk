load("@aspect_rules_js//js:defs.bzl", "js_library")
load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@npm//:vue-tsc/package_json.bzl", vue_tsc_bin = "bin")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:link_shared_typing.bzl", "link_shared_typing")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")
load("//bazel/rules:vitest_test.bzl", "vitest_test")
load("//bazel/rules:vue_library.bzl", "vue_library")

exports_files([
    "dev-requirements.in",
    "requirements.in",
])

py_library(
    name = "backend",
    srcs = [
        "cmk/profiling/backend/__init__.py",
        "cmk/profiling/backend/_flamegraph.py",
        "cmk/profiling/backend/_profile.py",
        "cmk/profiling/backend/_store.py",
    ],
    data = [":backend_py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-ccc:store",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "gui",
    srcs = [
        "cmk/profiling/gui/__init__.py",
        "cmk/profiling/gui/_store.py",
        "cmk/profiling/gui/pages.py",
    ],
    data = [":gui_py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":backend",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/watolib",
        "//cmk/utils:paths",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        "//packages/cmk-web/cmk/web/utils",
    ],
)

filegroup(
    name = "backend_py_typed",
    srcs = ["cmk/profiling/backend/py.typed"],
)

filegroup(
    name = "gui_py_typed",
    srcs = ["cmk/profiling/gui/py.typed"],
)

py_library(
    name = "plugins",
    srcs = glob(["cmk/plugins/**/*.py"]),
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//packages/cmk-profiling:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":backend",
        "//packages/cmk-plugin-apis:diagnostics",
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-profiling",
    strip_path_prefixes = ["packages/cmk-profiling"],
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":backend",
        ":backend_py_typed",
        ":gui",
        ":gui_py_typed",
        ":plugins",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":backend",
        ":gui",
        ":plugins",
    ],
    requirements_in = "requirements.in",
)

link_shared_typing()

npm_link_all_packages(name = "node_modules")

vue_library(
    name = "cmk-profiling",
    srcs = glob([
        "*.d.ts",
        "frontend/**/*.ts",
        "frontend/**/*.vue",
    ]) + [
        "package.json",
        "tsconfig.json",
        "tsconfig.test.json",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":node_modules/@tanstack",
        ":node_modules/cmk-shared-typing-bzl",
        ":node_modules/cmk-ui-library",
        ":node_modules/vite",
    ],
)

js_library(
    name = "eslintrc",
    srcs = ["eslint.config.mjs"],
    tags = ["no-lint"],
    visibility = ["//visibility:public"],
    deps = [
        ":cmk-profiling",
        "//packages/cmk-ui-library:eslintrc",
    ],
)

filegroup(
    name = "srcs",
    srcs = glob([
        "*.d.ts",
        "frontend/**",
    ]) + [
        "eslint.config.mjs",
        "package.json",
        "tsconfig.json",
        "tsconfig.test.json",
        "vite.config.ts",
        "//packages/cmk-profiling/tests/frontend:srcs",
    ],
    visibility = ["//visibility:public"],
)

vue_tsc_bin.vue_tsc_test(
    name = "type-check",
    args = [
        "-p",
        "tsconfig.json",
    ],
    chdir = package_name(),
    data = [
        ":cmk-profiling",
        "//:node_modules/@vue/compiler-dom",
        "//:node_modules/@vue/server-renderer",
        "//:node_modules/@vue/test-utils",
        "//:node_modules/jsdom",
        "//:node_modules/sass-embedded",
        "//:node_modules/vitest",
        "//:node_modules/vitest-fail-on-console",
        "//:node_modules/vue",
        "//:node_modules/vue-tsc",
    ],
    include_types = True,
)

vue_tsc_bin.vue_tsc_test(
    name = "type-check-tests",
    args = [
        "-p",
        "tsconfig.test.json",
    ],
    chdir = package_name(),
    data = [
        "tsconfig.test.json",
        "vite.config.ts",
        ":cmk-profiling",
        ":node_modules/@testing-library",
        ":node_modules/@vitejs",
        ":node_modules/msw",
        "//:node_modules/@vue/compiler-dom",
        "//:node_modules/@vue/server-renderer",
        "//:node_modules/@vue/test-utils",
        "//:node_modules/jsdom",
        "//:node_modules/sass-embedded",
        "//:node_modules/vitest",
        "//:node_modules/vitest-fail-on-console",
        "//:node_modules/vue",
        "//:node_modules/vue-tsc",
        "//packages/cmk-frontend:theme_images",
        "//packages/cmk-profiling/tests/frontend",
        "//packages/cmk-ui-library:vitest_msw",
        "//packages/cmk-ui-library:vitest_shared_setup",
    ],
    include_types = True,
)

vitest_test(
    name = "unit-test",
    data = [
        "tsconfig.test.json",
        "vite.config.ts",
        ":cmk-profiling",
        ":node_modules/@testing-library",
        ":node_modules/@vitejs",
        ":node_modules/msw",
        "//:node_modules/@vue/compiler-dom",
        "//:node_modules/@vue/server-renderer",
        "//:node_modules/@vue/test-utils",
        "//:node_modules/jsdom",
        "//:node_modules/sass-embedded",
        "//:node_modules/vitest",
        "//:node_modules/vitest-fail-on-console",
        "//:node_modules/vue",
        "//:node_modules/vue-tsc",
        "//packages/cmk-frontend:theme_images",
        "//packages/cmk-profiling/tests/frontend",
        "//packages/cmk-ui-library:vitest_msw",
        "//packages/cmk-ui-library:vitest_shared_setup",
    ],
)
