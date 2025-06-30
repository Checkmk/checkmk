load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")
load("@rules_pkg//pkg:providers.bzl", "PackageVariablesInfo")

def _pkg_name_info_impl(ctx):
    values = {}

    values["cmk_version"] = ctx.attr.cmk_version[BuildSettingInfo].value
    values["package"] = ctx.attr.package
    values["version"] = ctx.attr.version
    values["architecture"] = ctx.attr.architecture

    return PackageVariablesInfo(values = values)

pkg_name_info = rule(
    implementation = _pkg_name_info_impl,
    doc = "A rule to inject variables from the build file into package names.",
    attrs = {
        "cmk_version": attr.label(mandatory = True),
        "package": attr.string(mandatory = True),
        "version": attr.string(mandatory = True),
        "architecture": attr.string(mandatory = True),
    },
)
