#!groovy

/// file: test-python3-format.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-format-python",
            cmd: "make -C tests test-format-python",
            // output_file can not be used here as the venv and bazel setup
            // would be part of it as well, leading to unwanted output
        ]);

        // TODO this is not the correct parser to analyse the output
        test_jenkins_helper.analyse_issues("RUFFFORMAT", "ruff_check_and_format.txt");
    }
}

return this;
