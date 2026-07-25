#!groovy

/// file: build-wine-from-source.groovy

/// Build Wine from source and publish the tarball pinned by
/// @wine_linux_x86_64 to the CI binary-artifacts S3 bucket. This replaces the
/// third-party prebuilt Kron4ek binary with our own from-source build.
///
/// The Wine version and its source checksum are pinned in
/// third_party/wine/{create-archive,wine.sha256}. Bump them there in a commit,
/// then trigger this job manually to publish the new binaries and update the
/// sha256/URLs in MODULE.bazel.
///
/// The Wine build toolchain lives in a job-local image (third_party/wine/
/// Dockerfile) built inline as the first step, FROM the pinned AlmaLinux 8 base
/// (glibc floor 2.28). This keeps the shared build image lean and bakes the
/// toolchain (and the AWS CLI) at image-build time (inherently root), so the
/// build itself needs no root at runtime -- it just compiles into a tmpdir and
/// uploads to S3.
///
/// Credentials:
///     aws_ci_binary_artifacts_access_key -> AWS_ACCESS_KEY_ID
///     aws_ci_binary_artifacts_secret_key -> AWS_SECRET_ACCESS_KEY

void main() {
    def safe_branch_name = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy").safe_branch_name();
    def image_name = "wine-builder-checkmk-ci-${safe_branch_name}:latest";
    def base_image = resolve_docker_image_alias("IMAGE_ALMALINUX_8");
    def dockerfile = "${checkout_dir}/third_party/wine/Dockerfile";
    def docker_build_args = "--build-arg IMAGE_BASE=${base_image} -f ${dockerfile} ${checkout_dir}/third_party/wine";

    dir("${checkout_dir}") {
        docker.withRegistry(DOCKER_REGISTRY, "nexus") {
            def wine_image = docker.build(image_name, docker_build_args);
            withEnv([
                "AWS_DEFAULT_REGION=eu-central-1",
                "AWS_BUCKET_NAME=ci-binary-artifacts-710145618630-eu-central-1-an",
            ]) {
                withCredentials([
                    string(
                        credentialsId: 'aws_ci_binary_artifacts_access_key',
                        variable: 'AWS_ACCESS_KEY_ID'),
                    string(
                        credentialsId: 'aws_ci_binary_artifacts_secret_key',
                        variable: 'AWS_SECRET_ACCESS_KEY'),
                ]) {
                    wine_image.inside("-v ${checkout_dir}:/checkmk:ro") {
                        sh("buildscripts/scripts/build_wine.sh");
                    }
                }
            }
        }
    }
}

return this;
