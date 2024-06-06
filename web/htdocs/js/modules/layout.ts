/**
 * Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export function insertBefore(newElementId: string, targetElementId: string) {
    const newElement = document.getElementById(newElementId);
    const targetElement = document.getElementById(targetElementId);
    const parentElement = targetElement?.parentNode;
    if (
        parentElement &&
        newElement &&
        targetElement &&
        newElement !== parentElement
    ) {
        parentElement.insertBefore(newElement, targetElement);
    }
}
