# ToDo:
#    - PIPENV_PYPI_MIRROR (see technical dept socumentation)

load("@python_modules//:requirements.bzl", "packages")

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
        **kwargs
    )

build_cmd = """
    set -e
    # Needed because RULEDIR is relative and we need absolute paths as prefix
    export HOME=$$PWD

    # Path to external dependencies
    EXT_DEPS_PATH='bazel-out/k8-fastbuild/bin/external'

    # This is where the Python Modules should be found
    export LD_LIBRARY_PATH="$$PWD/$$EXT_DEPS_PATH/python/python/lib/:$$PWD/$$EXT_DEPS_PATH/openssl/openssl/lib/"

    # Python binary supplied by bazel build process
    export PYTHON_EXECUTABLE=$$PWD/$$EXT_DEPS_PATH/python/python/bin/python3

    INTERNAL_PYPI_MIRROR=https://devpi.lan.tribe29.com/root/pypi

    # Workaround for git execution issue
    mkdir -p $$TMPDIR/workdir/$(OUTS)
    install -m 755 "$(execpath @omd_packages//omd/packages/omd:use_system_openssl)" "$$TMPDIR/workdir/$(OUTS)/git"
    export PATH="$$TMPDIR/workdir/$(OUTS):$$PATH"

    # Build directory
    mkdir -p $$HOME//$(OUTS)

    echo -e "cython==0.29.34" > $$TMPDIR/constraints.txt

    export CPATH="$$HOME/$$EXT_DEPS_PATH/python/python/include/python{pyMajMin}/:$$HOME/$$EXT_DEPS_PATH/openssl/openssl/include/openssl:$$HOME/$$EXT_DEPS_PATH/freetds/freetds/include/"

    # Set up rust toolchain (probably better done bazel wide?)
    export RUSTUP_HOME="/opt/rust/rustup"
    export TMPDIR="/tmp"
    export PATH="/opt/rust/cargo/bin:$$PWD/$$EXT_DEPS_PATH/python/python/bin/:$$PATH"

    # Reduce GRPC build load peaks - See src/python/grpcio/_parallel_compile_patch.py in grpcio package
    # Keep in sync with scripts/run-pipenv
    export GRPC_PYTHON_BUILD_EXT_COMPILER_JOBS=4
    export NPY_NUM_BUILD_JOBS=4

    export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1

    # rust-openssl uses pkg-config to find the openssl libraries (good idea). But pkg-config is broken in the bazel build environment.
    # Therefore we need to give it some pointers. Here is the logic to find the openssl libaries to link against.
    # https://github.com/sfackler/rust-openssl/blob/10cee24f49cd3f37da1dbf663ba67bca6728db1f/openssl-sys/build/find_normal.rs#L8
    # TODO: we should ideally adjust the PKG_CONFIG_PATH to add the openssl pkgconfig files

    export OPENSSL_LIB_DIR="$$HOME/$$EXT_DEPS_PATH/openssl/openssl/lib"
    export OPENSSL_INCLUDE_DIR="$$HOME/$$EXT_DEPS_PATH/openssl/openssl/include"

    # install requirements
    export CFLAGS="-I$$HOME/$$EXT_DEPS_PATH/openssl/openssl/include -I$$HOME/$$EXT_DEPS_PATH/freetds/freetds/include -I$$HOME/$$EXT_DEPS_PATH/python/python/include/python{pyMajMin}/"
    export LDFLAGS="-L$$HOME/$$EXT_DEPS_PATH/openssl/openssl/lib -L$$HOME/$$EXT_DEPS_PATH/freedts/freedts/lib -L$$HOME/$$EXT_DEPS_PATH/python/python/lib -Wl,--strip-debug -Wl,--rpath,/omd/versions/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/lib"
    {git_ssl_no_verify}\\
    $$PYTHON_EXECUTABLE -m pip install \\
     `: dont use precompiled things, build with our build env ` \\
      --no-binary=":all:" \\
      --no-deps \\
      --compile \\
      --isolated \\
      --ignore-installed \\
      --no-warn-script-location \\
      --prefix="$$HOME/$(OUTS)" \\
      --constraint $$TMPDIR/constraints.txt \\
      -i $$INTERNAL_PYPI_MIRROR \\
      {requirements}
"""
