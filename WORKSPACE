workspace(name = "omd_packages")

load("@bazel_tools//tools/build_defs/repo:git.bzl", "git_repository")
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")
load("//omd/packages/toolchain:fork_cc_toolchain_config.bzl", "fork_cc_toolchain_config")

fork_cc_toolchain_config(
    name = "forked_cc_toolchain_config",
)

register_toolchains("//omd/packages/toolchain:linux_gcc13")

RULES_FOREIGN_CC_VERSION = "0.9.0"

http_archive(
    name = "rules_foreign_cc",
    patch_args = ["-p1"],
    patches = ["//omd/packages/foreign_cc:symlink.patch"],
    sha256 = "2a4d07cd64b0719b39a7c12218a3e507672b82a97b98c6a89d38565894cf7c51",
    strip_prefix = "rules_foreign_cc-" + RULES_FOREIGN_CC_VERSION,
    urls = [
        "https://github.com/bazelbuild/rules_foreign_cc/archive/refs/tags/" + RULES_FOREIGN_CC_VERSION + ".tar.gz",
        UPSTREAM_MIRROR_URL + "rules_foreign_cc-" + RULES_FOREIGN_CC_VERSION + ".tar.gz",
    ],
)

load("@rules_foreign_cc//foreign_cc:repositories.bzl", "rules_foreign_cc_dependencies")

rules_foreign_cc_dependencies()

RULES_PKG_VERSION = "0.9.1"

http_archive(
    name = "rules_pkg",
    sha256 = "8f9ee2dc10c1ae514ee599a8b42ed99fa262b757058f65ad3c384289ff70c4b8",
    urls = [
        "https://mirror.bazel.build/github.com/bazelbuild/rules_pkg/releases/download/" + RULES_PKG_VERSION + "/rules_pkg-" + RULES_PKG_VERSION + ".tar.gz",
        "https://github.com/bazelbuild/rules_pkg/releases/download/" + RULES_PKG_VERSION + "/rules_pkg-" + RULES_PKG_VERSION + ".tar.gz",
        UPSTREAM_MIRROR_URL + "rules_pkg-" + RULES_PKG_VERSION + ".tar.gz",
    ],
)

RULES_RUST_VERSION = "0.36.2"

http_archive(
    name = "rules_rust",
    sha256 = "a761d54e49db06f863468e6bba4a13252b1bd499e8f706da65e279b3bcbc5c52",
    urls = [
        "https://mirror.bazel.build/github.com/bazelbuild/rules_rust/releases/download/" + RULES_RUST_VERSION + "/rules_rust-v" + RULES_RUST_VERSION + ".tar.gz",
        "https://github.com/bazelbuild/rules_rust/releases/download/" + RULES_RUST_VERSION + "/rules_rust-v" + RULES_RUST_VERSION + ".tar.gz",
        UPSTREAM_MIRROR_URL + "rules_rust-v" + RULES_RUST_VERSION + ".tar.gz",
    ],
)

load("//omd/packages/rules:cargo_deps.bzl", "cargo_deps")
load("//omd/packages/rules:rust_workspace.bzl", "rust_workspace")

rust_workspace()

load("@rules_pkg//:deps.bzl", "rules_pkg_dependencies")

rules_pkg_dependencies()

