"""Macros to build Python modules from source with pip."""

load("@python_modules//:requirements.bzl", "packages")
load("//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")

def get_pip_options(module_name):
    return {
        # matplotlib's meson build defaults to downloading and building its own vendored
        # freetype as a subproject, which requires network access at build time.
        # Use the system library instead, which is already provided by the build image.
        # qhull and libraqm are left vendored (system-qhull/system-libraqm are NOT
        # set): our build images don't provide a usable libqhull_r, and ship
        # libraqm 0.10.1, older than the >=0.10.4 matplotlib requires. Their sources
        # (and harfbuzz/sheenbidi) are instead seeded offline, see get_extra_setup().
        "matplotlib": '--config-settings=setup-args="-Dsystem-freetype=true"',

        # * avoid compiling with BLAS support - we don't need super fast numpy (yet)
        "numpy": '--config-settings=setup-args="-Dallow-noblas=true"',
        # pillow in version 11.2 and above would require libavif>=1.0.0 which is per default not available on debian-12, see https://github.com/radarhere/Pillow/commit/7d50816f0a6e607b04f9bdc8af7482a29ba578e3 and as we don't need avif support, we simply disable it
        "pillow": "--config-settings=avif=disable",
    }.get(module_name, "")

def get_extra_setup(module_name):
    """Shell snippet executed right before `pip install`.

    Used to seed a local meson subproject package cache (MESON_PACKAGE_CACHE_DIR)
    so meson resolves vendored C deps from disk instead of downloading them at
    build time. The Bazel-fetched srcs referenced here must be added to that
    module's `srcs` in the calling BUILD file.
    """
    return {
        "matplotlib": """
	    # meson runs harfbuzz's gen-hb-version.py through its
            # "#!/usr/bin/env python3" shebang. LD_LIBRARY_PATH (see build_cmd) puts
            # our bundled Python's lib dir first, so a system python3 that links
            # libpython dynamically -- sles-16.0 does, with a colliding 3.13 soname --
            # loads the wrong libpython and aborts before running the script. Resolve
            # python3 to the interpreter LD_LIBRARY_PATH already matches.
            export PATH="$$(dirname "$$PYTHON_EXECUTABLE"):$$PATH"
            # Build in a private, guaranteed-writable/empty TMPDIR instead of the shared
            # host /tmp: pip/meson-python stage the harfbuzz/libraqm/etc.
            export TMPDIR="$$HOME/tmp_matplotlib"
            mkdir -p "$$TMPDIR"
            export MESON_PACKAGE_CACHE_DIR="$$HOME/mpl_packagecache"
            mkdir -p "$$MESON_PACKAGE_CACHE_DIR"
            cp "$(execpath @matplotlib_harfbuzz_src//file)" "$$MESON_PACKAGE_CACHE_DIR/harfbuzz-14.1.0.tar.xz"
            cp "$(execpath @matplotlib_sheenbidi_src//file)" "$$MESON_PACKAGE_CACHE_DIR/sheenbidi-3.0.0.tar.gz"
            cp "$(execpath @matplotlib_libraqm_src//file)" "$$MESON_PACKAGE_CACHE_DIR/libraqm-0.10.5.tar.gz"
            cp "$(execpath @matplotlib_qhull_src//file)" "$$MESON_PACKAGE_CACHE_DIR/qhull-8.0.2.tgz"
        """,
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
    constraints = "$$HOME/$(execpath //:constraints.txt)"
    openssl_dir = Label("@openssl").repo_name
    freetds_dir = Label("@freetds").repo_name
    python_dir = Label("@python").repo_name
    extra_setup = get_extra_setup(name)
    native.genrule(
        name = name + "_compile",
        srcs = srcs,
        outs = outs,
        tools = [
            "@//bazel/toolchains/rust:rustc",
            "@//bazel/toolchains/rust:cargo",
        ],
        cmd = select({
            ":git_ssl_no_verify": build_cmd.format(
                git_ssl_no_verify = "GIT_SSL_NO_VERIFY=true",
                pyMajMin = PYTHON_MAJOR_DOT_MINOR,
                requirements = requirements,
                constraints = constraints,
                extra_setup = extra_setup,
                openssl_dir = openssl_dir,
                freetds_dir = freetds_dir,
                python_dir = python_dir,
            ),
            "//conditions:default": build_cmd.format(
                git_ssl_no_verify = "",
                pyMajMin = PYTHON_MAJOR_DOT_MINOR,
                requirements = requirements,
                constraints = constraints,
                extra_setup = extra_setup,
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

    # Python binary supplied by bazel build process. Safe to run directly out of
    # @python's tree: it ships fully precompiled (CMK-35159), so importing here
    # never writes bytecode back into @python's output.
    export PYTHON_EXECUTABLE=$$PWD/$$EXT_DEPS_PATH/{python_dir}/python/bin/python3

    # Workaround for git execution issue: pip may call git for VCS deps, but LD_LIBRARY_PATH
    # is set to our OpenSSL which conflicts with system git. The wrapper unsets it.
    mkdir -p $$TMPDIR/workdir/$$MODULE_NAME
    install -m 755 "$(execpath :git_wrapper)" "$$TMPDIR/workdir/$$MODULE_NAME/git"
    export PATH="$$TMPDIR/workdir/$$MODULE_NAME:$$PATH"

    # Build directory
    mkdir -p $$HOME/$$MODULE_NAME

    export CPATH="$$HOME/$$EXT_DEPS_PATH/{python_dir}/python/include/python{pyMajMin}/:$$HOME/$$EXT_DEPS_PATH/{openssl_dir}/openssl/include/openssl:$$HOME/$$EXT_DEPS_PATH/{freetds_dir}/freetds/include/"

    # Reduce GRPC build load peaks - See src/python/grpcio/_parallel_compile_patch.py in grpcio package
    # Keep in sync with scripts/run-uvenv
    export GRPC_PYTHON_BUILD_EXT_COMPILER_JOBS=4
    export NPY_NUM_BUILD_JOBS=4

    export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1

    # Force python-lz4 to compile its vendored lz4 sources statically instead of
    # linking a system liblz4. python-lz4's setup.py links the system library when
    # pkg-config finds one, so the shipped extension would otherwise depend on
    # whatever liblz4 happens to be present in the build image (non-hermetic) -- and
    # the resulting liblz4.so.1 runtime dependency is neither shipped nor declared in
    # the package. Keeping lz4 self-contained avoids that. Only affects the lz4 module.
    export PYLZ4_USE_SYSTEM_LZ4=0

    # rust-openssl uses pkg-config to find the openssl libraries (good idea). But pkg-config is broken in the bazel build environment.
    # Therefore we need to give it some pointers. Here is the logic to find the openssl libaries to link against.
    # https://github.com/sfackler/rust-openssl/blob/10cee24f49cd3f37da1dbf663ba67bca6728db1f/openssl-sys/build/find_normal.rs#L8
    # TODO: we should ideally adjust the PKG_CONFIG_PATH to add the openssl pkgconfig files

    # Resolve tool paths provided by Bazel:
    export RUSTC="$$HOME/$(location //bazel/toolchains/rust:rustc)"
    export CARGO="$$HOME/$(location //bazel/toolchains/rust:cargo)"
    # The PATH order matters: For the build to be hermetic, we need to prefer `rustc` provided by Bazel.
    export PATH="$$(dirname "$$RUSTC"):$$(dirname "$$CARGO"):$$PATH"

    # Keep cargo artifacts inside the sandbox (optional but nice):
    export CARGO_TARGET_DIR="$(@D)/cargo_out"

    # Strip the Bazel sandbox/execroot prefix ($$HOME == $$PWD == execroot) from
    # the source paths rustc records into panic/debug location metadata (crates
    # live under $$HOME/.cargo/registry). Without this the build-host layout
    # leaks into the Rust-backed wheels (cryptography, pydantic-core, bcrypt,
    # rpds-py, libcst). Mirrors the -ffile-prefix-map=$$HOME=. used for C below.
    export RUSTFLAGS="--remap-path-prefix=$$HOME=."

    export OPENSSL_LIB_DIR="$$HOME/$$EXT_DEPS_PATH/{openssl_dir}/openssl/lib"
    export OPENSSL_INCLUDE_DIR="$$HOME/$$EXT_DEPS_PATH/{openssl_dir}/openssl/include"

    # Under some distros (e.g. almalinux), the build may use an available c++ system compiler instead of our own /opt/bin/g++
    # Enforce here the usage of the build image compiler and in the same time enable local building.
    # TODO: CMK-15581 The whole toolchain registration should be bazel wide!
    export CXX="$$(which g++)"
    export CC="$$(which gcc)"

    # install requirements
    # -ffile-prefix-map strips the Bazel sandbox/execroot prefix ($$HOME == $$PWD
    # == execroot) from paths the compiler bakes into the extension .so files --
    # chiefly the Python/openssl/freetds header -I paths captured via __FILE__ --
    # so the build-host layout does not leak into shipped binaries (SUP-28810).
    export CFLAGS="-Wno-error=incompatible-pointer-types -ffile-prefix-map=$$HOME=."
    export CPPFLAGS="-I$$HOME/$$EXT_DEPS_PATH/{openssl_dir}/openssl/include -I$$HOME/$$EXT_DEPS_PATH/{freetds_dir}/freetds/include -I$$HOME/$$EXT_DEPS_PATH/{python_dir}/python/include/python{pyMajMin}/"
    export LDFLAGS="-L$$HOME/$$EXT_DEPS_PATH/{openssl_dir}/openssl/lib -L$$HOME/$$EXT_DEPS_PATH/{freetds_dir}/freetds/lib -L$$HOME/$$EXT_DEPS_PATH/{python_dir}/python/lib -Wl,--strip-debug"
    {extra_setup}
    {git_ssl_no_verify}\\
    $$PYTHON_EXECUTABLE -m pip install \\
     `: dont use precompiled things, build with our build env ` \\
      --quiet \\
      --no-binary=":all:" \\
      --no-deps \\
      --compile \\
      --isolated \\
      --ignore-installed \\
      --no-warn-script-location \\
      --root-user-action=ignore \\
      --disable-pip-version-check \\
      --use-feature=build-constraint \\
      --build-constraint="{constraints}" \\
      --prefix="$$HOME/$$MODULE_NAME" \\
      {requirements} 2>&1 | tee "$$HOME/""$$MODULE_NAME""_pip_install.stdout" || true
    # The `|| true` above keeps `set -e` from aborting on pip's exit code before
    # we get a chance to inspect PIPESTATUS and dump diagnostics below.
    PIP_INSTALL_STATUS=$${{PIPESTATUS[0]}}
    if [ "$$PIP_INSTALL_STATUS" -ne 0 ]; then
        # pip/meson swallow the actual subprocess output on failure and only point
        # to a meson-log.txt buried in the (ephemeral) sandbox tmpdir -- e.g. the
        # harfbuzz subproject build inside matplotlib's meson-python backend just
        # reports "failed with status 1" with no further detail in the CI console.
        # Dump any such log here so the real traceback survives into the CI log.
        echo "pip install for $$MODULE_NAME failed (exit $$PIP_INSTALL_STATUS); dumping any meson-log.txt found under TMPDIR:"
        find "$$TMPDIR" -name meson-log.txt -print -exec cat {{}} \\; 2>/dev/null
        exit "$$PIP_INSTALL_STATUS"
    fi

    tar cf $@ -C $$MODULE_NAME .
"""
