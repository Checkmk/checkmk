# Rules to fix binaries for deployment.
# For example setting the RPATH
load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

# Set RPATH for a whole directory with unknown file names
def _write_omd_spec_impl(ctx):
    omd_spec = ctx.outputs.omd_spec

    # create omd.spec from omd.spec.in
    ctx.actions.run_shell(
        inputs = [ctx.file.omd_spec_in, ctx.file.dependencies],
        outputs = [omd_spec],
        command = """
                DEPENDENCIES=$(cat {DEPENDENCIES_FILE}) ; \
                sed -e "s/^Requires:.*/Requires:       $DEPENDENCIES/" \
                    -e 's/%{version}/{CMK_VERSION}.{CMK_EDITION}/g' \
                    -e 's/%{edition}/{CMK_EDITION}/g' \
                    -e "s/%{pkg_version}/{CMK_VERSION}/g" \
                    -e 's/^Release:.*/Release: 38/' \
                    -e 's/^Version:.*/Version: {DISTRO_CODE}/' \
                    -e 's#@APACHE_CONFDIR@#{APACHE_CONF_DIR}#g' \
                    -e 's#@APACHE_NAME@#{APACHE_INIT_NAME}#g' \
                    {OMD_SPEC_IN} > {OMD_SPEC}
                if [ "{CMK_EDITION}" =  "community" ]; then \
                    sed -i '/icmpsender/d;/icmpreceiver/d' {OMD_SPEC} ; \
                fi \
        """.format(
            OMD_SPEC_IN = ctx.file.omd_spec_in.path,
            OMD_SPEC = omd_spec.path,
            DEPENDENCIES_FILE = ctx.file.dependencies.path,
            CMK_VERSION = ctx.attr.version[BuildSettingInfo].value,
            CMK_EDITION = ctx.attr.edition[BuildSettingInfo].value,
            DISTRO_CODE = ctx.attr.distro_code,
            APACHE_CONF_DIR = ctx.attr.apache_conf_dir,
            APACHE_INIT_NAME = ctx.attr.apache_init_name,
            version = "{version}",
            pkg_version = "{pkg_version}",
            edition = "{edition}",
        ),
    )

write_omd_spec = rule(
    implementation = _write_omd_spec_impl,
    attrs = {
        "omd_spec_in": attr.label(allow_single_file = True, providers = ["files"], mandatory = True),
        "omd_spec": attr.output(mandatory = True),
        "version": attr.label(mandatory = True),
        "edition": attr.label(mandatory = True),
        "apache_init_name": attr.string(mandatory = True),
        "apache_conf_dir": attr.string(mandatory = True),
        "dependencies": attr.label(allow_single_file = True, providers = ["files"], mandatory = True),
        "distro_code": attr.string(mandatory = True),
    },
)
