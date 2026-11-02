/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Stands in for webpack's script-loader under jest: runs the shipped jQuery Mobile
// in the global scope, the way a <script> tag does, so it initializes (and fires
// mobileinit) at the point the page requires it.
import {readFileSync} from "fs";
import {join} from "path";

const source = readFileSync(join(__dirname, "../../../jquery/jquery.mobile-1.4.5.min.js"), "utf8");

(0, eval)(source);
