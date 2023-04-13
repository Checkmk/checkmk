// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

const path = require("path");
const RemoveEmptyScriptsPlugin = require("webpack-remove-empty-scripts");
const TerserPlugin = require("terser-webpack-plugin");
const webpack = require("webpack");

class WarningsToErrors {
    apply(compiler) {
        compiler.hooks.shouldEmit.tap("WarningsToErrors", compilation => {
            if (compilation.warnings.length > 0) {
                compilation.errors = compilation.errors.concat(compilation.warnings);
                compilation.warnings = [];
            }

            compilation.children.forEach(child => {
                if (child.warnings.length > 0) {
                    child.errors = child.errors.concat(child.warnings);
                    child.warnings = [];
                }
            });
        });
    }
}

module.exports = {
    mode: "production",
    devtool: "source-map",
    optimization: {
        minimizer: [
            new TerserPlugin({
                terserOptions: {
                    format: {
                        comments: false,
                    },
                },
                extractComments: false,
            }),
        ],
    },
    entry: {
        main: "./web/htdocs/js/index.ts",
        mobile: "./web/htdocs/js/mobile.ts",
        side: "./web/htdocs/js/side_index.ts",
        facelift: "./web/htdocs/themes/facelift/theme.scss",
        modern_dark: "./web/htdocs/themes/modern-dark/theme.scss",
        cma: "./web/htdocs/themes/facelift/cma_facelift.scss",
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
            path.resolve(__dirname, "web/htdocs/js/modules/nodevis"),
            path.resolve(__dirname, "enterprise/web/htdocs/js/modules"),
            path.resolve(__dirname, "enterprise/web/htdocs/js/modules/figures"),
            path.resolve(__dirname, "enterprise/web/htdocs/js/modules/ntop"),
            path.resolve(__dirname, "enterprise/web/htdocs/js/modules/license_usage"),
        ],
        // added this because otherwise it won't find any imported ts files inside of a js file
        extensions: [".ts", ".js"],
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
                            esModule: false,
                            sourceMap: false,
                        },
                    },
                    // 2. Some postprocessing of CSS definitions (see postcss.config.js)
                    // - add browser vendor prefixes https://github.com/postcss/autoprefixer
                    // - minifies CSS with https://github.com/cssnano/cssnano
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
        new RemoveEmptyScriptsPlugin(),
        new webpack.EnvironmentPlugin(["ENTERPRISE", "MANAGED"]),
        new WarningsToErrors(),
    ],
};

let babel_loader = {
    // Do not try to execute babel on all node_modules. But some d3 stuff seems to need it's help.
    exclude: /node_modules/,
    include: [
        path.resolve(__dirname, "web/htdocs/js"),
        path.resolve(__dirname, "enterprise/web/htdocs/js"),
        path.resolve(__dirname, "node_modules/d3"),
        path.resolve(__dirname, "node_modules/d3-flextree"),
        path.resolve(__dirname, "node_modules/d3-sankey"),
        path.resolve(__dirname, "node_modules/crossfilter2"),
        // Additional packages needed for D3js v6:
        path.resolve(__dirname, "node_modules/internmap"),
        path.resolve(__dirname, "node_modules/delaunator"),
    ],
    use: {
        loader: "babel-loader",
        options: {
            presets: ["@babel/typescript"],
            plugins: [
                "@babel/plugin-transform-parameters",
                "@babel/proposal-class-properties",
                "@babel/proposal-object-rest-spread",
            ],
        },
    },
};

if (process.env.WEBPACK_MODE === "quick") {
    babel_loader["test"] = /\.ts?$/;
} else {
    babel_loader["test"] = /\.(ts|js)?$/;
    babel_loader["use"]["options"]["presets"].unshift([
        "@babel/preset-env",
        {
            //debug: true,
            // This adds polyfills when needed. Requires core-js dependency.
            // See https://babeljs.io/docs/en/babel-preset-env#usebuiltins
            useBuiltIns: "usage",
            corejs: 3,
        },
    ]);
}

module.exports.module.rules.unshift(babel_loader);
