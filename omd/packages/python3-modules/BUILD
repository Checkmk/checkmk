load("@omd_packages//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")
load("@python_modules//:requirements.bzl", "all_requirements")
load(":build-python3-modules.bzl", "build_python_module", "create_requirements_file")

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

# Third Party packages parsed from runtime-requirements.txt
[build_python_module(
    name = module,
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
) for module in all_requirements]

# TODO: Switch to official release when netapp has fixed their build process
# See: https://github.com/NetApp/ontap-rest-python/issues/46
build_python_module(
    name = "netapp-ontap",
    srcs = [
        "@freetds",
        "@omd_packages//omd/packages/omd:use_system_openssl",
        "@openssl",
        "@python",
    ],
    outs = [
        "compiled_netapp-ontap.tar",
    ],
    requirements = "git+https://github.com/Checkmk/netapp-ontap-cmk.git@e38ce4ce357ad2ea8f47260c269757f8805bdbce",
)

genrule(
    name = "python3-modules",
    srcs = [
        "%s_compile" % module
        for module in all_requirements + [
            "netapp-ontap",
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
