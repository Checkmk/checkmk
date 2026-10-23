node {
    writeFile(file: "config.json", text: """{
    "retries": 3
}
""")
    writeFile(file: "settings.json", text: '''{
    "debug": false
}
''')
    if (params.VERBOSE) {
        print("verbose")
            }
}
