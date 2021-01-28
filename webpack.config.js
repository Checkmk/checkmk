// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

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
            "./web/htdocs/themes/facelift/cma_facelift.scss",
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
        libraryExport: "cmk_export",
    },
    resolve: {
        modules: [
            "node_modules",
            path.resolve(__dirname, "web/htdocs/js/modules"),
            path.resolve(__dirname, "web/htdocs/js/modules/figures"),
            path.resolve(__dirname, "web/htdocs/js/modules/node_visualization"),
            path.resolve(__dirname, "enterprise/web/htdocs/js/modules"),
            path.resolve(__dirname, "enterprise/web/htdocs/js/modules/ntop"),
        ],
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
                            name: "../themes/[1]/[2].css",
                        },
                    },
                    // 4. Extract CSS definitions from JS wrapped CSS
                    {
                        loader: "extract-loader",
                    },
                    // 3. Interpret and resolve @import / url()
                    {
                        loader: "css-loader",
                        options: {
                            url: false,
                            importLoaders: 2,
                        },
                    },
                    // 2. Some postprocessing of CSS definitions (see postcss.config.js)
                    // - add browser vendor prefixes https://github.com/postcss/autoprefixer
                    // - minifies CSS with https://github.com/jakubpawlowicz/clean-css
                    {
                        loader: "postcss-loader",
                    },
                    // 1. Transform sass definitions into CSS
                    {
                        loader: "sass-loader",
                        options: {
                            additionalData:
                                "$ENTERPRISE: " +
                                process.env.ENTERPRISE +
                                ";\n" +
                                "$MANAGED: " +
                                process.env.MANAGED +
                                ";",
                            sassOptions: {
                                // Hand over build options from webpack to SASS
                                includePaths: ["node_modules"],
                                // dart-sass supports "expanded" and "compressed":
                                // https://github.com/sass/dart-sass#javascript-api
                                outputStyle: "expanded",
                                precision: 10,
                            },
                        },
                    },
                ],
            },
        ],
    },
    plugins: [
        new FixStyleOnlyEntriesPlugin(),
        new webpack.EnvironmentPlugin(["ENTERPRISE", "MANAGED"]),
    ],
};

if (process.env.WEBPACK_MODE === "quick") {
    console.log(
        "not using Babel in Webpack mode '" +
            process.env.WEBPACK_MODE +
            "', let's hope you know what your're doing..."
    );
} else {
    console.log("using Babel in Webpack mode '" + process.env.WEBPACK_MODE + "'");
    let babel_loader = {
        test: /\.js$/,
        // Do not try to execute babel on all node_modules. But some d3 stuff seems to need it's help.
        include: [
            path.resolve(__dirname, "web/htdocs/js"),
            path.resolve(__dirname, "enterprise/web/htdocs/js/modules"),
            path.resolve(__dirname, "node_modules/d3"),
            path.resolve(__dirname, "node_modules/d3-flextree"),
            path.resolve(__dirname, "node_modules/d3-sankey"),
            path.resolve(__dirname, "node_modules/crossfilter2"),
        ],
        use: {
            loader: "babel-loader",
            options: {
                presets: [
                    [
                        "@babel/preset-env",
                        {
                            //debug: true,
                            // This adds polyfills when needed. Requires core-js dependency.
                            // See https://babeljs.io/docs/en/babel-preset-env#usebuiltins
                            useBuiltIns: "usage",
                            corejs: 3,
                        },
                    ],
                ],
                plugins: ["@babel/plugin-transform-parameters"],
            },
        },
    };
    module.exports.module.rules.unshift(babel_loader);
}
