#!groovy

/// file: test-clang_tidy.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-tidy-docker",
            cmd: "echo nothing to do REMOVE ME",
        ]);

        test_jenkins_helper.analyse_issues("CLANG", "");
    }
}

return this;
