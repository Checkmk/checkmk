#!groovy

/// file: test-bazel-format.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            sh("make -C tests test-format-bazel-docker");
        }
    }
}

return this;
