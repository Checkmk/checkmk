#!groovy

/// file: update-architecture-documentation.groovy

def main() {
    dir("${checkout_dir}") {
        // Sphinx supports many different builders.
        // We have to use the same for creating new documentation and for
        // copying the documentation over.
        def sphinx_builder = "html";

        stage("Update") {
            inside_container() {
                sh("make -C doc/documentation ${sphinx_builder}");
            }
        }

        stage("Deploy") {
            withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {    // groovylint-disable DuplicateMapLiteral
                sh("""
                    scp -rs -o StrictHostKeyChecking=accept-new -i ${RELEASE_KEY} doc/documentation/_build/${sphinx_builder}/* ${DEV_DOCS_URL}/devdoc
                """);
            }
        }
    }
}

return this;
