#!groovy

/// file: test-iwyu.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-iwyu-docker",
            cmd: "make -C tests test-iwyu-docker",
        ]);

        test_jenkins_helper.analyse_issues("CLANG", "");
    }
}

return this;
