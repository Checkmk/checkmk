#!groovy

/// file: build-qemu-from-source.groovy

/// Build the static QEMU (third_party/qemu) and publish the tarball pinned by
/// @qemu_linux_x86_64, with all its sources, to the Nexus upstream-archives
/// mirror.
///
/// The QEMU version, the sources and the archive's sha256 are pinned in
/// third_party/qemu/{create-archive,sources.txt,version.bzl}. The build is
/// reproducible: bump the recipe and the pin (from a local build, see
/// third_party/qemu/README.md) in a commit, then trigger this job manually.
/// It refuses to publish an archive that does not match the pin.
///
/// The toolchain is the builder image pinned by digest in
/// third_party/qemu/builder-image.txt (Harbor, built by
/// build-qemu-builder-image.groovy), so a rebuild uses the same toolchain as
/// the build the pin came from. The build runs in a pod of its own with that
/// image as a container: a pod template fixed in Jenkins would need updating
/// with every new pin. The pod is nested in the job's, and takes over its
/// settings.
///
/// Credentials:
///     registry-harbor-ci-qemu (pull secret in the jobs namespace) -> pulls
///         the builder image
///     nexus -> NEXUS_USERNAME / NEXUS_PASSWORD

void main() {
    def builder_image = readFile("${checkout_dir}/third_party/qemu/builder-image.txt").trim();

    // The nested pod has a workspace of its own: hand it what the build reads.
    dir("${checkout_dir}") {
        stash(
            name: "qemu-recipe",
            includes: "bazel_variables.bzl,buildscripts/scripts/build_qemu.sh,third_party/qemu/**");
    }

    podTemplate(
        // Not inherited from the job's pod: unnamed, it is the first cloud.
        cloud: "Klaus",
        // Fresh per build and used by one node() only, see CMK-36601.
        instanceCap: 1,
        yaml: """\
            |apiVersion: v1
            |kind: Pod
            |spec:
            |  imagePullSecrets:
            |  - name: registry-harbor-ci-qemu
            |  containers:
            |  - name: qemu-builder
            |    image: "${builder_image}"
            |    command: ["sleep"]
            |    args: ["9999999"]
            |    resources:
            |      requests:
            |        cpu: "4"
            |        memory: "8G"
            |      limits:
            |        cpu: "8"
            |        memory: "16G"
            |""".stripMargin(),
    ) {
        node(POD_LABEL) {
            container("qemu-builder") {
                unstash("qemu-recipe");
                withNexusCredentials {
                    sh("buildscripts/scripts/build_qemu.sh");
                }
            }
        }
    }
}

return this;
