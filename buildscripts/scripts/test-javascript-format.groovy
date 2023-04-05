#!groovy

/// file: test-javascript-format.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            sh("make -C tests test-format-js-docker");
        }
    }
}

return this;
