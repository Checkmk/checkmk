/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// This is for Jest/TypeScript. Without this, Jest won't understand TypeScript.
module.exports = {
    presets: [["@babel/preset-env", {targets: {node: "current"}}], "@babel/preset-typescript"],
};
