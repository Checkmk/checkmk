#!groovy

/// file: test-python3-unit-all.groovy

def main() {
    inside_container(init: true, ulimit_nofile: "1024") {
        stage('run test-unit-all') {
            dir("${checkout_dir}") {
                sh("make -C tests test-unit-all");
            }
        }
    }
}

return this;
