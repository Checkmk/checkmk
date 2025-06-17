#!groovy

/// file: test-python3-unit-all.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-unit-all",
            cmd: "make -C tests test-unit-all",
        ]);
    }
}

return this;
