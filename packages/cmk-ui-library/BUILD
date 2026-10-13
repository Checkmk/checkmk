load("@aspect_rules_js//js:defs.bzl", "js_library")
load("//bazel/rules:link_shared_typing.bzl", "link_shared_typing")
load("//bazel/rules:vue_package.bzl", "vue_package")

link_shared_typing()

vue_package(
    name = "cmk-ui-library",
    test_deps = [
        ":node_modules/@testing-library",
        ":node_modules/msw",
        ":node_modules/vue-component-type-helpers",
        ":vitest_msw",
        ":vitest_shared",
        ":vitest_shared_setup",
        "//packages/cmk-frontend:theme_images",
    ],
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
    ],
)

js_library(
    name = "vitest_shared_setup",
    srcs = ["vitest.shared-setup.ts"],
    visibility = ["//packages/cmk-frontend-vue:__pkg__"],
    deps = [
        ":node_modules/@testing-library",
        "//:node_modules/vitest",
    ],
)

js_library(
    name = "vitest_msw",
    srcs = ["vitest.msw.ts"],
    visibility = ["//packages/cmk-frontend-vue:__pkg__"],
    deps = [
        ":node_modules/msw",
        "//:node_modules/vitest",
    ],
)

js_library(
    name = "vitest_shared",
    srcs = ["vitest.shared.ts"],
    visibility = ["//packages/cmk-frontend-vue:__pkg__"],
    deps = ["//:node_modules/vitest"],
)
