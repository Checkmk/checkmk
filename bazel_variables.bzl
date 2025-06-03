UPSTREAM_MIRROR_URL = "https://artifacts.lan.tribe29.com/repository/upstream-archives/"
RUFF_VERSION = "0.11.11"

# TODO: Re-work this with edition_deps + check for duplicate in cmk/BUILD
edition_python_deps = {
    "cre": [],
    "cce": [
        "//non-free/packages/cmk-mknotifyd",
        "//non-free/packages/cmk-otel-collector",
        "//non-free/packages/cmk-update-agent",
    ],
    "cee": [
        "//non-free/packages/cmk-mknotifyd",
        "//non-free/packages/cmk-update-agent",
    ],
    "cme": [
        "//non-free/packages/cmk-mknotifyd",
        "//non-free/packages/cmk-update-agent",
        "//non-free/packages/cmk-otel-collector",
    ],
    "cse": [
        "//non-free/packages/cmk-mknotifyd",
        "//non-free/packages/cmk-update-agent",
        "//non-free/packages/cmk-otel-collector",
    ],
}

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
        "//omd/packages/nagios:skel.permissions",
        "//omd/packages/rabbitmq:skel.permissions",
    ],
    "cce": [
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//omd/packages/jaeger:skel.permissions",
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
        "//omd/packages/nagios:skel.permissions",
        "//omd/packages/rabbitmq:skel.permissions",
    ],
    "cee": [
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//omd/packages/jaeger:skel.permissions",
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
        "//omd/packages/nagios:skel.permissions",
        "//omd/packages/rabbitmq:skel.permissions",
    ],
    "cme": [
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//omd/packages/jaeger:skel.permissions",
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
        "//omd/packages/nagios:skel.permissions",
        "//omd/packages/rabbitmq:skel.permissions",
    ],
    "cse": [
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
        "//omd/packages/nagios:skel.permissions",
        "//omd/packages/rabbitmq:skel.permissions",
    ],
}
