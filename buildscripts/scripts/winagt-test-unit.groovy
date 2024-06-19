#!groovy

/// file: winagt-test-unit.groovy

def main() {
    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");

    dir("${checkout_dir}") {
        windows.build(
            TARGET: 'test_unit'
        );
    }
}

return this;
