/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

const path = require("path");
const RemoveEmptyScriptsPlugin = require("webpack-remove-empty-scripts");
const TerserPlugin = require("terser-webpack-plugin");
const webpack = require("webpack");
const FileManagerPlugin = require("filemanager-webpack-plugin");

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
        main: "./src/js/index.ts",
        mobile: "./src/js/mobile.ts",
        tracking_entry: "./src/js/tracking_entry.ts",
        side: "./src/js/side_index.ts",
        fonts_lato: "./src/themes/facelift/fonts_inter.scss",
        facelift: "./src/themes/facelift/theme.scss",
        modern_dark: "./src/themes/modern-dark/theme.scss",
    },
    output: {
        filename: "js/[name]_min.js",
        // Keep this until we have cleaned up our JS files to work as modules and changed all call sites
        // from HTML code to work with the modules. Until then we need to keep the old behaviour of loading
        // all JS code in the global namespace
        libraryTarget: "window",
        libraryExport: "cmk_export",
        clean: true,
    },
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "src/js/"),
        },
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
                            name: "themes/[1]/[2].css",
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
                            sassOptions: {
                                // Hand over build options from webpack to SASS
                                includePaths: ["node_modules"],
                                // dart-sass supports "expanded" and "compressed":
                                // https://github.com/sass/dart-sass#javascript-api
                                outputStyle: "expanded",
                                precision: 10,
                                // https://sass-lang.com/blog/import-is-deprecated/
                                // we have to adjust our themes implementation first
                                // CMK-20712
                                silenceDeprecations: ["import"],
                            },
                        },
                    },
                ],
            },
        ],
    },
    plugins: [
        new RemoveEmptyScriptsPlugin(),
        new WarningsToErrors(),
        new FileManagerPlugin({
            events: {
                onEnd: {
                    copy: [
                        {source: "src/images", destination: "dist/images"},
                        {source: "src/openapi", destination: "dist/openapi"},
                        {source: "src/jquery", destination: "dist/jquery"},
                        {source: "src/css", destination: "dist/css"},
                        {source: "src/sounds", destination: "dist/sounds"},
                        {
                            source: "src/themes/facelift/images",
                            destination: "dist/themes/facelift/images",
                        },
                        {
                            source: "src/themes/facelift/fonts",
                            destination: "dist/themes/facelift/fonts",
                        },
                        {
                            source: "src/themes/facelift/theme.json",
                            destination: "dist/themes/facelift/theme.json",
                        },
                        {
                            source: "src/themes/modern-dark/images",
                            destination: "dist/themes/modern-dark/images",
                        },
                        {
                            source: "src/themes/modern-dark/theme.json",
                            destination: "dist/themes/modern-dark/theme.json",
                        },
                    ],
                },
            },
        }),
    ],
};

let babel_loader = {
    // Do not try to execute babel on all node_modules. But some d3 stuff seems to need it's help.
    exclude: /node_modules/,
    include: [
        path.resolve(__dirname, "src/js"),
        path.resolve(__dirname, "enterprise/src/js"),
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

module.exports.module.rules.unshift(babel_loader);
