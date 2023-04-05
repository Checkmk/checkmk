#!groovy

/// file: test-javascript-lint.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            sh("make -C tests test-lint-js-docker");
        }
    }
}

return this;
