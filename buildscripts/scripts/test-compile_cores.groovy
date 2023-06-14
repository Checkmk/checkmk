#!groovy

/// file: test-compile_cores.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "compile-neb-cmc-docker",
            cmd: "make compile-neb-cmc-docker",
        ]);

        test_jenkins_helper.analyse_issues("GCC", "");
    }
}

return this;
