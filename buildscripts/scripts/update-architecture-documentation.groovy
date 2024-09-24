#!groovy

/// file: update-architecture-documentation.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Update") {
            inside_container() {
                sh("make -C doc/documentation htmlhelp");
            }
        }

        stage("Deploy") {
            withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {    // groovylint-disable DuplicateMapLiteral
                sh("""
                    scp -rs -o StrictHostKeyChecking=accept-new -i ${RELEASE_KEY} doc/documentation/_build/htmlhelp ${DEV_DOCS_URL}/devdoc
                """);
            }
        }
    }
}

return this;
