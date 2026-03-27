py_binary(
    name = "update_confluence_vscode_page",
    srcs = ["scripts/update_confluence_vscode_page.py"],
)

genrule(
    name = "vsix",
    srcs = glob(
        [
            "src/**",
            "config/**",
            "icons/**",
            "docs/**",
            "scripts/**",
        ],
        exclude = [
            "node_modules/**",
            "out/**",
            "*.vsix",
        ],
    ) + [
        "package.json",
        "package-lock.json",
        "tsconfig.json",
        "esbuild.js",
        ".vscodeignore",
        "CLAUDE.md",
        "README.md",
        "icon.png",
        "icon.svg",
    ],
    outs = ["cmk-vscode.vsix"],
    cmd = """
        ROOT=$$PWD
        EXT_DIR=$$(dirname $(location package.json))
        cd "$$EXT_DIR"
        npm ci --ignore-scripts 2>&1
        node esbuild.js
        npx @vscode/vsce package --no-dependencies -o cmk-vscode.vsix 2>&1
        mkdir -p $$(dirname "$$ROOT/$@")
        cp cmk-vscode.vsix "$$ROOT/$@"
    """,
    local = True,
    tags = [
        "manual",
        "no-remote",
    ],
)
