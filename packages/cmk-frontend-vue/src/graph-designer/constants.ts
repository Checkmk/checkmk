/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from '@/lib/i18n'

const { _t } = usei18n()

export const METRIC_BACKEND_MACRO_HELP = _t(
  'Available macros: <tt>$SERIES_ID$</tt>, <tt>$METRIC_NAME$</tt>, <tt>$RESOURCE_ATTR.&lt;key&gt;$</tt>, <tt>$SCOPE_ATTR.&lt;key&gt;$</tt>, <tt>$DATA_POINT_ATTR.&lt;key&gt;$</tt>'
)
