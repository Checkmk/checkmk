#!groovy

/// file: test-javascript-build.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            sh("make -C tests test-build-js-docker");
        }
    }
}

return this;
