#!groovy

/// file: test-css-format.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            sh("make -C tests test-format-css-docker");
        }
    }
}

return this;
