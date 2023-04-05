#!groovy

/// file: test-typescript-types.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            sh("make -C tests test-typescript-types-docker");
        }
    }
}

return this;