#   .--PACKAGES------------------------------------------------------------.
#   |           ____   _    ____ _  __    _    ____ _____ ____             |
#   |          |  _ \ / \  / ___| |/ /   / \  / ___| ____/ ___|            |
#   |          | |_) / _ \| |   | ' /   / _ \| |  _|  _| \___ \            |
#   |          |  __/ ___ \ |___| . \  / ___ \ |_| | |___ ___) |           |
#   |          |_| /_/   \_\____|_|\_\/_/   \_\____|_____|____/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'
load(
    "//:package_versions.bzl",
    "CRYPT_SSL_SHA256",
    "CRYPT_SSL_VERSION",
    "FREETDS_SHA256",
    "FREETDS_VERSION",
    "HEIRLOOMMAILX_SHA256",
    "HEIRLOOMMAILX_VERSION",
    "HEIRLOOM_PKGTOOLS_SHA256",
    "HEIRLOOM_PKGTOOLS_VERSION",
    "JAEGER_SHA256",
    "JAEGER_VERSION",
    "LCAB_SHA256",
    "LCAB_VERSION",
    "LIBGSF_SHA256",
    "LIBGSF_VERSION",
    "MOD_FCGID_SHA256",
    "MOD_FCGID_VERSION",
    "MOD_WSGI_SHA256",
    "MOD_WSGI_VERSION",
    "MONITORING_PLUGINS_SHA256",
    "MONITORING_PLUGINS_VERSION",
    "MSITOOLS_SHA256",
    "MSITOOLS_VERSION",
    "NAGIOS_SHA256",
    "NAGIOS_VERSION",
    "NET_SNMP_SHA256",
    "NET_SNMP_VERSION",
    "NRPE_SHA256",
    "NRPE_VERSION",
    "OPENSSL_SHA256",
    "OPENSSL_VERSION",
    "PATCH_SHA256",
    "PATCH_VERSION",
    "PNP4NAGIOS_SHA256",
    "PNP4NAGIOS_VERSION",
    "PYTHON_SHA256",
    "PYTHON_VERSION",
    "REDFISH_MKP_COMMIT_HASH",
    "REDFISH_MKP_SHA256",
    "REDFISH_MKP_VERSION",
    "REDIS_SHA256",
    "REDIS_VERSION",
    "ROBOTMK_SHA256",
    "ROBOTMK_VERSION",
    "RRDTOOL_SHA256",
    "RRDTOOL_VERSION",
    "SNAP7_SHA256",
    "SNAP7_VERSION",
    "STUNNEL_SHA256",
    "STUNNEL_VERSION",
    "XINETD_SHA256",
    "XINETD_VERSION",
    "XMLSEC1_SHA256",
    "XMLSEC1_VERSION",
)

cargo_deps(
    name = "check-cert-deps",
    package = "packages/check-cert",
)

load("@check-cert-deps//:defs.bzl", check_cert_deps = "crate_repositories")

check_cert_deps()

cargo_deps(
    name = "check-http-deps",
    package = "packages/check-http",
)

load("@check-http-deps//:defs.bzl", check_http_deps = "crate_repositories")

check_http_deps()

load("//omd/packages/patch:patch_http.bzl", "patch")

patch(
    sha256 = PATCH_SHA256,
    version_str = PATCH_VERSION,
)

load("//omd/packages/redis:redis_http.bzl", "redis")

redis(
    sha256 = REDIS_SHA256,
    version_str = REDIS_VERSION,
)

load("//omd/packages/asio:asio.bzl", "asio")

asio(
    sha256 = "09b9fe5c670c7bd47c7ee957cd9c184b4c8f0620d5b08b38ce837a24df971bca",
    version = "1.24.0-patched",
)

load("//omd/packages/re2:re2.bzl", "re2")

re2(
    sha256 = "665b65b6668156db2b46dddd33405cd422bd611352c5052ab3dae6a5fbac5506",
    version = "2022-12-01",
)

load("//omd/packages/openssl:openssl_http.bzl", "openssl")

openssl(
    sha256 = OPENSSL_SHA256,
    version_str = OPENSSL_VERSION,
)

load("//omd/packages/xmlsec1:xmlsec1_http.bzl", "xmlsec1")

xmlsec1(
    sha256 = XMLSEC1_SHA256,
    version_str = XMLSEC1_VERSION,
)

load("//omd/packages/heirloom-mailx:heirloom-mailx_http.bzl", "heirloommailx")

heirloommailx(
    sha256 = HEIRLOOMMAILX_SHA256,
    version_str = HEIRLOOMMAILX_VERSION,
)

load("//omd/packages/monitoring-plugins:monitoring-plugins_http.bzl", "monitoring_plugins")

