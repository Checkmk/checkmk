"""Deploy Python packages"""

load("@aspect_bazel_lib//lib:paths.bzl", "to_rlocation_path")
load("@rules_python//python:packaging.bzl", "PyWheelInfo")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")

def _update_wheels_code(ctx, f):
    return "WHEELS+=(\"$(rlocation \"{whl}\")\")".format(whl = to_rlocation_path(ctx, f))

def _deploy_python_script_impl(ctx):
    whl_files = [whl[PyWheelInfo].wheel for whl in ctx.attr.whls]
    update_wheels = "\n".join([_update_wheels_code(ctx, f) for f in whl_files])

    script_content = """\
#!/bin/bash
set -euo pipefail
if test $# -ne 1; then
    echo "Usage: bazel run //{pkg}:{rule_name} --cmk_edition=<EDITION> -- <OMD_ROOT>" 1>&2
    exit 1
fi
OMD_ROOT="$1"
WHEELS=()
{update_wheels}
UV="$(rlocation "{uv}")"
"${{UV}}" pip install \
    --python "${{OMD_ROOT}}/bin/python3" \
    --no-deps \
    --upgrade \
    --force-reinstall \
    --no-config \
    --compile-bytecode \
    "${{WHEELS[@]}}"
""".format(
        update_wheels = update_wheels,
        pkg = ctx.label.package,
        rule_name = ctx.attr.rule_name,
        uv = to_rlocation_path(ctx, ctx.executable._uv),
    )

    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(script, script_content, is_executable = True)
    return [DefaultInfo(
        files = depset([script]),
        runfiles = ctx.attr._uv.default_runfiles,
    )]

_deploy_python_script = rule(
    implementation = _deploy_python_script_impl,
    attrs = {
        "rule_name": attr.string(mandatory = True),
        "whls": attr.label_list(providers = [PyWheelInfo]),
        "_uv": attr.label(
            default = "//bazel/tools:uv",
            executable = True,
            cfg = "exec",
        ),
    },
)

def _deploy_python_impl(name, whls, visibility):
    script_name = name + "_gen"
    _deploy_python_script(
        name = script_name,
        whls = whls,
        rule_name = name,
        visibility = ["//visibility:private"],
    )
    sh_binary(
        name = name,
        srcs = [script_name],
        data = whls,
        use_bash_launcher = True,
        visibility = visibility,
    )

deploy_python = macro(
    attrs = {
        "whls": attr.label_list(providers = [PyWheelInfo], configurable = True),
    },
    implementation = _deploy_python_impl,
)

# NOTE: omd/BUILD contains similar, but slightly different lists of artifacts
# which define what goes into a given edition. We should somehow remove this
# duplication. In the end, there should be a single source of truth for
# deployment and building a distro package regarding what actually constitutes
# an edition.

