UPSTREAM_MIRROR_URL = "https://artifacts.lan.tribe29.com/repository/upstream-archives/"
RUFF_VERSION = "0.9.6"

edition_deps = {
    # NOTES:
    # * jaeger should be added to all editions EXCEPT saas - saas has its own tracing collector
    "cre": [
        "//omd/packages/jaeger:pkg_tar",
    ],
    "cce": [
        "//non-free/packages/cmk-mknotifyd:pkg_tar",
        "//non-free/packages/cmc-protocols:pkg_tar",
        "//non-free/packages/cmk-otel-collector:pkg_tar",
        "//non-free/packages/cmk-update-agent:pkg_tar",
        "//omd/packages/jaeger:pkg_tar",
    ],
    "cee": [
        "//non-free/packages/cmk-mknotifyd:pkg_tar",
        "//non-free/packages/cmc-protocols:pkg_tar",
        "//non-free/packages/cmk-update-agent:pkg_tar",
        "//omd/packages/jaeger:pkg_tar",
    ],
    "cme": [
        "//non-free/packages/cmk-mknotifyd:pkg_tar",
        "//non-free/packages/cmc-protocols:pkg_tar",
        "//non-free/packages/cmk-otel-collector:pkg_tar",
        "//non-free/packages/cmk-update-agent:pkg_tar",
        "//omd/packages/jaeger:pkg_tar",
    ],
    "cse": [
        "//non-free/packages/cmk-mknotifyd:pkg_tar",
        "//non-free/packages/cmc-protocols:pkg_tar",
        "//non-free/packages/cmk-otel-collector:pkg_tar",
        "//non-free/packages/cmk-update-agent:pkg_tar",
    ],
}

edition_skel_permissions = {
    "cre": [
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//omd/packages/jaeger:skel.permissions",
    ],
    "cce": [
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//omd/packages/jaeger:skel.permissions",
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
    "cee": [
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//omd/packages/jaeger:skel.permissions",
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
    "cme": [
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//omd/packages/jaeger:skel.permissions",
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
    "cse": [
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
}
