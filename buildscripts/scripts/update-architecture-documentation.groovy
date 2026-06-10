#!groovy

/// file: update-architecture-documentation.groovy

void main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def safe_branch_name = versioning.safe_branch_name();

    dir(checkout_dir) {
        stage("Build & Deploy") {
            def container_name = "testing-ubuntu-2204-checkmk-${safe_branch_name.replace('.', '-')}";

            container(container_name) {
                sh("bazel build //doc/documentation")

                // groovylint-disable-next-line DuplicateMapLiteral
                withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
                    // The chmod u+w is required:  Bazel creates read-only files, so `scp`
                    // uploads them as read-only.  The next run then fails to overwrite them.
                    sh("""
                        chmod -R u+w bazel-bin/doc/documentation/documentation_html/
                        scp -rs -o StrictHostKeyChecking=accept-new -i ${RELEASE_KEY} \
                        bazel-bin/doc/documentation/documentation_html/* ${DEV_DOCS_URL}/devdoc
                    """);
                }
            }
        }
    }
}

return this;
