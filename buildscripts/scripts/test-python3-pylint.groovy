#!groovy

/// file: test-python3-pylint.groovy

void main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name       : "test-astrein",
            cmd        : "make -C tests test-astrein",
            output_file: "astrein.txt",
        ]);
        test_jenkins_helper.analyse_issues("GCC", "astrein.txt");
    }
}

return this;
