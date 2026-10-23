/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// Every autocompleter goes through the REST API. `Autocompleter.fetch_method`
// still exists because the plugin API in cmk-plugin-apis declares it, and the
// legacy frontend still calls ajax_vs_autocomplete.py for its own select2
// widgets. Neither reaches this code, so the flag is ignored here rather than
// branched on: a producer that still says `ajax_vs_autocomplete` gets the REST
// call it would have wanted, instead of an error.
export { fetchSuggestions } from './autocompleters/rest'
