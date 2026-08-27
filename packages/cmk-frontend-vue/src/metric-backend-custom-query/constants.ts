/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

export function metricBackendMacroHelp(): TranslatedString {
  const { _t } = usei18n()
  return _t(
    'Available macros: <tt>$SERIES_ID$</tt>, <tt>$METRIC_NAME$</tt>, <tt>$RESOURCE_ATTR.&lt;key&gt;$</tt>, <tt>$SCOPE_ATTR.&lt;key&gt;$</tt>, <tt>$DATA_POINT_ATTR.&lt;key&gt;$</tt>'
  )
}
