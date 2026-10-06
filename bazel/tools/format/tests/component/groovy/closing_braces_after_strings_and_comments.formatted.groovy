node {
    def packages = sh(returnStdout: true,
                      script: """
        find . -name '*.deb'
    """).trim().split("\n").each { pkg ->
        echo("Found ${pkg}")
    }
    withEnv(["""A=
b"""]) {
        print("a")
    }
    foo(a,
        b /* the
    */) {
        print("b")
    }
    print("""
        ${ foo("""
            x
        """) { y ->
            bar(y)
        }
        }
    """)
}
