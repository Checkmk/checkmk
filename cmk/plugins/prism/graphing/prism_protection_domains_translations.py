# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1.translations import PassiveCheck, RenameToAndScaleBy, Translation

translation_prism_protection_domains = Translation(
    name="prism_protection_domains",
    check_commands=[
        PassiveCheck("prism_protection_domains"),
    ],
    # Scale by 1000 because the historical metrics were stored as kBps; the
    # new metrics are emitted in B/s, so existing RRDs need scaling on read.
    translations={
        "pd_bandwidthtx": RenameToAndScaleBy("pd_bandwidth_rx", 1000),
        "pd_bandwidthrx": RenameToAndScaleBy("pd_bandwidth_tx", 1000),
    },
)
