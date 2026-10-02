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
)
