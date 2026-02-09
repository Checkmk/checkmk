"""Repository rule for C++ runtime libraries that separates ELF files from symlinks. Only for local toolchains."""

def _get_lib_path(repository_ctx, lib_name):
    """Get the path object for a library using g++ -print-file-name."""
    result = repository_ctx.execute([repository_ctx.attr.gcc_path, "-print-file-name=" + lib_name])
    if result.return_code == 0:
        path_str = result.stdout.strip()
        if path_str and path_str != lib_name:  # g++ returns the name unchanged if not found
            repository_ctx.report_progress("cpp-libs: Library '{}' found at '{}'".format(lib_name, path_str))
            return repository_ctx.path(path_str)
    repository_ctx.report_progress("cpp-libs: Library '{}' not found".format(lib_name))
    return None

def _resolve_library(repository_ctx, lib_path):
    """Follow symlinks and return the symlink chain.

    Returns:
        - symlink_chain: List of (link_name, target_name) tuples (basenames only)
    """
    if not lib_path:
        return (None, [])

    current = lib_path
    symlink_chain = []

    for _ in range(3):  # 3 is the maximum depth of symlinks we will follow, major, minor and patch versions of the library.
        result = repository_ctx.execute([repository_ctx.attr.readlink_path, current])
        if result.return_code != 0:
            # Not a symlink, we've reached the real file
            break

        target_str = result.stdout.strip()
        if target_str.startswith("/"):
            target = repository_ctx.path(target_str)
        else:
            target = current.dirname.get_child(target_str)

        symlink_chain.append((current.basename, target.basename))
        current = target

    return symlink_chain

def _get_soname(repository_ctx, elf_path):
    """Extract the SONAME from an ELF file using readelf.

    The SONAME is the name the dynamic linker searches for at runtime
    (e.g. libstdc++.so.6).  Reading it from the ELF metadata is more
    robust than hard-coding version strings because it adapts
    automatically to any GCC / library version.

    Returns:
        The SONAME string, or None if it could not be determined.
    """
    result = repository_ctx.execute([repository_ctx.attr.readelf_path, "-d", str(elf_path)])
    if result.return_code != 0:
        return None
    for line in result.stdout.split("\n"):
        if "SONAME" not in line:
            continue

        # readelf output: 0x…… (SONAME)  Library soname: [libstdc++.so.6]
        start = line.find("[")
        end = line.find("]")
        if start != -1 and end != -1:
            return line[start + 1:end]
    return None

def _cpp_libs_repository_impl(repository_ctx):
    """Detects symlinks vs ELF files at fetch time and generates appropriate BUILD file."""
    files = []
    elf_files = []
    symlink_mappings = []

    # libgcc_s.so is a linker script (text file), include it as a file.
    libgcc_so_path = _get_lib_path(repository_ctx, "libgcc_s.so")
    if libgcc_so_path:
        repository_ctx.symlink(libgcc_so_path, libgcc_so_path.basename)
        files.append(libgcc_so_path.basename)

    # Process libraries that may be symlinks to versioned ELF files
    for lib_name in ["libgcc_s.so.1", "libstdc++.so"]:
        lib_path = _get_lib_path(repository_ctx, lib_name)
        if not lib_path:
            continue

        # Resolve the ELF file and create a symlink to it.
        real_path = lib_path.realpath
        repository_ctx.symlink(real_path, real_path.basename)
        elf_files.append(real_path.basename)

        # Resolve the symlink chain to the actual ELF file.
        chain = _resolve_library(repository_ctx, lib_path)
        symlink_mappings.extend(chain)

        # Ensure the SONAME symlink is present.  On some systems
        # (e.g. libstdc++.so -> libstdc++.so.6.0.33 directly) the
        # intermediate SONAME link (libstdc++.so.6) may not appear in
        # the on-disk symlink chain, yet the dynamic linker needs it.
        soname = _get_soname(repository_ctx, real_path)
        if soname and soname != real_path.basename:
            soname_mapping = (soname, real_path.basename)
            if soname_mapping not in symlink_mappings:
                symlink_mappings.append(soname_mapping)

    # Generate symlink_mappings.bzl
    mappings_str = ", ".join([
        '("{}", "{}")'.format(link, target)
        for link, target in sorted(symlink_mappings)
    ])
    repository_ctx.template(
        "symlink_mappings.bzl",
        Label("//omd/packages/cpp-libs:cpp-libs.tpl.symlink_mappings.bzl"),
        substitutions = {"{mappings}": mappings_str},
        executable = False,
    )

    # Generate BUILD.bazel from template
    files_str = ", ".join(['"{}"'.format(f) for f in sorted(files)])
    elf_srcs_str = ", ".join(['"{}"'.format(f) for f in sorted(elf_files)])
    repository_ctx.template(
        "BUILD.bazel",
        Label("//omd/packages/cpp-libs:cpp-libs.tpl.BUILD.bazel"),
        substitutions = {"{elf_srcs}": elf_srcs_str, "{files}": files_str},
        executable = False,
    )

cpp_libs_repository = repository_rule(
    implementation = _cpp_libs_repository_impl,
    attrs = {
        "gcc_path": attr.string(
            doc = "Path to g++ compiler (e.g., 'g++' or '/usr/bin/g++')",
            mandatory = True,
        ),
        "readelf_path": attr.string(
            doc = "Path to readelf (e.g., 'readelf' or '/usr/bin/readelf')",
            mandatory = True,
        ),
        "readlink_path": attr.string(
            doc = "Path to readlink (e.g., 'readlink' or '/usr/bin/readlink')",
            mandatory = True,
        ),
    },
    local = True,  # Re-fetch when local files change
    doc = "Creates a repository with separate filegroups for ELF files and symlinks, detected at fetch time using g++ -print-file-name",
)
