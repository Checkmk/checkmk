/**
 * Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {AbstractLink, link_type_class_registry} from "nodevis/link_utils";

export class DefaultLinkNode extends AbstractLink {
    static override class_name = "default";
}

link_type_class_registry.register(DefaultLinkNode);
