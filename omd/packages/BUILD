load("@rules_pkg//pkg:mappings.bzl", "pkg_files")

SKEL_PERM = [
    "//omd/packages/stunnel:skel.permissions",
    "//omd/packages/rrdtool:skel.permissions",
    "//omd/packages/nagvis:skel.permissions",
    "//omd/packages/apache-omd:skel.permissions",
    "//omd/packages/jaeger:skel.permissions",
    "//omd/packages/enterprise:skel.permissions",
    "//omd/packages/check_mk:skel.permissions",
    "//omd/packages/perl-modules:skel.permissions",
    "//omd/packages/nagios:skel.permissions",
    "//omd/packages/redis:skel.permissions",
    "//omd/packages/openssl:skel.permissions",
    "//omd/packages/pnp4nagios:skel.permissions",
    "//omd/packages/omd:skel.permissions",
    "//omd/packages/rabbitmq:skel.permissions",
    "//omd/packages/maintenance:skel.permissions",
]

[genrule(
    name = "skel_permissions_" + edition,
    srcs = SKEL_PERM + {
        "cre": [],
        "cce": [
            "//non-free/packages/cmk-mknotifyd:skel.permissions",
            "//non-free/packages/otel-collector:skel.permissions",
        ],
        "cee": [
            "//non-free/packages/cmk-mknotifyd:skel.permissions",
        ],
        "cme": [
            "//non-free/packages/cmk-mknotifyd:skel.permissions",
            "//non-free/packages/otel-collector:skel.permissions",
        ],
        "cse": [
            "//non-free/packages/cmk-mknotifyd:skel.permissions",
            "//non-free/packages/otel-collector:skel.permissions",
        ],
    }[edition],
    outs = ["skel.permissions_" + edition],
    cmd = "cat $(SRCS) > $@",
) for edition in [
    "cre",
    "cce",
    "cee",
    "cme",
    "cse",
]]

[pkg_files(
    name = "skel_permissions_pkg_" + edition,
    srcs = [
        ":skel.permissions_" + edition,
    ],
    prefix = "share/omd",
    renames = {
        "skel.permissions_" + edition: "skel.permissions",
    },
    visibility = [
        "//omd:__pkg__",
    ],
) for edition in [
    "cre",
    "cce",
    "cee",
    "cme",
    "cse",
]]
