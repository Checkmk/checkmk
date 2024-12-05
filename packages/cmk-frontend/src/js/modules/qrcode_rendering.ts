/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import QRCode from "qrcode";

export async function render_qr_code(
    qr_div: HTMLElement,
    options: {[key: string]: string},
) {
    const canvas = document.createElement("canvas");
    const data = options.qrcode;
    qr_div.appendChild(canvas);
    QRCode.toCanvas(canvas, data!, function (error) {
        if (error) {
            console.error(error);
            qr_div.appendChild(
                document.createTextNode(
                    `Could not render qrcode because an internal error occurred: ${error}. The data shown in the qrcode would be: ${data}.`,
                ),
            );
        }
    });
}
