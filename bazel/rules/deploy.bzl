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

_ProductWheelsInfo = provider(
    doc = "Transitive py_wheel labels found in the product's dependency graph.",
    fields = {"labels": "depset of label strings"},
)

def _product_wheels_aspect_impl(target, ctx):
    own = []
    if PyWheelInfo in target and not target.label.workspace_name:
        # External wheels are skipped: they are not built from this repo.
        own.append("//{}:{}".format(target.label.package, target.label.name))

    transitive = []
    for attr_name in dir(ctx.rule.attr):
        value = getattr(ctx.rule.attr, attr_name, None)
        if type(value) == "Target":
            deps = [value]
        elif type(value) == "list":
            deps = [v for v in value if type(v) == "Target"]
        elif type(value) == "dict":
            deps = [k for k in value.keys() if type(k) == "Target"]
        else:
            continue
        for dep in deps:
            if _ProductWheelsInfo in dep:
                transitive.append(dep[_ProductWheelsInfo].labels)

    return [_ProductWheelsInfo(labels = depset(own, transitive = transitive))]

_product_wheels_aspect = aspect(
    implementation = _product_wheels_aspect_impl,
    attr_aspects = ["*"],
)

def _deploy_python_drift_test_impl(ctx):
    product = {
        label.replace("wheel-for-pkg_tar-", "wheel-for-f12-"): None
        for label in ctx.attr.product[_ProductWheelsInfo].labels.to_list()
    }
    deployed = {
        "//{}:{}".format(whl.label.package, whl.label.name): None
        for whl in ctx.attr.whls
    }

    product_file = ctx.actions.declare_file(ctx.label.name + ".product")
    ctx.actions.write(product_file, "\n".join(sorted(product)) + "\n")
    deployed_file = ctx.actions.declare_file(ctx.label.name + ".deployed")
    ctx.actions.write(deployed_file, "\n".join(sorted(deployed)) + "\n")

    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(script, """#!/bin/bash
if ! diff -u "{product}" "{deployed}"; then
    echo
    echo "The edition wheel lists in bazel/rules/deploy.bzl drifted from the" 1>&2
    echo "product definition (omd/BUILD). Update the lists to match the diff" 1>&2
    echo "above ('-' = shipped but not deployed, '+' = deployed but not shipped)." 1>&2
    exit 1
fi
""".format(
        product = product_file.short_path,
        deployed = deployed_file.short_path,
    ), is_executable = True)

    return [DefaultInfo(
        executable = script,
        runfiles = ctx.runfiles(files = [product_file, deployed_file]),
    )]

deploy_python_drift_test = rule(
    implementation = _deploy_python_drift_test_impl,
    attrs = {
        "product": attr.label(
            mandatory = True,
            aspects = [_product_wheels_aspect],
        ),
        "whls": attr.label_list(providers = [PyWheelInfo]),
    },
    test = True,
)

# NOTE: omd/BUILD is the source of truth for what constitutes an edition.
# The lists below must stay in sync with it; //:deploy-python-drift-test
# fails with a diff when they drift. Two deliberate deviations:
#
# * The product ships the wheel-for-pkg_tar-* plugin wheels and adds the
#   libexec files via a separate tar (CMK-27714 workaround, see
#   packages/cmk-plugins/BUILD). We deploy the wheel-for-f12-* siblings,
#   which carry the libexec files inside the wheel.
# * External wheels (e.g. @rrdtool_native) are not deployed: they are not
#   built from this repo, so they cannot change during development.
#
# Once CMK-27714 is fixed and the wheel duplication in cmk-plugins is gone,
# these lists can be replaced by collecting the product's wheels directly
# (see _product_wheels_aspect below).

COMMUNITY_WHEELS = [
    "//cmk:whl",
    "//packages/cmk-agent-receiver:wheel",
    "//packages/cmk-backup:wheel",
    "//packages/cmk-ccc:wheel",
    "//packages/cmk-check-engine:wheel",
    "//packages/cmk-crash:wheel",
    "//packages/cmk-crypto:wheel",
    "//packages/cmk-ec:wheel",
    "//packages/cmk-events:wheel",
    "//packages/cmk-flags:wheel",
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
