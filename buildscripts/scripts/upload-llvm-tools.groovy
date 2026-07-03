#!groovy

/// file: upload-llvm-tools.groovy

/// Extract clang-tidy and clang-format from the upstream LLVM release and
/// upload them, standalone, to the CI binary-artifacts S3 bucket. This lets
/// the build fetch just the two binaries instead of the full LLVM archive.
///
/// The LLVM version and its checksum are pinned in
/// buildscripts/scripts/extract_llvm.sh. Bump them there in a commit, then
/// trigger this job manually to publish the new binaries.
///
/// Credentials (not yet registered in Jenkins):
///     aws_ci_binary_artifacts_access_key -> AWS_ACCESS_KEY_ID
///     aws_ci_binary_artifacts_secret_key -> AWS_SECRET_ACCESS_KEY

void main() {
    dir("${checkout_dir}") {
        inside_container() {
            sh("buildscripts/infrastructure/build-nodes/scripts/install-aws-cli.sh");
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
                    sh("buildscripts/scripts/extract_llvm.sh");
                }
            }
        }
    }
}

return this;
