node {
    print("""
        ${params.ITEMS.collect({ item ->
            if (item) {
                return item
                }
            return "none"
        }).join(", ")}
        ${ params.NAMES.collect { name ->
            name
              }
        }
        ${
            params.A
                    }
    """)
}
