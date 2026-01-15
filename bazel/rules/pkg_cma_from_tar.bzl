# Rules to create CMA archive with custom extension .cma
load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

def _pkg_cma_from_tar_impl(ctx):
    default_output = ctx.outputs.cma
    outputs = [default_output]

    output_name = "check-mk-{edition}-{cmk_version}-{distro_code}-x86_64.cma".format(
        edition = ctx.attr.edition[BuildSettingInfo].value,
        cmk_version = ctx.attr.version[BuildSettingInfo].value,
        # Distro code is a single version number, e.g. "4"
        distro_code = ctx.attr.distro_code,
    )
    output_file = ctx.actions.declare_file(output_name)
    outputs.append(output_file)
    ctx.actions.symlink(
        output = ctx.outputs.cma,
        target_file = output_file,
    )

    # Create a link with our desired name pointing at the input tarball
    ctx.actions.symlink(
        output = output_file,
        target_file = ctx.file.input_tarball,
    )

pkg_cma_from_tar = rule(
    implementation = _pkg_cma_from_tar_impl,
    attrs = {
        "input_tarball": attr.label(allow_single_file = True, providers = ["files"], mandatory = True),
        "cma": attr.output(mandatory = True),
        "version": attr.label(mandatory = True, providers = [BuildSettingInfo]),
        "edition": attr.label(mandatory = True, providers = [BuildSettingInfo]),
        "distro_code": attr.string(mandatory = True),
    },
)
