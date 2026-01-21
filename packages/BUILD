filegroup(
    # TODO: De-dup with list in cmk/BUILD:CMK_PACKAGES
    name = "python_requirements",
    srcs = [
        "//packages/cmk-agent-receiver:requirements.in",
        "//packages/cmk-ccc:requirements.in",
        "//packages/cmk-check-engine:requirements.in",
        "//packages/cmk-crypto:requirements.in",
        "//packages/cmk-ec:requirements.in",
        "//packages/cmk-events:requirements.in",
        "//packages/cmk-livestatus-client:requirements.in",
        "//packages/cmk-messaging:requirements.in",
        "//packages/cmk-mkp-tool:requirements.in",
        "//packages/cmk-plugin-apis:requirements.in",
        "//packages/cmk-plugins:requirements.in",
        "//packages/cmk-trace:requirements.in",
        "//packages/cmk-werks:requirements.in",
    ],
    visibility = ["//visibility:public"],
)

filegroup(
    name = "dev_python_requirements",
    srcs = [
        "//packages/cmk-agent-receiver:dev-requirements.in",
        "//packages/cmk-astrein:requirements.in",
        "//packages/cmk-ccc:dev-requirements.in",
        "//packages/cmk-check-engine:dev-requirements.in",
        "//packages/cmk-crypto:dev-requirements.in",
        "//packages/cmk-ec:dev-requirements.in",
        "//packages/cmk-events:dev-requirements.in",
        "//packages/cmk-livestatus-client:dev-requirements.in",
        "//packages/cmk-messaging:dev-requirements.in",
        "//packages/cmk-mkp-tool:dev-requirements.in",
        "//packages/cmk-plugin-apis:dev-requirements.in",
        "//packages/cmk-relay-protocols:dev-requirements.in",
        "//packages/cmk-trace:dev-requirements.in",
        "//packages/cmk-werks:dev-requirements.in",
    ],
    visibility = ["//visibility:public"],
)
