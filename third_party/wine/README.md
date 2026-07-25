# Wine (from Source)

This directory builds the Wine tarball pinned by the `@wine_linux_x86_64`
Bazel module (`MODULE.bazel`). Wine powers the Windows-agent-from-source test
tier (`//agents/wnx:watest-wine`) and the WiX multi-cabinet MSI build
(`//agents/wnx:check_mk_agent_msi`)

We build Wine ourselves rather than pinning a third-party prebuilt binary, so
the artifact's provenance is fully traceable.

## What Is Built

- **Version:** Wine 11.0 (WineHQ stable).
- **Flavor:** `amd64-wow64` — new-style WoW64 (`--enable-archs=i386,x86_64`): a
  single 64-bit prefix carrying the 32-bit PE DLLs, with **no** i386 Unix
  libraries and **no** 32-bit host toolchain.
- **glibc floor:** 2.28 (built in the pinned AlmaLinux 8 image). The artifact
  runs on AlmaLinux/RHEL 8 and newer; it will **not** run on glibc < 2.28
  (e.g. RHEL 7).
- **Mono / Gecko:** not bundled. Consumers install wine-mono (10.4.1) into
  throwaway prefixes themselves.

## Files

- `create-archive` — downloads the pinned WineHQ source, verifies it against
  `wine.sha256`, applies any `patches/*.dif`, configures + builds the WoW64
  flavor, prunes to the shipped tree, and produces
  `wine-11.0-amd64-wow64.tar.xz` (printing its sha256 to pin in `MODULE.bazel`)
  plus the retained `wine-11.0.tar.xz` source.
- `wine.sha256` — pinned sha256 of the upstream `wine-11.0.tar.xz` source
  (provenance gate). The upstream sha512 is additionally cross-checked against
  WineHQ's signed `sha512sums.asc` during pinning.
- `patches/` — patches applied to the source before building. Changing this
  set changes the artifact's content, so a republish needs a fresh name (see
  _Building and Publishing_). Current set:
  - `cabinet-fci-dataless-folder.dif` — FCI fails to write cabinets whose
    final folder holds only zero-length files (WiX smart cabbing produces
    exactly that for product.cab); one-line fix in `write_data_blocks()`,
    not yet upstream as of Wine 11.14. Details and repro in the patch header.
- `Dockerfile` — the build environment: FROM the pinned AlmaLinux 8 base plus
  the Wine build toolchain (clang, lld, llvm-dlltool, the mingw-w64 sysroot, and
  Wine's X11/font/TLS dev libs) and the AWS CLI used for publishing. Built
  inline as the first step of the CI job.

## Building and Publishing

`create-archive` needs the Wine build toolchain present and must run in an
environment whose glibc is <= the target floor (AlmaLinux 8 / 2.28) — i.e. the
image built from `Dockerfile`.

In CI this is driven by `buildscripts/scripts/build-wine-from-source.groovy`
(manual job). It builds the `Dockerfile` image inline (FROM the pinned
AlmaLinux 8 base), then runs `buildscripts/scripts/build_wine.sh` inside it.
Keeping the toolchain in this job-local image avoids bloating the shared
AlmaLinux 8 build image, and baking it at image-build time means the build runs
without root. `build_wine.sh` builds the tarball and publishes it (with its
corresponding LGPL source) to the public CI binary-artifacts S3 bucket, under

```
dl/wine/wine/<version>/linux/<arch>/<variant>/<file>
```

the same object schema `buildscripts/scripts/extract_llvm.sh` uses. Afterwards
the `urls` and `sha256` are updated in `MODULE.bazel`; the job prints the public
URL to pin. Published objects are treated as immutable — a rebuilt artifact that
differs in content needs a fresh name (bump `<variant>`), so that older
`MODULE.bazel` pins keep resolving.

To run `create-archive` standalone (e.g. locally), build/enter the `Dockerfile`
image first (or otherwise provide the toolchain).

## Licence / Attribution

Wine itself is licensed under the **LGPL-2.1-or-later**. `create-archive` bundles
Wine's `LICENSE`, `COPYING.LIB` (the LGPL text) and `AUTHORS` into the produced
tarball, so the distributed binary carries its own license and copyright
notices.

The **corresponding source** is the exact upstream tarball pinned in
`wine.sha256` plus the `patches/*.dif` set, together with this
`create-archive` recipe. `build_wine.sh` publishes that source tarball from the
**same place** as the binary, and the applied patches travel inside the binary
tarball (`patches/` next to `BUILDINFO`), so a public download of the binary is
accompanied by its complete source, as the LGPL (section 4) requires.

`create-archive` is our own work. It was informed by studying Kron4ek's publicly
available Wine-Builds scripts (<https://github.com/Kron4ek/Wine-Builds>, MIT).
Credited here as the reference for the `amd64-wow64` recipe — but it contains no
Kron4ek code: we reimplement the build against upstream WineHQ source, and no
third-party build scripts are vendored or distributed in this directory.
