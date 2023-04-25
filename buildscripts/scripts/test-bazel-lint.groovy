#!groovy

/// file: test-bazel-lint.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            sh("make -C tests test-lint-bazel-docker");
        }
    }
}

return this;