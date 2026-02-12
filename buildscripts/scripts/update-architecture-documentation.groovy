#!groovy

/// file: update-architecture-documentation.groovy

void main() {
    def helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def safe_branch_name = versioning.safe_branch_name();

    dir(checkout_dir) {
        // Sphinx supports many different builders.
        // We have to use the same for creating new documentation and for
        // copying the documentation over.
        def sphinx_builder = "html";

        stage("Create") {
            def container_name = "testing-ubuntu-2204-checkmk-${safe_branch_name.replace('.', '-')}";

            def lock_label = "bzl_lock_${env.NODE_NAME.split('\\.')[0].split('-')[-1]}";
            if (kubernetes_inherit_from != "UNSET") {
                lock_label = "bzl_lock_k8s";
            }
            lock(label: lock_label, quantity: 1, resource : null) {
                helper.execute_test([
                    name       : "documentation",
                    cmd        : "make -C doc/documentation ${sphinx_builder}",
                    container_name: container_name,
                ]);
            }
        }

        stage("Deploy") {
            withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {    // groovylint-disable DuplicateMapLiteral
                sh("""
                    scp -rs -o StrictHostKeyChecking=accept-new -i ${RELEASE_KEY} \
                    doc/documentation/_build/${sphinx_builder}/* ${DEV_DOCS_URL}/devdoc
                """);
            }
        }
    }
}

return this;
