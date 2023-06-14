#!groovy

/// file: test-css-format.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-javascript-lint",
            cmd: "make -C tests test-format-css-docker",
            output_file: "css-prettier.txt"
        ]);

        test_jenkins_helper.analyse_issues("CSSFORMAT", "css-prettier.txt");
    }
}

return this;
