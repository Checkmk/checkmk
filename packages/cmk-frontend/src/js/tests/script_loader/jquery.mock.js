/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Stands in for webpack's script-loader under jest. It runs a script in the global
// scope the way a <script> tag does, so jQuery becomes window.$ and window.jQuery.
import jquery from "jquery";

window.$ = window.jQuery = jquery;
