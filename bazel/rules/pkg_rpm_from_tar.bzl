# Rules to fix binaries for deployment.
# For example setting the RPATH
load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

# Set RPATH for a whole directory with unknown file names
def _pkg_rpm_from_tar_impl(ctx):
    default_output = ctx.outputs.rpm
    outputs = [default_output]

    output_name = "check-mk-{edition}-{cmk_version}-{distro_code}-38.x86_64.rpm".format(
        edition = ctx.attr.edition[BuildSettingInfo].value,
        cmk_version = ctx.attr.version[BuildSettingInfo].value,
        distro_code = ctx.attr.distro_code,
    )
    output_file = ctx.actions.declare_file(output_name)
    outputs.append(output_file)
    ctx.actions.symlink(
        output = ctx.outputs.rpm,
        target_file = output_file,
    )

    ctx.actions.run_shell(
        inputs = [ctx.file.input_tarball, ctx.file.omd_spec],
        outputs = [output_file],
        command = """
        set -x
            RPM_TOPDIR=$PWD/rpm/topdir
            RPM_BUILDROOT=$PWD/rpm/buildroot
            ROOT_DIR=$PWD

            mkdir -p ${RPM_TOPDIR}/{SOURCES,BUILD,RPMS,SRPMS,SPECS}
            mkdir -p ${RPM_BUILDROOT}

            sed -i "s|make -C \\$REPO_PATH/omd DESTDIR=\\$RPM_BUILD_ROOT install|tar xf $ROOT_DIR/%s -C \\$RPM_BUILD_ROOT|" %s

            NO_BRP_CHECK_RPATH="yes" \
            NO_BRP_STALE_LINK_ERROR="yes" \
            rpmbuild -bb --define "_topdir ${RPM_TOPDIR}" \
                --buildroot=${RPM_BUILDROOT} %s
            mv ${RPM_TOPDIR}/RPMS/*/*.rpm %s
        """ % (ctx.file.input_tarball.path, ctx.file.omd_spec.path, ctx.file.omd_spec.path, output_file.path),
    )

pkg_rpm_from_tar = rule(
    implementation = _pkg_rpm_from_tar_impl,
    attrs = {
        "input_tarball": attr.label(allow_single_file = True, providers = ["files"], mandatory = True),
        "rpm": attr.output(mandatory = True),
        "omd_spec": attr.label(allow_single_file = True, providers = ["files"], mandatory = True),
        "version": attr.label(mandatory = True),
        "edition": attr.label(mandatory = True),
        "distro_code": attr.string(mandatory = True),
    },
)
