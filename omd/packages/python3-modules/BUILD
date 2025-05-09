load(":build-python3-modules.bzl", "build_cmd", "build_python_module", "create_requirements_file", "get_pip_options")
load("@python_modules//:requirements.bzl", "all_requirements")
load("@omd_packages//:package_versions.bzl", "PYTHON_MAJOR_DOT_MINOR")
load("@omd_packages//:static_variables.bzl", "INTERNAL_PYPI_MIRROR")

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
            pip_add_opts = get_pip_options(module),
            pyMajMin = PYTHON_MAJOR_DOT_MINOR,
            pypi_mirror = INTERNAL_PYPI_MIRROR,
            requirements = "-r $$HOME/$(execpath %s_requirements.txt)" % module,
        ),
        ":git_ssl_no_verify": build_cmd.format(
            git_ssl_no_verify = "GIT_SSL_NO_VERIFY=true",
            pip_add_opts = get_pip_options(module),
            pyMajMin = PYTHON_MAJOR_DOT_MINOR,
            pypi_mirror = INTERNAL_PYPI_MIRROR,
            requirements = "-r $$HOME/$(execpath %s_requirements.txt)" % module,
        ),
    }),
) for module in all_requirements]

[build_python_module(
    name = "%s_compile" % module,
    srcs = [
        "@freetds",
        "@omd_packages//omd/packages/omd:use_system_openssl",
        "@omd_packages//packages:cmk-agent-based",
        "@omd_packages//packages:cmk-agent-receiver",
        "@omd_packages//packages:cmk-graphing",
        "@omd_packages//packages:cmk-livestatus-client",
        "@omd_packages//packages:cmk-mkp-tool",
        "@omd_packages//packages:cmk-rulesets",
        "@omd_packages//packages:cmk-server-side-calls",
        "@omd_packages//packages:cmk-werks",
        "@openssl",
        "@python",
    ],
    outs = [
        "compiled_%s.tar" % module,
    ],
    cmd = select({
        "//conditions:default": build_cmd.format(
            git_ssl_no_verify = "",
            pip_add_opts = get_pip_options(module),
            pyMajMin = PYTHON_MAJOR_DOT_MINOR,
            pypi_mirror = INTERNAL_PYPI_MIRROR,
            requirements = dep,
        ),
        ":git_ssl_no_verify": build_cmd.format(
            git_ssl_no_verify = "GIT_SSL_NO_VERIFY=true",
            pip_add_opts = get_pip_options(module),
            pyMajMin = PYTHON_MAJOR_DOT_MINOR,
            pypi_mirror = INTERNAL_PYPI_MIRROR,
            requirements = dep,
        ),
    }),
) for module, dep in [
    ("agent-receiver", "$(execpath @omd_packages//packages:cmk-agent-receiver)"),
    ("graphing", "$(execpath @omd_packages//packages:cmk-graphing)"),
    ("rulesets", "$(execpath @omd_packages//packages:cmk-rulesets)"),
    ("server-side-calls", "$(execpath @omd_packages//packages:cmk-server-side-calls)"),
    ("werks", "$(execpath @omd_packages//packages:cmk-werks)"),
    ("agent-based", "$(execpath @omd_packages//packages:cmk-agent-based)"),
    ("mkp-tool", "$(execpath @omd_packages//packages:cmk-mkp-tool)"),
    ("livestatus-client", "$(execpath @omd_packages//packages:cmk-livestatus-client)"),
    # TODO: Switch to official release when netapp has fixed their build process
    # See: https://github.com/NetApp/ontap-rest-python/issues/46
    ("netapp-ontap", "git+https://github.com/Checkmk/netapp-ontap-cmk.git@e38ce4ce357ad2ea8f47260c269757f8805bdbce"),
]]

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
            module_name = MODULE_PYMSSQL,
            pip_add_opts = get_pip_options(MODULE_PYMSSQL),
            pyMajMin = PYTHON_MAJOR_DOT_MINOR,
            requirements = MODULE_PYMSSQL_SOURCE,
        ),
        ":git_ssl_no_verify": build_cmd.format(
            git_ssl_no_verify = "GIT_SSL_NO_VERIFY=true",
            module_name = MODULE_PYMSSQL,
            pip_add_opts = get_pip_options(MODULE_PYMSSQL),
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
            "agent-based",
            "agent-receiver",
            "graphing",
            "mkp-tool",
            "rulesets",
            "server-side-calls",
            "werks",
            "livestatus-client",
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
	tar cf $@ python3-modules
    """.format(pyMajMin = PYTHON_MAJOR_DOT_MINOR),
    visibility = ["//visibility:public"],
)
