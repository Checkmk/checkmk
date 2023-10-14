load(":build-python3-modules.bzl", "build_cmd", "build_python_module", "create_requirements_file")
load("@python_modules//:requirements.bzl", "all_requirements")

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
        "compiled_%s" % module,
    ],
    cmd = select({
        "//conditions:default": build_cmd.format(
            git_ssl_no_verify = "",
            requirements = "-r $$HOME/$(execpath %s_requirements.txt);" % module,
        ),
        ":git_ssl_no_verify": build_cmd.format(
            git_ssl_no_verify = "GIT_SSL_NO_VERIFY=true",
            requirements = "-r $$HOME/$(execpath %s_requirements.txt);" % module,
        ),
    }),
) for module in all_requirements]

[build_python_module(
    name = "%s_compile" % module,
    srcs = [
        "@freetds",
        "@omd_packages//:agent-receiver",
        "@omd_packages//omd/packages/omd:use_system_openssl",
        "@omd_packages//packages:werks",
        "@openssl",
        "@python",
    ],
    outs = [
        "compiled_%s" % module,
    ],
    cmd = select({
        "//conditions:default": build_cmd.format(
            git_ssl_no_verify = "",
            requirements = dep,
        ),
        ":git_ssl_no_verify": build_cmd.format(
            git_ssl_no_verify = "GIT_SSL_NO_VERIFY=true",
            requirements = dep,
        ),
    }),
) for module, dep in [
    ("cython3", "git+https://github.com/JonasScharpf/pymssql.git@cython3_fix_v227"),
    ("agent-receiver", "$(execpath @omd_packages//:agent-receiver)"),
    ("werks", "$(execpath @omd_packages//packages:werks)"),
]]

genrule(
    name = "python3-modules-modify",
    srcs = [
        "%s_compile" % module
        for module in all_requirements + [
            "cython3",
            "agent-receiver",
            "werks",
        ]
    ],
    outs = [
        "python3-modules",
    ],
    cmd = """
        mkdir -p $(RULEDIR)/python3-modules
        for MODULE in $(SRCS); do
            if ls $$MODULE/* >/dev/null 2>&1; then
                rsync -a $$MODULE/* $(RULEDIR)/python3-modules/
            fi
        done

        # For some highly obscure unknown reason some files end up world-writable. Fix that!
        chmod -R o-w $(RULEDIR)/python3-modules/lib/python3.11/site-packages

        # Cleanup some unwanted files (example scripts)
        find $(RULEDIR)/python3-modules/bin -name "*.py" ! -name snmpsimd.py -exec rm -f {} \\;

        # These files break the integration tests on the CI server. Don't know exactly
        # why this happens only there, but should be a working fix.
        rm -r -f $(RULEDIR)/python3-modules/snmpsim

        # Cleanup unneeded test files of numpy
        rm -r -f $(RULEDIR)/python3-modules/lib/python3.11/site-packages/numpy/*/tests

        # Fix python interpreter for kept scripts
        sed -E -i '1s|^#!.*/python3?$$|#!/usr/bin/env python3|' $(RULEDIR)/python3-modules/bin/[!_]*

        # pip is using pip._vendor.distlib.scripts.ScriptMaker._build_shebang() to
        # build the shebang of the scripts installed to bin. When executed via our CI
        # containers, the shebang exceeds the max_shebang_length of 127 bytes. For this
        # case, it adds a #!/bin/sh wrapper in front of the python code o_O to make it
        # fit into the shebang. Let's also cleanup this case.
        sed -i -z "s|^#\\!/bin/sh\\n.*exec.*python3.*\\n.*|#\\!/usr/bin/env python3|" $(RULEDIR)/python3-modules/bin/[!_]*

        # Fix rpath for all .so libs
        cd $(RULEDIR)/python3-modules/lib/
        for F in $$(find -name "*.so");
            do patchelf --set-rpath \\
            $$(echo $$F | sed 's|[^/]*/|../|g' | sed 's|\\.\\./|\\$$ORIGIN/|' | sed 's|[^/]*$$||') $$F ;
        done
        cd -

        # Fix gunicorn permissios
        chmod +x $(RULEDIR)/python3-modules/bin/gunicorn
    """,
)
