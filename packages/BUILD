filegroup(
    # TODO: De-dup with list in cmk/BUILD:CMK_PACKAGES
    name = "python_requirements",
    srcs = [
        "//packages/cmk-agent-receiver:requirements.in",
        "//packages/cmk-ccc:requirements.in",
        "//packages/cmk-crypto:requirements.in",
        "//packages/cmk-events:requirements.in",
        "//packages/cmk-livestatus-client:requirements.in",
        "//packages/cmk-messaging:requirements.in",
        "//packages/cmk-mkp-tool:requirements.in",
        "//packages/cmk-plugin-apis:requirements.in",
        "//packages/cmk-trace:requirements.in",
        "//packages/cmk-werks:requirements.in",
    ],
    visibility = ["//visibility:public"],
)
