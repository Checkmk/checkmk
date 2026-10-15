load("@aspect_rules_js//js:defs.bzl", "js_library")

filegroup(
    name = "srcs",
    srcs = glob(["**/*.ts"]),
    visibility = ["//packages/cmk-profiling:__pkg__"],
)

js_library(
    name = "frontend",
    srcs = [":srcs"],
    visibility = ["//packages/cmk-profiling:__pkg__"],
    deps = [
        "//:node_modules/@vue/compiler-dom",
        "//:node_modules/@vue/server-renderer",
        "//:node_modules/@vue/test-utils",
        "//:node_modules/jsdom",
        "//:node_modules/sass-embedded",
        "//:node_modules/vitest",
        "//:node_modules/vitest-fail-on-console",
        "//:node_modules/vue",
        "//:node_modules/vue-tsc",
        "//packages/cmk-profiling",
        "//packages/cmk-profiling:node_modules/@testing-library",
        "//packages/cmk-profiling:node_modules/@vitejs",
        "//packages/cmk-profiling:node_modules/msw",
        "//packages/cmk-ui-library:vitest_msw",
        "//packages/cmk-ui-library:vitest_shared_setup",
    ],
)
