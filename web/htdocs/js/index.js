require('script-loader!./checkmk.js');
require('script-loader!./dashboard.js');
require('script-loader!./colorpicker.js');
require('script-loader!./prediction.js');
require('script-loader!./search.js');
require('script-loader!./sidebar.js');
require('script-loader!./wato.js');

// TODO: Find a better solution for this CEE specific include
try {
    require('script-loader!../../../enterprise/web/htdocs/js/graphs.js');
} catch(e) {}
