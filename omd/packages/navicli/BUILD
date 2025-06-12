load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")

# NOTE: The EMC Navisphere command line tools come with their own dynamic
# libraries, which are quite old and some of them even collide with newer ones
# supplied by the distro, e.g. the OpenSSL libraries. We must take great care
# and should NEVER EVER put these ancient libraries into the search path of the
# dynamic linker, the only exception being when calling naviseccli itself. As a
# consequence, we install the libraries to a subdirectory which is not searched
# and call the command via a wrapper which sets LD_LIBRARY_PATH.

pkg_files(
    name = "bin_pkg",
    srcs = [
        "navicli-0.7.1/bin/admsnap",
        "navicli-0.7.1/bin/setlevel_cli.sh",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

pkg_files(
    name = "lib_pkg",
    srcs = [
        "navicli-0.7.1/lib/seccli/libCSP.so",
        "navicli-0.7.1/lib/seccli/libCSP-CertService.so",
        "navicli-0.7.1/lib/seccli/libCSP-Configuration.so",
        "navicli-0.7.1/lib/seccli/libCSP-RT.so",
        "navicli-0.7.1/lib/seccli/libCSP-SM.so",
        "navicli-0.7.1/lib/seccli/libCSP-Security.so",
        "navicli-0.7.1/lib/seccli/libCSP-lb.so",
        "navicli-0.7.1/lib/seccli/libCSPI.so",
        "navicli-0.7.1/lib/seccli/libCST-Admin.so",
        "navicli-0.7.1/lib/seccli/libNonFipsUtilities.so",
        "navicli-0.7.1/lib/seccli/libccme_base.so",
        "navicli-0.7.1/lib/seccli/libcrypto.so.1.0.0",
        "navicli-0.7.1/lib/seccli/libcryptocme2.so",
        "navicli-0.7.1/lib/seccli/libexpat.so",
        "navicli-0.7.1/lib/seccli/libosysrt.so",
        "navicli-0.7.1/lib/seccli/libosysrtxml.so",
        "navicli-0.7.1/lib/seccli/libssl.so.1.0.0",
    ],
    prefix = "lib/seccli",
)

pkg_files(
    name = "lib_755_pkg",
    srcs = [
        "navicli-0.7.1/bin/naviseccli",
        "navicli-0.7.1/lib/seccli/libcryptocme2.sig",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/seccli",
)

pkg_files(
    name = "cst_pkg",
    srcs = [
        "navicli-0.7.1/seccli/CST/CSP.xml",
        "navicli-0.7.1/seccli/CST/CSP-Admin.xml",
        "navicli-0.7.1/seccli/CST/CSP-Authn.xml",
        "navicli-0.7.1/seccli/CST/CSP-CatalogPosix.xml",
        "navicli-0.7.1/seccli/CST/CSP-CatalogService.xml",
        "navicli-0.7.1/seccli/CST/CSP-CatalogWindows.xml",
        "navicli-0.7.1/seccli/CST/CSP-CertificateManagement.xml",
        "navicli-0.7.1/seccli/CST/CSP-Config.xml",
        "navicli-0.7.1/seccli/CST/CSP-DestinationAlert.xml",
        "navicli-0.7.1/seccli/CST/CSP-DestinationEventLog.xml",
        "navicli-0.7.1/seccli/CST/CSP-DestinationFile.xml",
        "navicli-0.7.1/seccli/CST/CSP-DestinationODBC.xml",
        "navicli-0.7.1/seccli/CST/CSP-DestinationSyslog.xml",
        "navicli-0.7.1/seccli/CST/CSP-LDAP.xml",
        "navicli-0.7.1/seccli/CST/CSP-LayoutFlat.xml",
        "navicli-0.7.1/seccli/CST/CSP-LayoutRaw.xml",
        "navicli-0.7.1/seccli/CST/CSP-LayoutXML.xml",
        "navicli-0.7.1/seccli/CST/CSP-LocalDirectory.xml",
        "navicli-0.7.1/seccli/CST/CSP-LocalizationService.xml",
        "navicli-0.7.1/seccli/CST/CSP-Logging.xml",
        "navicli-0.7.1/seccli/CST/CSP-OSLogin.xml",
        "navicli-0.7.1/seccli/CST/CSP-PAM.xml",
        "navicli-0.7.1/seccli/CST/CSP-PositionalFormatter.xml",
        "navicli-0.7.1/seccli/CST/CSP-RoleManagement.xml",
        "navicli-0.7.1/seccli/CST/CSP-SM.xml",
        "navicli-0.7.1/seccli/CST/CSP-SecurID.xml",
        "navicli-0.7.1/seccli/CST/CSP-SprintfFormatter.xml",
        "navicli-0.7.1/seccli/CST/CSP-TrustedUser.xml",
        "navicli-0.7.1/seccli/CST/CSP-UserManagement.xml",
        "navicli-0.7.1/seccli/CST/CSP-saml-schema-assertion-1.1.xsd",
        "navicli-0.7.1/seccli/CST/CSP-saml-schema-assertion-2.0.xsd",
        "navicli-0.7.1/seccli/CST/CSP-xenc-schema.xsd",
        "navicli-0.7.1/seccli/CST/Config.xml",
        "navicli-0.7.1/seccli/CST/Config-Template.xml",
        "navicli-0.7.1/seccli/CST/csp-app.xml",
        "navicli-0.7.1/seccli/CST/xmldsig-core-schema.xsd",
    ],
    prefix = "share/navicli/CST",
)

file_from_flag(
    name = "naviseccli",
    out = "bin/naviseccli",
    content = [
        "#! /bin/sh",
        "LD_LIBRARY_PATH=\"$LD_LIBRARY_PATH:/omd/versions/{cmk_version}.{cmk_edition}/lib/seccli\" exec /omd/versions/{cmk_version}.{cmk_edition}/lib/seccli/naviseccli \"$@\"",
        "",
    ],
    replace_labels = {
        "cmk_version": "//bazel/cmk/version",
        "cmk_edition": "//bazel/cmk/edition",
    },
)

pkg_files(
    name = "naviseccli_pkg",
    srcs = ["naviseccli"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

pkg_tar(
    name = "navicli",
    srcs = [
        "bin_pkg",
        "cst_pkg",
        "lib_755_pkg",
        "lib_pkg",
        "naviseccli_pkg",
    ],
    visibility = ["//omd:__pkg__"],
)
