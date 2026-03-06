"""Macros for creating dependency lists and bills of materials."""

load("@bazel_skylib//rules:run_binary.bzl", "run_binary")
load("@supply_chain_tools//sbom:providers.bzl", "SbomInfo")
load("@supply_chain_tools//sbom:sbom.bzl", "sbom")

def _sbom_config_impl(ctx):
    config = ctx.attr.sbom[SbomInfo].config
    return [DefaultInfo(files = depset([config]))]

_sbom_config = rule(
    doc = "Extracts the config file from an sbom() target via SbomInfo provider.",
    implementation = _sbom_config_impl,
    attrs = {
        "sbom": attr.label(providers = [SbomInfo]),
    },
)

def dependency_list(name, sbom_target, manifest_srcs):
    """Generates a JSON list of all dependencies for a given Bazel target and given manifest files

    Args:
        name: base name for the generated targets
        sbom_target: the Bazel target to generate the sbom for
        manifest_srcs: additional manifest files (e.g. lock files) to pass to list_dependencies_bin
    """
    sbom(
        name = name + "_sbom",
        target = sbom_target,
        tags = ["manual"],
    )

    _sbom_config(
        name = name + "_sbom_config",
        sbom = ":" + name + "_sbom",
        tags = ["manual"],
    )

    manifest_args = [
        arg
        for src in manifest_srcs
        for arg in ("--manifest", "$(location " + src + ")")
    ]

    run_binary(
        name = name,
        srcs = [
            ":" + name + "_sbom",
            ":" + name + "_sbom_config",
        ] + manifest_srcs,
        outs = [name + ".json"],
        args = [
            "--bazel_info",
            "$(location :" + name + "_sbom_config)",
            "--out",
            "$(location " + name + ".json)",
        ] + manifest_args,
        tags = ["manual"],
        tool = "//omd/dependency_management:list_dependencies_bin",
    )

def bill_of_materials(name, dependencies, vulnerability_info):
    """Generates a CycloneDX bill of materials from a dependency list.

    Args:
        name: name of the generated target; output is {name}.json
        dependencies: label of the dependency list produced by dependency_list()
        vulnerability_info: yaml with info about vulnerabilities
    """
    args = [
        "--dependencies",
        "$(location " + dependencies + ")",
        "--out",
        "$(location " + name + ".json)",
    ]
    srcs = [dependencies]

    if vulnerability_info:
        args += [
            "--vulnerability_info",
            "$(location " + vulnerability_info + ")",
        ]
        srcs.append(vulnerability_info)

    run_binary(
        name = name,
        srcs = srcs,
        outs = [name + ".json"],
        args = args,
        tags = ["manual"],
        tool = "//omd/dependency_management:bill_of_materials_bin",
    )
