load("@aspect_rules_js//js:defs.bzl", "js_library")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("//bazel/rules:link_shared_typing.bzl", "link_shared_typing")
load("//bazel/rules:vitest_test.bzl", "vitest_test")
load("//bazel/rules:vue_library.bzl", "vue_library")

link_shared_typing()

npm_link_all_packages(name = "node_modules")

vue_library(
    name = "cmk-ui-library",
    srcs = glob([
        "*.d.ts",
        "assets/**/*.svg",
        "components/**/*.ts",
        "components/**/*.vue",
        "lib/**/*.ts",
        "lib/**/*.vue",
    ]) + [
        "package.json",
        "tsconfig.json",
        "tsconfig.test.json",
        "tsconfig.vue-base.json",
    ],
    tsconfig = "tsconfig.json",
    visibility = ["//visibility:public"],
    deps = [
        ":node_modules/@internationalized",
        ":node_modules/@types",
        ":node_modules/@vitejs",
        ":node_modules/class-variance-authority",
        ":node_modules/cmk-shared-typing-bzl",
        ":node_modules/openapi-fetch",
        ":node_modules/reka-ui",
        ":node_modules/sanitize-html",
        ":node_modules/typescript",
        ":node_modules/vite",
        ":node_modules/vue3-gettext",
        "//:node_modules/vue",
    ],
)

js_library(
    name = "vitest_isolated",
    srcs = ["vitest.isolated.json"],
)

js_library(
    name = "eslintrc",
    srcs = [
        "eslint.config.mjs",
        "eslint.shared.mjs",
    ],
    tags = ["no-lint"],
    visibility = ["//visibility:public"],
    deps = [
        ":cmk-ui-library",
        ":vitest_isolated",
    ],
)

filegroup(
    name = "srcs",
    srcs = glob(
        ["**"],
        exclude = ["node_modules/**"],
    ),
    visibility = ["//visibility:public"],
)

js_library(
    name = "vitest_shared_setup",
    srcs = ["vitest.shared-setup.ts"],
    visibility = ["//packages:__subpackages__"],
    deps = [
        ":node_modules/@testing-library",
        "//:node_modules/vitest",
    ],
)

js_library(
    name = "vitest_msw",
    srcs = ["vitest.msw.ts"],
    visibility = ["//packages:__subpackages__"],
    deps = [
        ":node_modules/cmk-shared-typing-bzl",
        ":node_modules/msw",
        ":node_modules/openapi-msw",
        "//:node_modules/vitest",
    ],
)

js_library(
    name = "vitest_shared",
    srcs = ["vitest.shared.ts"],
    visibility = ["//packages/cmk-frontend-vue:__pkg__"],
    deps = ["//:node_modules/vitest"],
)

vue_library(
    name = "tests",
    srcs = glob(["tests/**/*.ts"]),
    tsconfig = "tsconfig.test.json",
    deps = [
        ":cmk-ui-library",
        ":node_modules/@testing-library",
        ":node_modules/msw",
        ":node_modules/vue-component-type-helpers",
        ":vitest_msw",
        ":vitest_shared",
        ":vitest_shared_setup",
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
)

vitest_test(
    name = "unit-test",
    data = [
        "tsconfig.test.json",
        "vite.config.ts",
        ":tests",
        ":vitest_isolated",
        "//packages/cmk-frontend:theme_images",
    ],
    shard_count = 4,
)
