#!groovy

/// file: test-javascript-lint.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-javascript-lint",
            cmd: "./scripts/run-in-docker.sh ./packages/cmk-frontend/run check-eslint --xml",
            output_file: "eslint.xml",
        ]);

        test_jenkins_helper.analyse_issues("ESLINT", "eslint.xml");
    }
}

return this;
