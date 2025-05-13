workspace(name = "omd_packages")

load("//:bazel_variables.bzl", "RUFF_VERSION")
load("//omd/packages/asio:asio_http.bzl", "asio_workspace")

asio_workspace()

load("//omd/packages/re2:re2_http.bzl", "re2_workspace")

re2_workspace()

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
        # Currently broken due to new cython version, see https://github.com/pymssql/pymssql/issues/937
        "pymssql",
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

load("//omd/packages/rabbitmq:rabbitmq_http.bzl", "rabbitmq_workspace")

rabbitmq_workspace()

load("@aspect_rules_lint//lint:ruff.bzl", "fetch_ruff")

fetch_ruff(RUFF_VERSION)
