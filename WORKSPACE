workspace(name = "omd_packages")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("@rules_rust//crate_universe:defs.bzl", "crate", "crates_repository")
load("//:bazel_variables.bzl", "RUFF_VERSION")
load("//bazel/rules:rust_workspace.bzl", "rust_workspace")

rust_workspace()

#   .--PACKAGES------------------------------------------------------------.
#   |           ____   _    ____ _  __    _    ____ _____ ____             |
#   |          |  _ \ / \  / ___| |/ /   / \  / ___| ____/ ___|            |
#   |          | |_) / _ \| |   | ' /   / _ \| |  _|  _| \___ \            |
#   |          |  __/ ___ \ |___| . \  / ___ \ |_| | |___ ___) |           |
#   |          |_| /_/   \_\____|_|\_\/_/   \_\____|_____|____/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# Repin with `CARGO_BAZEL_REPIN=1 bazel sync --only=cargo_deps_site`.
crates_repository(
    # Repository for rust binaries or libraries deployed in the site.
    name = "cargo_deps_site",
    annotations = {
        "openssl-sys": [
            crate.annotation(
                build_script_data = [
                    "@openssl//:gen_dir",
                ],
                build_script_env = {
                    "OPENSSL_DIR": "$(execpath @openssl//:gen_dir)",
                    "OPENSSL_NO_VENDOR": "1",
                },
                deps = [
                    "@openssl//:openssl_shared",
                ],
            ),
        ],
    },
    cargo_lockfile = "//packages/site:Cargo.lock",
    lockfile = "//packages/site:Cargo.lock.bazel",
    manifests = [
        "//packages/site:Cargo.toml",
        "//packages/site/check-cert:Cargo.toml",
        "//packages/site/check-http:Cargo.toml",
    ],
)

load("@cargo_deps_site//:defs.bzl", site_crate_repository = "crate_repositories")

site_crate_repository()

# Repin with `CARGO_BAZEL_REPIN=1 bazel sync --only=cargo_deps_host`.
crates_repository(
    # Repository for rust binaries deployed on the host.
    name = "cargo_deps_host",
    annotations = {
        "openssl-sys": [
            crate.annotation(
                build_script_data = [
                    "@openssl//:gen_dir",
                ],
                build_script_env = {
                    "OPENSSL_DIR": "$(execpath @openssl//:gen_dir)",
                    "OPENSSL_NO_VENDOR": "1",
                    "OPENSSL_STATIC": "1",
                },
                data = ["@openssl//:gen_dir"],
                deps = [
                    "@openssl",
                ],
            ),
        ],
    },
    cargo_lockfile = "//packages/host:Cargo.lock",
    lockfile = "//packages/host:Cargo.lock.bazel",
    manifests = [
        "//packages/host:Cargo.toml",
        "//packages/host/cmk-agent-ctl:Cargo.toml",
        "//packages/host/mk-sql:Cargo.toml",
    ],
)

load("@cargo_deps_host//:defs.bzl", host_crate_repository = "crate_repositories")

host_crate_repository()

load("//omd/packages/redis:redis_http.bzl", "redis_workspace")

redis_workspace()

load("//omd/packages/asio:asio_http.bzl", "asio_workspace")

asio_workspace()

load("//omd/packages/re2:re2_http.bzl", "re2_workspace")

re2_workspace()

load("//omd/packages/openssl:openssl_http.bzl", "openssl_workspace")

openssl_workspace()

load("//omd/packages/xmlsec1:xmlsec1_http.bzl", "xmlsec_workspace")

xmlsec_workspace()

load("//omd/packages/heirloom-mailx:heirloom-mailx_http.bzl", "heirloommailx_workspace")

heirloommailx_workspace()

load("//omd/packages/monitoring-plugins:monitoring-plugins_http.bzl", "monitoring_plugins_workspace")

monitoring_plugins_workspace()

load("//omd/packages/stunnel:stunnel_http.bzl", "stunnel_workspace")

stunnel_workspace()

load("//omd/packages/freetds:freetds_http.bzl", "freetds_workspace")

freetds_workspace()

load("//omd/packages/heirloom-pkgtools:heirloom-pkgtools_http.bzl", "heirloom_pkgtools_workspace")

heirloom_pkgtools_workspace()

load("//omd/packages/libgsf:libgsf_http.bzl", "libgsf_workspace")

libgsf_workspace()

load("//omd/packages/lcab:lcab_http.bzl", "lcab_workspace")

lcab_workspace()

load("//omd/packages/msitools:msitools_http.bzl", "msitools_workspace")

msitools_workspace()

load("//omd/packages/snap7:snap7_http.bzl", "snap7_workspace")

snap7_workspace()

load("//omd/packages/perl-modules:perl-modules_http.bzl", "perl_modules")

perl_modules()

load("//omd/packages/crypt-ssleay:cryptssl_http.bzl", "crypt_ssleay_workspace")

crypt_ssleay_workspace()

load("//omd/packages/nrpe:nrpe_http.bzl", "nrpe_workspace")

nrpe_workspace()

load("//omd/packages/Python:Python_http.bzl", "python_workspace")

python_workspace()

load("//omd/packages/pnp4nagios:pnp4nagios_http.bzl", "pnp4nagios_workspace")

pnp4nagios_workspace()

load("//omd/packages/mod_fcgid:mod_fcgid_http.bzl", "mod_fcgid_workspace")

mod_fcgid_workspace()

load("//omd/packages/xinetd:xinetd_http.bzl", "xinetd_workspace")

xinetd_workspace()

load("//omd/packages/nagios:nagios_http.bzl", "nagios_workspace")

nagios_workspace()

load("//omd/packages/python3-modules:create_python_requirements.bzl", "create_python_requirements")

create_python_requirements(
    name = "python_modules",
    ignored_modules = [
        # Broken third party packages
        "netapp-ontap",  # their build process is broken, see https://github.com/NetApp/ontap-rest-python/issues/46
    ],
    requirements_lock = "//:runtime-requirements.txt",
)

load("//omd/packages/mod_wsgi:mod_wsgi_http.bzl", "mod_wsgi_workspace")

mod_wsgi_workspace()

load("//omd/packages/net-snmp:net-snmp_http.bzl", "netsnmp_workspace")

netsnmp_workspace()

load("//omd/packages/robotmk:robotmk_http.bzl", "robotmk_workspace")

robotmk_workspace()

load("//omd/packages/rrdtool:rrdtool_http.bzl", "rrdtool_workspace")

rrdtool_workspace()

load("//omd/packages/rrdtool:rrdtool_native.bzl", "rrdtool_native_workspace")

rrdtool_native_workspace()

load("//omd/packages/httplib:httplib_http.bzl", "httplib_workspace")

httplib_workspace()

http_archive(
    name = "gtest",
    sha256 = "75bfc7c1fd2eecf8dafeaee71836348941b422e9eee0a10493c68514cad81c8f",
    strip_prefix = "googletest-e90fe2485641bab0d6af4500192dc503384950d1",
    url = "https://github.com/google/googletest/archive/e90fe2485641bab0d6af4500192dc503384950d1.tar.gz",
)

load("//omd/packages/jaeger:jaeger_http.bzl", "jaeger_workspace")

jaeger_workspace()

load("//omd/packages/erlang:erlang_http.bzl", "erlang_workspace")

erlang_workspace()

load("//omd/packages/rabbitmq:rabbitmq_http.bzl", "rabbitmq_workspace")

rabbitmq_workspace()

load("@aspect_rules_lint//lint:ruff.bzl", "fetch_ruff")

fetch_ruff(RUFF_VERSION)
