load("@rules_pkg//pkg:mappings.bzl", "pkg_files", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

genrule(
    name = "apache-omd",
    srcs = [
        "//omd/packages/apache-omd:apache.conf",
        "//omd/packages/apache-omd:APACHE_TCP_ADDR",
        "//omd/packages/apache-omd:APACHE_TCP_PORT",
    ],
    outs = ["apache-omd.tar.gz"],
    cmd = """
        # NOTE: lots of the content in here is just a brainless mapping from
        # what we did in the `apache-omd.make` without any fundamental
        # refactoring in mind. A future more bazelesk implementation should just
        # make sure our known requirements are met.
        #
        # Currently we store distro-specific configuration in a makefile called
        # /opt/<DISTRO>.mk, which get's copied when we build the build images.
        # In here we do nasty grepping to be as close to the former approach,
        # but as soon as possible we should get rid of those files and have
        # a Bazel-native approach instead (if needed at all)
        # see https://jira.lan.tribe29.com/browse/CMK-18674
        #
        ROOT_DIR=$$PWD
        (mkdir apache-omd; cd apache-omd
            # Install software below {bin,lib,share}
            mkdir -p share/omd
            install -m 644 $$ROOT_DIR/$(location //omd/packages/apache-omd:apache.conf) share/omd/apache.conf

            # Create distribution independent alias for htpasswd command, see https://checkmk.com/werk/5985
            mkdir -p bin
            # hacky way to retrieve HTPASSWD_BIN - we might as well store a
            # script trying to call `htpasswd2` or `htpasswd`
            HTPASSWD_BIN="$$(grep "HTPASSWD_BIN" /opt/*.mk | awk '{print $$3}')"
            if [ ! -f $$HTPASSWD_BIN ]; then
                echo "ERROR: no value for HTPASSWD_BIN found"
                exit -1
            fi
            echo "HTPASSWD_BIN=$$HTPASSWD_BIN"
            ln -sf "$$HTPASSWD_BIN" bin/htpasswd

            mkdir -p lib/omd/hooks
            install -m 755 $$ROOT_DIR/$(location //omd/packages/apache-omd:APACHE_TCP_ADDR) lib/omd/hooks/
            install -m 755 $$ROOT_DIR/$(location //omd/packages/apache-omd:APACHE_TCP_PORT) lib/omd/hooks/

            # Create working directories
            mkdir -p skel/var/log/apache
            mkdir -p skel/var/www
            mkdir -p skel/tmp/apache/run
            mkdir -p skel/tmp/php/session
            mkdir -p skel/tmp/php/upload
            mkdir -p skel/tmp/php/wsdl-cache

            # Install symlinks to apache modules for this platform
            # Some of the modules are optional on some platforms. Link only
            # the available ones.
            mkdir -p lib/apache/modules
            if [ "$$(uname -m)" = "x86_64" ]; then
                APACHE_OMD_MODULE_DIR_VAR=APACHE_MODULE_DIR_64
            else
                APACHE_OMD_MODULE_DIR_VAR=APACHE_MODULE_DIR
            fi
            # hacky way to retrieve APACHE_MODULE_DIR_64 or APACHE_MODULE_DIR
            APACHE_OMD_MODULE_DIR="$$(grep "$$APACHE_OMD_MODULE_DIR_VAR " /opt/*.mk | awk '{print $$3}')"
            if [ ! -d $$APACHE_OMD_MODULE_DIR ]; then
                echo "ERROR: APACHE_OMD_MODULE_DIR=$$APACHE_OMD_MODULE_DIR is not a directory"
                exit -1
            fi
            echo "APACHE_OMD_MODULE_DIR=$$APACHE_OMD_MODULE_DIR"
            # we want symlinks to each of the following modules if available:
            APACHE_MODULES="\
                mod_access_compat.so \
                mod_alias.so \
                mod_auth_basic.so \
                mod_authn_core.so \
                mod_authn_file.so \
                mod_authz_core.so \
                mod_authz_host.so \
                mod_authz_user.so \
                mod_autoindex.so \
                mod_cgi.so \
                mod_deflate.so \
                mod_dir.so \
                mod_env.so \
                mod_expires.so \
                mod_filter.so \
                mod_headers.so \
                mod_log_config.so \
                mod_mime.so \
                mod_mime_magic.so \
                mod_mpm_prefork.so \
                mod_negotiation.so \
                mod_rewrite.so \
                mod_setenvif.so \
                mod_status.so \
                mod_unixd.so \
                mod_proxy.so \
                mod_proxy_http.so"
            for MODULE_FILE in $$APACHE_MODULES; do
                if [ -e "$$APACHE_OMD_MODULE_DIR/$$MODULE_FILE" ]; then
                    echo "+++ create symlink lib/apache/modules/$$MODULE_FILE"
                    ln -sf "$$APACHE_OMD_MODULE_DIR/$$MODULE_FILE" "lib/apache/modules/$$MODULE_FILE"
                fi
            done
        )
        tar -czf $@ apache-omd
    """,
    visibility = ["//visibility:public"],
)

pkg_files(
    name = "skel_files",
    srcs = glob(
        include = ["skel/**/*"],
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_mklink(
    name = "85-apache-symlink",
    link_name = "skel/etc/rc.d/85-apache",
    target = "../init.d/apache",
)

pkg_tar(
    name = "skel_dir",
    srcs = [
        "85-apache-symlink",
        "skel_files",
    ],
    extension = "tar.gz",
    package_file_name = "apache-skel.tar.gz",
    strip_prefix = ".",
    visibility = ["//visibility:public"],
)