monitoring_plugins(
    sha256 = MONITORING_PLUGINS_SHA256,
    version_str = MONITORING_PLUGINS_VERSION,
)

load("//omd/packages/stunnel:stunnel_http.bzl", "stunnel")

stunnel(
    sha256 = STUNNEL_SHA256,
    version_str = STUNNEL_VERSION,
)

load("//omd/packages/freetds:freetds_http.bzl", "freetds")

freetds(
    sha256 = FREETDS_SHA256,
    version_str = FREETDS_VERSION,
)

load("//omd/packages/heirloom-pkgtools:heirloom-pkgtools_http.bzl", "heirloom_pkgtools")

heirloom_pkgtools(
    sha256 = HEIRLOOM_PKGTOOLS_SHA256,
    version_str = HEIRLOOM_PKGTOOLS_VERSION,
)

load("//omd/packages/libgsf:libgsf_http.bzl", "libgsf")

libgsf(
    sha256 = LIBGSF_SHA256,
    version_str = LIBGSF_VERSION,
)

load("//omd/packages/lcab:lcab_http.bzl", "lcab")

lcab(
    sha256 = LCAB_SHA256,
    version_str = LCAB_VERSION,
)

load("//omd/packages/msitools:msitools_http.bzl", "msitools")

msitools(
    sha256 = MSITOOLS_SHA256,
    version_str = MSITOOLS_VERSION,
)

load("//omd/packages/snap7:snap7_http.bzl", "snap7")

snap7(
    sha256 = SNAP7_SHA256,
    version_str = SNAP7_VERSION,
)

load("//omd/packages/perl-modules:perl-modules_http.bzl", "perl_modules")

# TODO: Centralize perl modules versions
perl_modules()

load("//omd/packages/crypt-ssleay:cryptssl_http.bzl", "crypt_ssleay")

crypt_ssleay(
    sha256 = CRYPT_SSL_SHA256,
    version_str = CRYPT_SSL_VERSION,
)

load("//omd/packages/nrpe:nrpe_http.bzl", "nrpe")

nrpe(
    sha256 = NRPE_SHA256,
    version_str = NRPE_VERSION,
)

load("//omd/packages/Python:Python_http.bzl", "python")

python(
    sha256 = PYTHON_SHA256,
    version_str = PYTHON_VERSION,
)

load("//omd/packages/pnp4nagios:pnp4nagios_http.bzl", "pnp4nagios")

pnp4nagios(
    sha256 = PNP4NAGIOS_SHA256,
    version_str = PNP4NAGIOS_VERSION,
)

load("//omd/packages/mod_fcgid:mod_fcgid_http.bzl", "mod_fcgid")

mod_fcgid(
    sha256 = MOD_FCGID_SHA256,
    version_str = MOD_FCGID_VERSION,
)

load("//omd/packages/xinetd:xinetd_http.bzl", "xinetd")

xinetd(
    sha256 = XINETD_SHA256,
    version_str = XINETD_VERSION,
)

load("//omd/packages/nagios:nagios_http.bzl", "nagios")

nagios(
    sha256 = NAGIOS_SHA256,
    version_str = NAGIOS_VERSION,
)

load("//omd/packages/python3-modules:create_python_requirements.bzl", "create_python_requirements")

create_python_requirements(
    name = "python_modules",
    # TODO: differentiate between own code and things we get from other omd packages
    ignored_modules = [
        "protobuf",  # don't build with pip -> see protobuf omd packages
        "rrdtool",  # don't build with pip -> see rrdtool omd packages
        "agent-receiver",  # don't build with pip (yet)
        "werks",  # don't build with pip (yet)
        "netapp-ontap",  # their build process is broken, see https://github.com/NetApp/ontap-rest-python/issues/46
    ],
    requirements = "//:Pipfile",
)

load("//omd/packages/mod_wsgi:mod_wsgi_http.bzl", "mod_wsgi")

