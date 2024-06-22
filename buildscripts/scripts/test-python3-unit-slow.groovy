#!groovy

/// file: test-python3-unit-slow.groovy

def main() {
    inside_container(
        init: true,
        ulimit_nofile: 1024,
    ) {
        stage('run test-unit-slow') {
            dir("${checkout_dir}") {
                sh("make -C tests test-unit-slow");
            }
        }
    }
}

return this;
