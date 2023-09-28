#!groovy

/// file: test-javascript-format.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-javascript-format",
            cmd: "make -C tests test-format-js-docker",
            output_file: "js-prettier.txt"
        ]);

        test_jenkins_helper.analyse_issues("TSJSFORMAT", "js-prettier.txt");
    }
}

return this;
