# Build environment for the from-source Wine build. It is built inline as the
# first step of buildscripts/scripts/build-wine-from-source.groovy, FROM the
# pinned AlmaLinux 8 base (glibc floor 2.28), adding only the Wine 11 build
# toolchain. Keeping these deps in a job-local image avoids bloating the shared
# AlmaLinux 8 build image, and baking them at image-build time (inherently root)
# avoids needing root when the build itself runs.
#
# The PE (WoW64) side is cross-compiled with clang + lld + llvm-dlltool against
# the mingw-w64 sysroot; the distro mingw-w64 GCC (7.2.0) is too old for Wine
# 11's PE code, so mingw-gcc is intentionally not installed (Wine's configure
# auto-selects clang when it is absent).
ARG IMAGE_BASE
FROM ${IMAGE_BASE}

RUN yum -y install epel-release && \
    yum -y --enablerepo=powertools install \
    gcc gcc-c++ make flex bison curl xz tar findutils perl \
    clang lld llvm \
    mingw64-binutils mingw32-binutils \
    mingw64-headers mingw64-crt mingw32-headers mingw32-crt \
    freetype-devel fontconfig-devel gnutls-devel gettext-devel \
    libX11-devel libXext-devel libXcursor-devel libXi-devel libXrandr-devel \
    libXrender-devel libXinerama-devel libXcomposite-devel libXfixes-devel \
    libxcb-devel && \
    yum clean all
