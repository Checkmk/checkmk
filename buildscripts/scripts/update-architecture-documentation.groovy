#!groovy

/// file: update-architecture-documentation.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Update") {
            inside_container() {
                sh("make -C doc/documentation htmlhelp");
            }
            stage("Stash") {
                stash(
                    name: "htmlhelp",
                    includes: "doc/documentation/_build/htmlhelp/**"
                );
            }
        }

        // The pages produced by the job are served by the web server on our CI
        // master node. Extract the results there to make it available to the
        // web server.
        node("Master_DoNotUse") {
            unstash("htmlhelp");
        }
    }
}

return this;
