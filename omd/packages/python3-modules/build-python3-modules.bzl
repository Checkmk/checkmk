# ToDo:
#    - PIPENV_PYPI_MIRROR (see technical dept socumentation)

load("@python_modules//:requirements.bzl", "packages")

def get_pip_options(module_name):
    return {
        # * avoid compiling with BLAS support - we don't need super fast numpy (yet)
        "numpy": '--config-settings=setup-args="-Dallow-noblas=true"',
    }.get(module_name, "")

def create_requirements_file(name, outs):
    """This macro is creating a requirements file per module.
    """
    native.genrule(
        name = name,
        outs = outs,
        cmd = """
           echo "%s" > $@
        """ % packages[name],
    )

def build_python_module(name, srcs, outs, cmd, **kwargs):
    """This macro is creating an empty file.
    """
    native.genrule(
        name = name,
        srcs = srcs,
        outs = outs,
        cmd = cmd,
        toolchains = ["@rules_python//python:current_py_toolchain"],
        **kwargs
    )

build_cmd = """
    set -e
    # Needed because RULEDIR is relative and we need absolute paths as prefix
    export HOME=$$PWD
    export TMPDIR="/tmp"

    # Path to external dependencies
    # SRCS contains a whitespace seperated list of paths to dependencies.
    # We pick one containing 'external' and cut the path after the keyword.
    EXT_DEPS_PATH=$$(echo $(SRCS) | sed 's/.*\\s\\(.*external\\).*\\s.*/\\1/')

    # This is where the Python Modules should be found

    # Workaround for git execution issue
    mkdir -p $$TMPDIR/workdir/$(OUTS)
    install -m 755 "$(execpath @omd_packages//omd/packages/omd:use_system_openssl)" "$$TMPDIR/workdir/$(OUTS)/git"
    export PATH="$$TMPDIR/workdir/$(OUTS):$$PATH"

    # Build directory
    mkdir -p $$HOME/$(OUTS)

    # Reduce GRPC build load peaks - See src/python/grpcio/_parallel_compile_patch.py in grpcio package
    # Keep in sync with scripts/run-pipenv
    export GRPC_PYTHON_BUILD_EXT_COMPILER_JOBS=4
    export NPY_NUM_BUILD_JOBS=4

    export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1

    # rust-openssl uses pkg-config to find the openssl libraries (good idea). But pkg-config is broken in the bazel build environment.
    # Therefore we need to give it some pointers. Here is the logic to find the openssl libaries to link against.
    # https://github.com/sfackler/rust-openssl/blob/10cee24f49cd3f37da1dbf663ba67bca6728db1f/openssl-sys/build/find_normal.rs#L8
    # TODO: we should ideally adjust the PKG_CONFIG_PATH to add the openssl pkgconfig files

    if [[ "{requirements}" = -r* || "{requirements}" = git+* ]]; then
        REQUIREMENTS="{requirements}"
    else
        REQUIREMENTS=$$HOME/tmp/$(OUTS)
	rm -rf $$REQUIREMENTS
	mkdir -p $$REQUIREMENTS
        echo "Copy package sources"
        echo "cp -r {requirements}/** $$REQUIREMENTS"
        cp -r {requirements}/** $$REQUIREMENTS
    fi

    # Fix python-gssapi build on SLES12SP5
    # https://github.com/pythongssapi/python-gssapi/issues/212
    if grep 'PRETTY_NAME="SUSE Linux Enterprise Server 12 SP5"' /etc/os-release >/dev/null 2>&1; then
        export GSSAPI_COMPILER_ARGS='-DHAS_GSSAPI_EXT_H'
    fi

    # Under some distros (e.g. almalinux), the build may use an available c++ system compiler instead of our own /opt/bin/g++
    # Enforce here the usage of the build image compiler and in the same time enable local building.
    # TODO: CMK-15581 The whole toolchain registration should be bazel wide!
    export CXX="$$(which g++)"
    export CC="$$(which gcc)"

    # install requirements
    export LDFLAGS="$${{LDFLAGS:-""}} -Wl,--strip-debug -Wl,--rpath,/omd/versions/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/lib"
    {git_ssl_no_verify}\\
    $(PYTHON3) -m pip install \\
     `: dont use precompiled things, build with our build env ` \\
      --verbose \\
      --no-binary=":all:" \\
      --no-deps \\
      --compile \\
      --isolated \\
      --ignore-installed \\
      --no-warn-script-location \\
      --prefix="$$HOME/$(OUTS)" \\
      -i {pypi_mirror} \\
      {pip_add_opts} \\
      $$REQUIREMENTS 2>&1 | tee "$$HOME/$(OUTS)_pip_install.stdout"
"""
