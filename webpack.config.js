var path = require("path");

module.exports = {
    mode: "production",
    entry: {
        main: "./web/htdocs/js/index.js",
        mobile: "./web/htdocs/js/mobile.js"
    },
    output: {
        path: path.resolve(__dirname, "web/htdocs/js"),
        filename: "[name]_min.js",
        publicPath: "js",
        // Keep this until we have cleaned up our JS files to work as modules and changed all call sites
        // from HTML code to work with the modules. Until then we need to keep the old behaviour of loading
        // all JS code in the global namespace
        libraryTarget: "window",
    },
    resolve: {
        modules: [
            "node_modules",
            path.resolve(__dirname, "web/htdocs/js/modules"),
            path.resolve(__dirname, "web/htdocs/js"),
            path.resolve(__dirname, "enterprise/web/htdocs/js")
        ]
    },
    module: {
        rules: [
            {
                test: /\.(js|jsx)$/,
                exclude: /node_modules/,
                use: {
                    loader: "babel-loader",
                    options: {
                        presets: ["@babel/preset-env"]
                    }
                }
            }
        ]
    }
};
