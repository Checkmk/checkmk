load("@omd_packages//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")
load("@python_modules//:requirements.bzl", "packages")

def get_pip_options(module_name):
    return {
        # * avoid compiling with BLAS support - we don't need super fast numpy (yet)
        "numpy": '--config-settings=setup-args="-Dallow-noblas=true"',
        # pillow in version 11.2 and above would require libavif>=1.0.0 which is per default not available on debian-12, see https://github.com/radarhere/Pillow/commit/7d50816f0a6e607b04f9bdc8af7482a29ba578e3 and as we don't need avif support, we simply disable it
        "pillow": "--config-settings=avif=disable",
    }.get(module_name, "")

def create_requirements_file(name, outs):
    """This macro is creating a requirements file per module.
    """
    native.genrule(
        name = name,
        outs = outs,
        cmd = """
           echo "%s %s" > $@
        """ % (packages[name], get_pip_options(name)),
    )

def build_python_module(name, srcs, outs, requirements = "", **kwargs):
    # buildifier: disable=function-docstring-args
    """This macro is creating an empty file.
    """
    requirements = requirements if requirements else "-r $$HOME/$(execpath %s_requirements.txt)" % name
    openssl_dir = Label("@openssl").repo_name
    freetds_dir = Label("@freetds").repo_name
    python_dir = Label("@python").repo_name
    native.genrule(
        name = name + "_compile",
        srcs = srcs,
        outs = outs,
        cmd = select({
            "//conditions:default": build_cmd.format(
                git_ssl_no_verify = "",
                pyMajMin = PYTHON_MAJOR_DOT_MINOR,
                requirements = requirements,
                openssl_dir = openssl_dir,
                freetds_dir = freetds_dir,
                python_dir = python_dir,
            ),
            ":git_ssl_no_verify": build_cmd.format(
                git_ssl_no_verify = "GIT_SSL_NO_VERIFY=true",
                pyMajMin = PYTHON_MAJOR_DOT_MINOR,
                requirements = requirements,
                openssl_dir = openssl_dir,
                freetds_dir = freetds_dir,
                python_dir = python_dir,
            ),
        }),
        **kwargs
    )

build_cmd = """
    set -e
    # Needed because RULEDIR is relative and we need absolute paths as prefix
    export HOME=$$PWD
    export TMPDIR="/tmp"

    # output needs to be an archive for bazel 7
    MODULE_NAME=$$(basename $@)

    # Path to external dependencies
    # SRCS contains a whitespace seperated list of paths to dependencies.
    # We pick one containing 'external' and cut the path after the keyword.
    EXT_DEPS_PATH=$$(echo $(SRCS) | sed 's/.*\\s\\(.*external\\).*\\s.*/\\1/')

    # This is where the Python Modules should be found
    export LD_LIBRARY_PATH="$$PWD/$$EXT_DEPS_PATH/{python_dir}/python/lib/:$$PWD/$$EXT_DEPS_PATH/{openssl_dir}/openssl/lib/"

    # Python binary supplied by bazel build process
    export PYTHON_EXECUTABLE=$$PWD/$$EXT_DEPS_PATH/{python_dir}/python/bin/python3

    # Workaround for git execution issue
    mkdir -p $$TMPDIR/workdir/$$MODULE_NAME
    install -m 755 "$(execpath @omd_packages//omd/packages/omd:use_system_openssl)" "$$TMPDIR/workdir/$$MODULE_NAME/git"
    export PATH="$$TMPDIR/workdir/$$MODULE_NAME:$$PATH"

    # Build directory
    mkdir -p $$HOME/$$MODULE_NAME

    export CPATH="$$HOME/$$EXT_DEPS_PATH/{python_dir}/python/include/python{pyMajMin}/:$$HOME/$$EXT_DEPS_PATH/{openssl_dir}/openssl/include/openssl:$$HOME/$$EXT_DEPS_PATH/{freetds_dir}/freetds/include/"

    # Reduce GRPC build load peaks - See src/python/grpcio/_parallel_compile_patch.py in grpcio package
    # Keep in sync with scripts/run-uvenv
    export GRPC_PYTHON_BUILD_EXT_COMPILER_JOBS=4
    export NPY_NUM_BUILD_JOBS=4

    export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1

    # rust-openssl uses pkg-config to find the openssl libraries (good idea). But pkg-config is broken in the bazel build environment.
    # Therefore we need to give it some pointers. Here is the logic to find the openssl libaries to link against.
    # https://github.com/sfackler/rust-openssl/blob/10cee24f49cd3f37da1dbf663ba67bca6728db1f/openssl-sys/build/find_normal.rs#L8
    # TODO: we should ideally adjust the PKG_CONFIG_PATH to add the openssl pkgconfig files

    export OPENSSL_LIB_DIR="$$HOME/$$EXT_DEPS_PATH/{openssl_dir}/openssl/lib"
    export OPENSSL_INCLUDE_DIR="$$HOME/$$EXT_DEPS_PATH/{openssl_dir}/openssl/include"

    # Under some distros (e.g. almalinux), the build may use an available c++ system compiler instead of our own /opt/bin/g++
    # Enforce here the usage of the build image compiler and in the same time enable local building.
    # TODO: CMK-15581 The whole toolchain registration should be bazel wide!
    export CXX="$$(which g++)"
    export CC="$$(which gcc)"

    # install requirements
    export CPPFLAGS="-I$$HOME/$$EXT_DEPS_PATH/{openssl_dir}/openssl/include -I$$HOME/$$EXT_DEPS_PATH/{freetds_dir}/freetds/include -I$$HOME/$$EXT_DEPS_PATH/{python_dir}/python/include/python{pyMajMin}/"
    export LDFLAGS="-L$$HOME/$$EXT_DEPS_PATH/{openssl_dir}/openssl/lib -L$$HOME/$$EXT_DEPS_PATH/{freetds_dir}/freetds/lib -L$$HOME/$$EXT_DEPS_PATH/{python_dir}/python/lib -Wl,--strip-debug"
    {git_ssl_no_verify}\\
    $$PYTHON_EXECUTABLE -m pip install \\
     `: dont use precompiled things, build with our build env ` \\
      --verbose \\
      --no-binary=":all:" \\
      --no-deps \\
      --compile \\
      --isolated \\
      --ignore-installed \\
      --no-warn-script-location \\
      --prefix="$$HOME/$$MODULE_NAME" \\
      {requirements} 2>&1 | tee "$$HOME/""$$MODULE_NAME""_pip_install.stdout"

    tar cf $@ $$MODULE_NAME
"""
