#!groovy

/// file: test-python3-code-quality.groovy

def main() {
    inside_container(
        init: true,
        ulimit_nofile: 1024,
    ) {
        stage('test python3 code quality') {
            dir("${checkout_dir}") {
                sh("make -C tests test-code-quality");
            }
        }
    }
}

return this;
