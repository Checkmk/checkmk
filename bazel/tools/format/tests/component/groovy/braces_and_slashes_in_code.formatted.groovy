node {
    if (params.A) {
        print("a")  // } closes nothing
    }
    withEnv(["""MESSAGE="hello""""]) {
        print("b")
    }
    def ratio = (params.A
        / params.B)
    if (ratio) {
        sh("cp a/b c")
    }
}
