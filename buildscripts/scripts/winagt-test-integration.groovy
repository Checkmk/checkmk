#!groovy

/// file: winagt-test-integration.groovy

def main() {
    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");

    stage("Run 'test_integration'") {
        dir("${checkout_dir}") {
            windows.build(
                TARGET: 'test_integration'
            )
        }
    }
}

return this;