mod_wsgi(
    sha256 = MOD_WSGI_SHA256,
    version_str = MOD_WSGI_VERSION,
)

load("//omd/packages/net-snmp:net-snmp_http.bzl", "netsnmp")

netsnmp(
    sha256 = NET_SNMP_SHA256,
    version_str = NET_SNMP_VERSION,
)

load("//omd/packages/robotmk:robotmk_http.bzl", "robotmk")

robotmk(
    sha256 = ROBOTMK_SHA256,
    version_str = ROBOTMK_VERSION,
)

load("//omd/packages/rrdtool:rrdtool_http.bzl", "rrdtool")

rrdtool(
    sha256 = RRDTOOL_SHA256,
    version_str = RRDTOOL_VERSION,
)

load("//omd/packages/rrdtool:rrdtool_native.bzl", "rrdtool_native")

rrdtool_native(
    sha256 = RRDTOOL_SHA256,
    version_str = RRDTOOL_VERSION,
)

load("//omd/packages/glib:glib.bzl", "glibconfig")

glibconfig("glibconfig-default", "/usr/lib/x86_64-linux-gnu/glib-2.0")

glibconfig("glibconfig-centos", "/usr/lib64/glib-2.0")

load("//omd/packages/httplib:httplib.bzl", "httplib")

httplib(
    sha256 = "2a4503f9f2015f6878baef54cd94b01849cc3ed19dfe95f2c9775655bea8b73f",
    version = "0.13.3",
)

load("//omd/packages/googletest:gtest_http.bzl", "googletest")

googletest(
    # Googletest doesn't provide releases anymore, it uses a "Abseil Live at Head philosophy" nowadays.
    commit = "71140c3ca7a87bb1b5b9c9f1500fea8858cce344",
)

http_archive(
    name = "rules_cc",
    sha256 = "35f2fb4ea0b3e61ad64a369de284e4fbbdcdba71836a5555abb5e194cf119509",
    strip_prefix = "rules_cc-624b5d59dfb45672d4239422fa1e3de1822ee110",
    urls = [
        "https://mirror.bazel.build/github.com/bazelbuild/rules_cc/archive/624b5d59dfb45672d4239422fa1e3de1822ee110.tar.gz",
        "https://github.com/bazelbuild/rules_cc/archive/624b5d59dfb45672d4239422fa1e3de1822ee110.tar.gz",
    ],
)

load("@rules_cc//cc:repositories.bzl", "rules_cc_dependencies")

rules_cc_dependencies()

http_archive(
    name = "rules_proto",
    sha256 = "6fb6767d1bef535310547e03247f7518b03487740c11b6c6adb7952033fe1295",
    strip_prefix = "rules_proto-6.0.2",
    url = "https://github.com/bazelbuild/rules_proto/releases/download/6.0.2/rules_proto-6.0.2.tar.gz",
)

load("@rules_proto//proto:repositories.bzl", "rules_proto_dependencies")

rules_proto_dependencies()

load("@rules_proto//proto:setup.bzl", "rules_proto_setup")

rules_proto_setup()

load("@rules_proto//proto:toolchains.bzl", "rules_proto_toolchains")

rules_proto_toolchains()

git_repository(
    name = "com_google_protobuf",
    commit = "3d9f7c430a5ae1385512908801492d4421c3cdb7",  # v27.1
    remote = "https://github.com/protocolbuffers/protobuf.git",
)

load("@com_google_protobuf//:protobuf_deps.bzl", "protobuf_deps")

protobuf_deps()

load("//omd/packages/redfish_mkp:redfish_mkp_http.bzl", "redfish_mkp")

redfish_mkp(
    commit_hash = REDFISH_MKP_COMMIT_HASH,
    sha256 = REDFISH_MKP_SHA256,
    version_str = REDFISH_MKP_VERSION,
)

load("//omd/packages/jaeger:jaeger_http.bzl", "jaeger")

jaeger(
    sha256 = JAEGER_SHA256,
    version_str = JAEGER_VERSION,
)
