workspace(name = "omd_packages")

load("//:bazel_variables.bzl", "RUFF_VERSION")
load("//omd/packages/asio:asio_http.bzl", "asio_workspace")

asio_workspace()

load("//omd/packages/re2:re2_http.bzl", "re2_workspace")

re2_workspace()

load("//omd/packages/msitools:msitools_http.bzl", "msitools_workspace")

msitools_workspace()

load("//omd/packages/perl-modules:perl-modules_http.bzl", "perl_modules")

perl_modules()

load("//omd/packages/crypt-ssleay:cryptssl_http.bzl", "crypt_ssleay_workspace")

crypt_ssleay_workspace()

load("//omd/packages/pnp4nagios:pnp4nagios_http.bzl", "pnp4nagios_workspace")

pnp4nagios_workspace()

load("//omd/packages/mod_fcgid:mod_fcgid_http.bzl", "mod_fcgid_workspace")

mod_fcgid_workspace()

load("//omd/packages/nagios:nagios_http.bzl", "nagios_workspace")

nagios_workspace()

load("//omd/packages/mod_wsgi:mod_wsgi_http.bzl", "mod_wsgi_workspace")

mod_wsgi_workspace()

load("//omd/packages/rrdtool:rrdtool_http.bzl", "rrdtool_workspace")

rrdtool_workspace()

load("//omd/packages/rrdtool:rrdtool_native.bzl", "rrdtool_native_workspace")

rrdtool_native_workspace()

load("@aspect_rules_lint//lint:ruff.bzl", "fetch_ruff")

fetch_ruff(RUFF_VERSION)
