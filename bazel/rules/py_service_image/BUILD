# The interpreter of the Bazel toolchain, as one layer for all images.
genrule(
    name = "python_layer",
    srcs = ["@rules_python//python:current_py_toolchain"],
    outs = ["python_layer.tar.gz"],
    cmd = """
        tmp="$$(mktemp -d)"
        trap 'rm -rf "$$tmp"' EXIT
        mkdir -p "$$tmp/app/python/bin"
        # Bazel gives the files as links, so copy what they point to.
        cp --dereference "$(PYTHON3)" "$$tmp/app/python/bin/python3"
        # Only the standard library goes in, without the parts that a service
        # does not use. The binary has libpython and OpenSSL built in.
        (cd "$$(dirname "$$(dirname "$(PYTHON3)")")" && tar --create --file - --dereference \\
            --anchored --wildcards \\
            --exclude='lib/python3.*/config-*' --exclude='lib/python3.*/ensurepip' \\
            --exclude='lib/python3.*/idlelib' --exclude='lib/python3.*/pydoc_data' \\
            --exclude='lib/python3.*/site-packages' --exclude='lib/python3.*/tkinter' \\
            --exclude='lib/python3.*/turtledemo' --exclude='lib/python3.*/__phello__' \\
            --exclude='lib/python3.*/lib-dynload/_tkinter*' \\
            --exclude='lib/python3.*/turtle.py' --exclude='*/__pycache__' \\
            lib/python3.*) | tar --extract --file - --directory "$$tmp/app/python"
        # Fixed times and owners: the same content gives the same archive.
        tar --create --file - --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner \\
            --directory "$$tmp" app | gzip --no-name > $@
    """,
    # The commands need GNU tar, and the image is for this platform only.
    target_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    toolchains = ["@rules_python//python:current_py_toolchain"],
    visibility = ["//visibility:public"],
)
