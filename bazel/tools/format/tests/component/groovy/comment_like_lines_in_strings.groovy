node {
        // Aligned with the line after it
    sh("""
        bazel run \\
            --flag \\
            //some/package:target
        echo done
    """)
    print($/
          // not a comment
    /$)
}
