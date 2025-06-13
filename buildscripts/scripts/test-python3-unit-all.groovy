#!groovy

/// file: test-python3-unit-all.groovy

def main() {
    stage('run test-unit-all') {
        dir("${checkout_dir}") {
            withCredentials([
            ]) {
                sh("make -C tests test-unit-all");
            }
        }
    }
}

return this;
