/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import * as cmk_site_overview from "./cmk_site_overview";

export class AlertOverview extends cmk_site_overview.SiteOverview {
    override ident() {
        return "alert_overview";
    }
}
