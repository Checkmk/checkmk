filegroup(
    name = "srcs",
    srcs = glob(
        ["**"],
        exclude = [
            "BUILD",
            "**/OWNERS",
        ],
    ),
    visibility = ["//visibility:public"],
)

sh_library(
    name = "agents_cfg_examples_sh",
    srcs = [
        "dnsclient.cfg",
        "encryption.cfg",
        "exclude_sections.cfg",
        "exclude_sections_aix.cfg",
        "informix.cfg",
        "jar_signature.cfg",
        "lnx_container_host_if.cfg",
        "mk_inventory.cfg",
        "mk_oracle.cfg",
        "mk_redis.cfg",
        "mk_scaleio.cfg",
        "real_time_checks.cfg",
        "saprouter.cfg",
        "site_object_counts.cfg",
        "sqlplus.sh",
        "tsm.cfg",
    ],
    visibility = ["//visibility:public"],
)
