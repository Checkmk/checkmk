#!groovy

/// file: frontend-demo.groovy

void main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def safe_branch_name = versioning.safe_branch_name();
    def output_artifacts = "bazel-bin/packages/cmk-frontend-vue/demo/dist";

    // The branch-specific part must not contain dots (e.g. 2.5.0),
    // because this results in an invalid branch name.
    // The pod templates uses - instead.
    def container_safe_branch_name = safe_branch_name.replace(".", "-");

    dir("${checkout_dir}") {
        container("ubuntu-2404-${container_safe_branch_name}-latest") {
            stage("Build") {
                sh("""
                    bazel build @@//packages/cmk-frontend-vue:dist-demo-hosted
                """);
            // all files are "-r-xr-xr-x" aka "555"
            }

            stage("Deploy") {
                // groovylint-disable-next-line DuplicateMapLiteral
                withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
                    sh("""
                        chmod -R 755 ${output_artifacts}/

                        scp -rs -o StrictHostKeyChecking=accept-new -i ${RELEASE_KEY} \
                        ${output_artifacts}/* ${DEV_DOCS_URL}/frontend-demo
                    """);
                }
            }
        }
    }
}

return this;
