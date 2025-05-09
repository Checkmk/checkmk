workspace(name = "omd_packages")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

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
        # Currently broken due to new cython version, see https://github.com/pymssql/pymssql/issues/937
        "pymssql",
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

load("//omd/packages/redfish_mkp:redfish_mkp_http.bzl", "redfish_mkp")

redfish_mkp(
    commit_hash = REDFISH_MKP_COMMIT_HASH,
    sha256 = REDFISH_MKP_SHA256,
    version_str = REDFISH_MKP_VERSION,
)
