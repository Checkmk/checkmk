#!groovy

/// file: test-python3-format.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-format-python",
            cmd: "make -C tests test-format-python-docker",
        ]);

        // TODO this is not the correct parser to analyse the output
        test_jenkins_helper.analyse_issues("CLANG", "");
    }
}

return this;
