"""Macro to declare an OMD package with name, version, CPE, and license metadata."""

load("@package_metadata//licenses/rules:license.bzl", "license")
load("@package_metadata//providers:package_attribute_info.bzl", "PackageAttributeInfo")
load("@package_metadata//rules:package_metadata.bzl", "package_metadata")

def _cpe_impl(ctx):
    attribute = {"cpe": ctx.attr.cpe}
    output = ctx.actions.declare_file("{}.package-attribute.json".format(ctx.attr.name))
    ctx.actions.write(output = output, content = json.encode(attribute))
    return [
        DefaultInfo(files = depset(direct = [output])),
        PackageAttributeInfo(
            kind = "com.checkmk.dependency_management.cpe",
            attributes = output,
        ),
    ]

_cpe = rule(
    implementation = _cpe_impl,
    attrs = {
        "cpe": attr.string(
            mandatory = True,
        ),
    },
)

def _strip_version_suffix(version):
    parts = version.split(".")
    if len(parts) >= 2 and parts[-1].isdigit() and parts[-2] in ("cmk", "bcr"):
        return ".".join(parts[:-2])
    return version

def dependency_info(
        *,
        name,
        package_name,
        version,
        cpe_format_str = None,
        license_kind = None,
        license_text = None,
        purl_type = "generic",
        purl_namespace = None):
    """Declares package metadata including package_name, version, CPE, and license.

    Args:
        name: the name used by the resulting package_metadata,
        package_name: name of the package,
        version: version of the package,
        cpe_format_str: Optional: used to generate the cpe (`cpe_format_str % version`)
        license_kind: Optional: one of "@package_metadata//licenses/spdx:Apache-2.0"
        license_text: Optional: add the file to the original license text
        purl_type: Optional: Used in the PURL e.g. generic, pypi, cargo
        purl_namespace: Optional: Used in the PURL

    """
    stripped_version = _strip_version_suffix(version)

    purl_name = "{}/{}".format(purl_namespace, package_name) if purl_namespace else package_name
    purl = "pkg:{}/{}@{}".format(purl_type, purl_name, stripped_version)

    attributes = []
    if cpe_format_str:
        _cpe(
            name = "{}-cpe".format(name),
            cpe = cpe_format_str % stripped_version,
            # If we omit this, we might get default_package_metadata which could lead to circular deps
            applicable_licenses = [],
        )
        attributes.append(":{}-cpe".format(name))
    if license_kind:
        license(
            name = "{}-license".format(name),
            kind = license_kind,
            text = license_text,
        )
        attributes.append(":{}-license".format(name))

    package_metadata(
        name = name,
        purl = purl,
        attributes = attributes,
    )
