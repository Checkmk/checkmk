#!groovy

/// file: test-python3-pylint.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name       : "test-pylint",
            cmd        : "PYLINT_ARGS=--output-format=parseable make -C tests test-pylint",
            output_file: "pylint.txt",
        ]);
        test_jenkins_helper.analyse_issues("PYLINT", "pylint.txt");
    }
}

return this;
