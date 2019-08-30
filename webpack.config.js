const path = require("path");
const FixStyleOnlyEntriesPlugin = require("webpack-fix-style-only-entries");
const webpack = require("webpack");

module.exports = {
    mode: "production",
    devtool: "source-map",
    entry: {
        main: "./web/htdocs/js/index.js",
        mobile: "./web/htdocs/js/mobile.js",
        side: "./web/htdocs/js/side_index.js",
        themes: [
            "./web/htdocs/themes/facelift/theme.scss",
            "./web/htdocs/themes/classic/theme.scss",
            "./web/htdocs/themes/modern-dark/theme.scss",
        ],
    },
    output: {
        path: path.resolve(__dirname, "web/htdocs/js"),
        filename: "[name]_min.js",
        publicPath: "js",
        // Keep this until we have cleaned up our JS files to work as modules and changed all call sites
        // from HTML code to work with the modules. Until then we need to keep the old behaviour of loading
        // all JS code in the global namespace
        libraryTarget: "window",
        libraryExport: "default"
    },
    resolve: {
        modules: [
            "node_modules",
            path.resolve(__dirname, "web/htdocs/js/modules"),
            path.resolve(__dirname, "web/htdocs/js/modules/node_visualization"),
            path.resolve(__dirname, "enterprise/web/htdocs/js/modules"),
        ]
    },
    module: {
        rules: [
            // needed for theme CSS files
            {
                test: /\.scss$/,
                use: [
                    // 5. Write to theme specific file
                    {
                        loader: "file-loader",
                        options: {
                            regExp: /\/([a-z0-9_-]+)\/([a-z0-9_-]+)\.scss$/,
                            name: "../themes/[1]/[2].css"
                        }
                    },
                    // 4. Extract CSS definitions from JS wrapped CSS
                    {
                        loader: "extract-loader"
                    },
                    // 3. Interpret and resolve @import / url()
                    {
                        loader: "css-loader",
                        options: {
                            url: false,
                            importLoaders: 2
                        },
                    },
                    // 2. Some postprocessing of CSS definitions (see postcss.config.js)
                    // - add browser vendor prefixes https://github.com/postcss/autoprefixer
                    // - minifies CSS with https://github.com/jakubpawlowicz/clean-css
                    {
                        loader: "postcss-loader"
                    },
                    // 1. Transform sass definitions into CSS
                    {
                        loader: "sass-loader",
                        options: {
                            prependData: "$ENTERPRISE: " + process.env.ENTERPRISE + ";\n"
                                + "$MANAGED: " + process.env.MANAGED + ";",
                            sassOptions: {
                                // Hand over build options from webpack to SASS
                                "includePaths": ["node_modules"],
                                // See https://github.com/sass/node-sass/blob/master/README.md#options
                                outputStyle: "expanded",
                                precision: 10
                            }
                        }
                    }
                ]
            },
        ]
    },
    plugins: [
        new FixStyleOnlyEntriesPlugin(),
        new webpack.EnvironmentPlugin(["ENTERPRISE", "MANAGED"]),
    ]
};


if (process.env.NO_BABEL_LOADER == undefined) {
    let babel_loader = {
        test: /\.js$/,
        exclude: /node_modules/,
        use: {
            loader: "babel-loader",
            options: {
                presets: ["@babel/preset-env"],
            }
        }
    };
    module.exports.module.rules.unshift(babel_loader);
}


