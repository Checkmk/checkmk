#!groovy

/// file: test-agent-controller.groovy

def main() {
    dir("${checkout_dir}") {
        docker_reference_image().inside() {
            stage('Compile & Test Agent Controller') {
                sh("packages/cmk-agent-ctl/run --setup-environment --clean --all");
            }
        }
    }
}

return this;
