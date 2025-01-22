/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export async function insert_before(
    elementToMove: HTMLElement,
    options: {[key: string]: string},
) {
    if (!("targetElementId" in options)) {
        throw new Error("Missing required option 'targetElementId'");
    }
    const targetElementId = options["targetElementId"];
    const targetElement = document.getElementById(targetElementId);
    const parentElement = targetElement?.parentNode;
    if (
        parentElement &&
        elementToMove &&
        targetElement &&
        elementToMove !== parentElement
    ) {
        parentElement.insertBefore(elementToMove, targetElement);
    }
}
