#!groovy

/// file: test-bazel-lint.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-bazel-lint",
            cmd: "make -C tests test-lint-bazel",
            output_file: "bazel-lint.txt",
        ]);

        test_jenkins_helper.analyse_issues("BAZELLINT", "bazel-lint.txt");
    }
}

return this;
