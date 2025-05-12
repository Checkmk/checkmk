load("@omd_packages//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")
load("@python_modules//:requirements.bzl", "all_requirements")
load(":build-python3-modules.bzl", "build_cmd", "build_python_module", "create_requirements_file")

config_setting(
    name = "git_ssl_no_verify",
    values = {"define": "git-ssl-no-verify=true"},
)

[create_requirements_file(
    name = module,
    outs = [
        "%s_requirements.txt" % module,
    ],
) for module in all_requirements]

# Third Party packages parsed from Pipfile
[build_python_module(
    name = "%s_compile" % module,
    srcs = [
        "%s_requirements.txt" % module,
        "@freetds",
        "@omd_packages//omd/packages/omd:use_system_openssl",
        "@openssl",
        "@python",
    ],
    outs = [
        "compiled_%s.tar" % module,
    ],
    cmd = select({
        "//conditions:default": build_cmd.format(
            git_ssl_no_verify = "",
            pyMajMin = PYTHON_MAJOR_DOT_MINOR,
            requirements = "-r $$HOME/$(execpath %s_requirements.txt)" % module,
        ),
        ":git_ssl_no_verify": build_cmd.format(
            git_ssl_no_verify = "GIT_SSL_NO_VERIFY=true",
            pyMajMin = PYTHON_MAJOR_DOT_MINOR,
            requirements = "-r $$HOME/$(execpath %s_requirements.txt)" % module,
        ),
    }),
) for module in all_requirements]

# TODO: Switch to official release when netapp has fixed their build process
# See: https://github.com/NetApp/ontap-rest-python/issues/46
MODULE_NETAPP = "netapp-ontap"

MODULE_NETAPP_SOURCE = "git+https://github.com/Checkmk/netapp-ontap-cmk.git@e38ce4ce357ad2ea8f47260c269757f8805bdbce"

build_python_module(
    name = "%s_compile" % MODULE_NETAPP,
    srcs = [
        "@freetds",
        "@omd_packages//omd/packages/omd:use_system_openssl",
        "@openssl",
        "@python",
    ],
    outs = [
        "compiled_%s.tar" % MODULE_NETAPP,
    ],
    cmd = select({
        "//conditions:default": build_cmd.format(
            git_ssl_no_verify = "",
            pyMajMin = PYTHON_MAJOR_DOT_MINOR,
            requirements = MODULE_NETAPP_SOURCE,
        ),
        ":git_ssl_no_verify": build_cmd.format(
            git_ssl_no_verify = "GIT_SSL_NO_VERIFY=true",
            pyMajMin = PYTHON_MAJOR_DOT_MINOR,
            requirements = MODULE_NETAPP_SOURCE,
        ),
    }),
)

# TODO: Switch to official release when pymssql is cython 3.1.0 compatible
# see also https://github.com/pymssql/pymssql/pull/938
MODULE_PYMSSQL = "pymssql"

MODULE_PYMSSQL_SOURCE = "git+https://github.com/TimotheusBachinger/pymssql@2a02c839c59c2b87e2acdfad8bc0187b2b6c4fe9"

build_python_module(
    name = "%s_compile" % MODULE_PYMSSQL,
    srcs = [
        "@freetds",
        "@omd_packages//omd/packages/omd:use_system_openssl",
        "@openssl",
        "@python",
    ],
    outs = [
        "compiled_%s.tar" % MODULE_PYMSSQL,
    ],
    cmd = select({
        "//conditions:default": build_cmd.format(
            git_ssl_no_verify = "",
            pyMajMin = PYTHON_MAJOR_DOT_MINOR,
            requirements = MODULE_PYMSSQL_SOURCE,
        ),
        ":git_ssl_no_verify": build_cmd.format(
            git_ssl_no_verify = "GIT_SSL_NO_VERIFY=true",
            pyMajMin = PYTHON_MAJOR_DOT_MINOR,
            requirements = MODULE_PYMSSQL_SOURCE,
        ),
    }),
)

genrule(
    name = "python3-modules",
    srcs = [
        "%s_compile" % module
        for module in all_requirements + [
            "netapp-ontap",
            "pymssql",
        ]
    ],
    outs = [
        "python3-modules.tar",
    ],
    cmd = """
        mkdir -p python3-modules
        for MODULE in $(SRCS); do
            tar --strip-components 1 -xf $$MODULE -C python3-modules/
        done

        # For some highly obscure unknown reason some files end up world-writable. Fix that!
        chmod -R o-w python3-modules/lib/python{pyMajMin}/site-packages

        # Cleanup some unwanted files (example scripts)
        find python3-modules/bin -name "*.py" ! -name snmpsimd.py -exec rm -f {{}} \\;

        # These files break the integration tests on the CI server. Don't know exactly
        # why this happens only there, but should be a working fix.
        rm -r -f python3-modules/snmpsim

        # Cleanup unneeded test files of numpy
        rm -r -f python3-modules/lib/python{pyMajMin}/site-packages/numpy/*/tests

        # Fix python interpreter for kept scripts
        sed -E -i '1s|^#!.*/python3?$$|#!/usr/bin/env python3|' python3-modules/bin/[!_]*

        # pip is using pip._vendor.distlib.scripts.ScriptMaker._build_shebang() to
        # build the shebang of the scripts installed to bin. When executed via our CI
        # containers, the shebang exceeds the max_shebang_length of 127 bytes. For this
        # case, it adds a #!/bin/sh wrapper in front of the python code o_O to make it
        # fit into the shebang. Let's also cleanup this case.
        sed -i -z "s|^#\\!/bin/sh\\n.*exec.*python3[^\\n]*\\n[^\\n]*|#\\!/usr/bin/env python3|" python3-modules/bin/[!_]*

        # Fix rpath for all .so libs
        cd python3-modules/lib/
        for F in $$(find -name "*.so");
            do patchelf --set-rpath \\
            $$(echo $$F | sed 's|[^/]*/|../|g' | sed 's|\\.\\./|\\$$ORIGIN/|' | sed 's|[^/]*$$||') $$F ;
        done
        cd -
	tar cf $@ -C python3-modules .
    """.format(pyMajMin = PYTHON_MAJOR_DOT_MINOR),
    visibility = ["//visibility:public"],
)
