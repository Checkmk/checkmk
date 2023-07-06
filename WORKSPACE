workspace(name = "omd_packages")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

http_archive(
    name = "rules_foreign_cc",
    sha256 = "2a4d07cd64b0719b39a7c12218a3e507672b82a97b98c6a89d38565894cf7c51",
    strip_prefix = "rules_foreign_cc-0.9.0",
    url = "https://github.com/bazelbuild/rules_foreign_cc/archive/refs/tags/0.9.0.tar.gz",
)

load("@rules_foreign_cc//foreign_cc:repositories.bzl", "rules_foreign_cc_dependencies")

# This sets up some common toolchains for building targets. For more details, please see
# https://bazelbuild.github.io/rules_foreign_cc/0.9.0/flatten.html#rules_foreign_cc_dependencies
rules_foreign_cc_dependencies()

http_archive(
    name = "rules_pkg",
    sha256 = "8f9ee2dc10c1ae514ee599a8b42ed99fa262b757058f65ad3c384289ff70c4b8",
    urls = [
        "https://mirror.bazel.build/github.com/bazelbuild/rules_pkg/releases/download/0.9.1/rules_pkg-0.9.1.tar.gz",
        "https://github.com/bazelbuild/rules_pkg/releases/download/0.9.1/rules_pkg-0.9.1.tar.gz",
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
    "MONITORING_PLUGINS_SHA256",
    "MONITORING_PLUGINS_VERSION",
    "MSITOOLS_SHA256",
    "MSITOOLS_VERSION",
    "NAGIOS_SHA256",
    "NAGIOS_VERSION",
    "NRPE_SHA256",
    "NRPE_VERSION",
    "OPENSSL_SHA256",
    "OPENSSL_VERSION",
    "PATCH_SHA256",
    "PATCH_VERSION",
    "PYTHON_SHA256",
    "PYTHON_VERSION",
    "REDIS_SHA256",
    "REDIS_VERSION",
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

load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

http_archive(
    name = "Crypt-SSLeay",
    build_file = "//omd/packages/perl-modules:BUILD.Crypt-SSLeay.bazel",
    patch_args = ["-p1"],
    patch_tool = "patch",
    patches = [
        "//omd/packages/perl-modules/patches:Crypt-SSLeay-0.72-do-not-use-SSLv2_client_method-with-new-openssl.dif",
    ],
    strip_prefix = "Crypt-SSLeay-0.72",
    urls = [
        "https://www.cpan.org/modules/by-module/Net/NANIS/Crypt-SSLeay-0.72.tar.gz",
        UPSTREAM_MIRROR_URL + "Crypt-SSLeay-0.72.tar.gz",
    ],
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
    sha256 = "ab59a8a02d0f70de3cf89b12fe1e9216e4b1127bc29c04a036cd06dde72ee8fb",
    version_str = "0.6.26",
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
