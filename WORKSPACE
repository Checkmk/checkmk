workspace(name = "omd_packages")

load("//omd/packages/perl-modules:perl-modules_http.bzl", "perl_modules")

perl_modules()

load("//omd/packages/mod_fcgid:mod_fcgid_http.bzl", "mod_fcgid_workspace")

mod_fcgid_workspace()

load("//omd/packages/mod_wsgi:mod_wsgi_http.bzl", "mod_wsgi_workspace")

mod_wsgi_workspace()

load("//omd/packages/rrdtool:rrdtool_http.bzl", "rrdtool_workspace")

rrdtool_workspace()

load("//omd/packages/rrdtool:rrdtool_native.bzl", "rrdtool_native_workspace")

rrdtool_native_workspace()
