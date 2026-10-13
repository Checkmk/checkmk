"""Rule to build an RPM from a buildroot tarball and a static .spec file.

Unlike pkg_rpm_from_tar.bzl, which is tied to OMD's generated,
edition/distro-specific spec, this is for a plain static .spec relying only
on `--buildroot` + `%files`.
"""

load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

def _pkg_rpm_from_buildroot_impl(ctx):
    version = ctx.attr.version[BuildSettingInfo].value
    rpm_version = version.replace("-", "_")

    ctx.actions.run_shell(
        inputs = [ctx.file.buildroot_tar, ctx.file.spec],
        outputs = [ctx.outputs.rpm],
        arguments = [
            ctx.file.buildroot_tar.path,
            ctx.file.spec.path,
            ctx.outputs.rpm.path,
            version,
            rpm_version,
            ctx.attr.target_arch,
        ],
        command = """
            set -e
            buildroot_tar="$1" spec="$2" out="$3" version="$4" rpm_version="$5" target_arch="$6"
            topdir="$PWD/rpm/topdir"
            buildroot="$PWD/rpm/buildroot"
            mkdir -p "$topdir"/{SOURCES,BUILD,RPMS,SRPMS,SPECS,TMP} "$buildroot"
            tar xf "$buildroot_tar" -C "$buildroot"

            target_args=()
            [ -n "$target_arch" ] && target_args=(--target "$target_arch")

            # rpmbuild defaults %_tmppath to /var/tmp, which linux-sandbox
            # mounts read-only - use a writable scratch dir under our own
            # topdir instead.
            #
            # rpm 6's default package format writes a wrong payload size,
            # which later breaks signing - force the legacy v4 format.
            rpmbuild -bb \
                --define "_topdir $topdir" \
                --define "_tmppath $topdir/TMP" \
                --define "_version $version" \
                --define "_rpm_version $rpm_version" \
                --define "_rpmformat 4" \
                --buildroot="$buildroot" \
                "${target_args[@]}" \
                "$spec"
            mv "$topdir"/RPMS/*/*.rpm "$out"
        """,
    )

pkg_rpm_from_buildroot = rule(
    implementation = _pkg_rpm_from_buildroot_impl,
    doc = """Builds `rpm` by untarring `buildroot_tar` and running rpmbuild
against `spec`, filling in `_version`/`_rpm_version` (dashes replaced with
underscores) from `version`'s build setting. Pass `target_arch` (e.g.
"aarch64") to build for a non-native architecture via `rpmbuild --target`.
""",
    attrs = {
        "buildroot_tar": attr.label(allow_single_file = True, mandatory = True),
        "rpm": attr.output(mandatory = True),
        "spec": attr.label(allow_single_file = True, mandatory = True),
        "target_arch": attr.string(),
        "version": attr.label(mandatory = True),
    },
)
