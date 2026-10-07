load("@aspect_rules_js//js:defs.bzl", "js_binary", "js_library")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")

js_library(
    name = "diagnostic-formatter",
    srcs = ["rust.diagnostic-formatter.cjs"],
    tags = ["no-lint"],  # vendored
)

js_binary(
    name = "cli",
    data = [":diagnostic-formatter"],
    entry_point = "rust.cli.cjs",
    visibility = ["//visibility:public"],
)

sh_binary(
    name = "process_wrapper_wrapper",
    srcs = ["process_wrapper_wrapper.bash"],
    data = ["@rules_rust//util/process_wrapper"],
    tags = ["no-lint"],  # vendored
    visibility = ["//visibility:public"],
    deps = ["@rules_shell//shell/runfiles"],
)
