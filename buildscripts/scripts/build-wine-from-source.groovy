#!groovy

/// file: build-wine-from-source.groovy

/// Build Wine from source and publish the tarball pinned by
/// @wine_linux_x86_64 to the Nexus upstream-archives mirror. This replaces the
/// third-party prebuilt Kron4ek binary with our own from-source build.
///
/// TODO: also publish to the public CI binary-artifacts S3 bucket once its
/// aws_ci_binary_artifacts_* credentials are registered in Jenkins.
///
/// The Wine version and its source checksum are pinned in
/// third_party/wine/{create-archive,wine.sha256}. Bump them there in a commit,
/// then trigger this job manually to publish the new binaries and update the
/// sha256/URLs in MODULE.bazel.
///
/// The Wine build toolchain lives in a job-local image (third_party/wine/
/// Dockerfile) built inline as the first step, FROM the pinned AlmaLinux 8 base
/// (glibc floor 2.28). This keeps the shared build image lean and bakes the
/// toolchain at image-build time (inherently root), so the build itself needs
/// no root at runtime -- it just compiles into a tmpdir and uploads to Nexus.
///
/// Credentials:
///     nexus -> NEXUS_USERNAME / NEXUS_PASSWORD

void main() {
    def safe_branch_name = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy").safe_branch_name();
    def image_name = "wine-builder-checkmk-ci-${safe_branch_name}:latest";
    def base_image = resolve_docker_image_alias("IMAGE_ALMALINUX_8");
    def dockerfile = "${checkout_dir}/third_party/wine/Dockerfile";
    def docker_build_args = "--build-arg IMAGE_BASE=${base_image} -f ${dockerfile} ${checkout_dir}/third_party/wine";

    dir("${checkout_dir}") {
        docker.withRegistry(DOCKER_REGISTRY, "nexus") {
            def wine_image = docker.build(image_name, docker_build_args);
            withCredentials([
                usernamePassword(
                    credentialsId: 'nexus',
                    passwordVariable: 'NEXUS_PASSWORD',
                    usernameVariable: 'NEXUS_USERNAME'),
            ]) {
                wine_image.inside("-v ${checkout_dir}:/checkmk:ro") {
                    sh("buildscripts/scripts/build_wine.sh");
                }
            }
        }
    }
}

return this;
