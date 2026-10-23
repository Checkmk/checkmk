"""Verifies when the agent .rpm gets signed and when release packages build.

The real consumers (//agents:agents, //omd:agent_package_signing_guard) can't
be the target under test: an incompatible target under test makes the test
itself incompatible, i.e. skipped instead of failed. So probes resolve the
same select()s from agent_package_signing.bzl that the consumers use. Whether
the release packages actually depend on the guard isn't covered here.
"""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")
load(
    "//bazel/rules:agent_package_signing.bzl",
    "requires_signed_agent_rpm",
    "signed_or_unsigned_agent_rpm",
)

_ProbeInfo = provider(
    doc = "What a probe's select() resolved to.",
    fields = {"value": "The resolved value, as a string."},
)

def _agent_rpm_probe_impl(ctx):
    return [_ProbeInfo(value = ctx.attr.agent_rpm)]

_agent_rpm_probe = rule(
    implementation = _agent_rpm_probe_impl,
    attrs = {"agent_rpm": attr.string(mandatory = True)},
)

def agent_rpm_probe(name, **kwargs):
    """Resolves to "signed" or "unsigned", like the agent .rpm in //agents:agents."""
    _agent_rpm_probe(
        name = name,
        agent_rpm = signed_or_unsigned_agent_rpm(signed = "signed", unsigned = "unsigned"),
        **kwargs
    )

def _release_packages_probe_impl(ctx):
    incompatible = Label("@platforms//:incompatible")
    refused = any([t.label == incompatible for t in ctx.attr.release_packages_compatible_with])
    return [_ProbeInfo(value = "refused" if refused else "built")]

_release_packages_probe = rule(
    implementation = _release_packages_probe_impl,
    attrs = {"release_packages_compatible_with": attr.label_list(mandatory = True)},
)

def release_packages_probe(name, **kwargs):
    """Resolves to "refused" or "built", like //omd:agent_package_signing_guard."""
    _release_packages_probe(
        name = name,
        release_packages_compatible_with = requires_signed_agent_rpm(),
        **kwargs
    )

def _impl(ctx):
    env = analysistest.begin(ctx)

    asserts.equals(
        env,
        ctx.attr.expected,
        analysistest.target_under_test(env)[_ProbeInfo].value,
    )

    return analysistest.end(env)

_DUMMY_KEY = "/dummy/analysis-test.key"

def _make(signing_key_file, disable_signing = False, use_faked_artifacts = False):
    # Always set every flag the policy depends on, so e.g. CI's
    # --//:use_faked_artifacts=true can't leak into a test.
    return analysistest.make(
        _impl,
        attrs = {"expected": attr.string(mandatory = True)},
        config_settings = {
            str(Label("//:disable_agent_package_signing")): disable_signing,
            str(Label("//:use_faked_artifacts")): use_faked_artifacts,
            str(Label("//bazel/rules:signing_key_file")): signing_key_file,
        },
    )

without_key_test = _make(signing_key_file = "")
without_key_signing_disabled_test = _make(signing_key_file = "", disable_signing = True)
without_key_faked_artifacts_test = _make(signing_key_file = "", use_faked_artifacts = True)
with_key_test = _make(signing_key_file = _DUMMY_KEY)
with_key_signing_disabled_test = _make(signing_key_file = _DUMMY_KEY, disable_signing = True)
with_key_faked_artifacts_test = _make(signing_key_file = _DUMMY_KEY, use_faked_artifacts = True)
