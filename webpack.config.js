var path = require('path');

module.exports = {
    mode: 'development',
    entry: './web/htdocs/js/index.js',
    output: {
        path: path.resolve(__dirname, 'web/htdocs/js'),
        filename: 'main.js',
        publicPath: 'js'
    },
    resolve: {
        modules: [
            "node_modules",
            path.resolve(__dirname, "web/htdocs/js")
        ]
    }
};