COMMUNITY_WHEELS = [
    "//cmk:whl",
    "//packages/cmk-agent-receiver:wheel",
    "//packages/cmk-backup:wheel",
    "//packages/cmk-ccc:wheel",
    "//packages/cmk-check-engine:wheel",
    "//packages/cmk-crypto:wheel",
    "//packages/cmk-ec:wheel",
    "//packages/cmk-events:wheel",
    "//packages/cmk-licensing:wheel",
    "//packages/cmk-livestatus-client:cmk-livestatus-client_whl",
    "//packages/cmk-livestatus-client:livestatus_whl",
    "//packages/cmk-logwatch:wheel",
    "//packages/cmk-messaging:wheel",
    "//packages/cmk-mkp-tool:wheel",
    "//packages/cmk-notification-plugins:wheel",
    "//packages/cmk-plugin-apis:wheel",
    "//packages/cmk-plugins:wheel-for-f12-aws",
    "//packages/cmk-plugins:wheel-for-f12-azure_deprecated",
    "//packages/cmk-plugins:wheel-for-f12-azure_v2",
    "//packages/cmk-plugins:wheel-for-f12-bazel",
    "//packages/cmk-plugins:wheel-for-f12-cisco_prime",
    "//packages/cmk-plugins:wheel-for-f12-dell",
    "//packages/cmk-plugins:wheel-for-f12-elasticsearch",
    "//packages/cmk-plugins:wheel-for-f12-gcp",
    "//packages/cmk-plugins:wheel-for-f12-gerrit",
    "//packages/cmk-plugins:wheel-for-f12-graylog",
    "//packages/cmk-plugins:wheel-for-f12-ipmi",
    "//packages/cmk-plugins:wheel-for-f12-jenkins",
    "//packages/cmk-plugins:wheel-for-f12-kube",
    "//packages/cmk-plugins:wheel-for-f12-lib",
    "//packages/cmk-plugins:wheel-for-f12-netapp",
    "//packages/cmk-plugins:wheel-for-f12-prism",
    "//packages/cmk-plugins:wheel-for-f12-proxmox_ve",
    "//packages/cmk-plugins:wheel-for-f12-pure_storage_fa",
    "//packages/cmk-plugins:wheel-for-f12-rabbitmq",
    "//packages/cmk-plugins:wheel-for-f12-randomds",
    "//packages/cmk-plugins:wheel-for-f12-redfish",
    "//packages/cmk-plugins:wheel-for-f12-splunk",
    "//packages/cmk-plugins:wheel-for-f12-stulz",
    "//packages/cmk-plugins:wheel-for-f12-tplink",
    "//packages/cmk-plugins:wheel-for-f12-ucs_bladecenter",
    "//packages/cmk-plugins:wheel-for-f12-vsphere",
    "//packages/cmk-relay-protocols:wheel",
    "//packages/cmk-shared-typing:wheel",
    "//packages/cmk-trace:wheel",
    "//packages/cmk-web:wheel",
    "//packages/cmk-werks:wheel",
]

PRO_WHEELS = COMMUNITY_WHEELS + [
    "//non-free/packages/cmc-protocols:wheel",
    "//non-free/packages/cmk-bakery:wheel",
    "//non-free/packages/cmk-core-helpers:wheel",
    "//non-free/packages/cmk-dcd:wheel",
    "//non-free/packages/cmk-licensing-nonfree:wheel",
    "//non-free/packages/cmk-liveproxyd:wheel",
    "//non-free/packages/cmk-mknotifyd:wheel",
    "//non-free/packages/cmk-notification-plugins-nonfree:wheel",
    "//non-free/packages/cmk-plugins-nonfree:wheel-kube_extended",
    "//non-free/packages/cmk-robotmk:wheel",
]

CLOUD_WHEELS = PRO_WHEELS + [
    "//non-free/packages/cmk-cloud:wheel",
    "//non-free/packages/cmk-core-helpers:relay-fetcher-trigger-wheel",
    "//non-free/packages/cmk-metric-backend:wheel",
    "//non-free/packages/cmk-otel-collector:wheel",
    "//non-free/packages/cmk-otel-collector:wheel-auth-only",
    "//non-free/packages/cmk-plugins-nonfree:wheel-azure_deprecated_extended",
    "//non-free/packages/cmk-plugins-nonfree:wheel-azure_v2_extended",
    "//non-free/packages/cmk-plugins-nonfree:wheel-gcp_extended",
    "//non-free/packages/cmk-telemetry:wheel",
]

ULTIMATE_WHEELS = PRO_WHEELS + [
    "//non-free/packages/cmk-core-helpers:relay-fetcher-trigger-wheel",
    "//non-free/packages/cmk-metric-backend:wheel",
    "//non-free/packages/cmk-otel-collector:wheel",
    "//non-free/packages/cmk-plugins-nonfree:wheel-aws_extended",
    "//non-free/packages/cmk-plugins-nonfree:wheel-azure_deprecated_extended",
    "//non-free/packages/cmk-plugins-nonfree:wheel-azure_v2_extended",
    "//non-free/packages/cmk-plugins-nonfree:wheel-gcp_extended",
    "//non-free/packages/cmk-telemetry:wheel",
]

ULTIMATEMT_WHEELS = ULTIMATE_WHEELS + [
    "//non-free/packages/cmk-multi-tenancy:wheel",
    "//non-free/packages/cmk-relay-engine:wheel",
]
