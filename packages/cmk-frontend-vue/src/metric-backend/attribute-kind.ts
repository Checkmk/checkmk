/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AttributeKind } from 'cmk-shared-typing/typescript/attribute_filter'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

// Wire type, re-exported so the whole metric-backend UI shares one name for it.
export type { AttributeKind }

// Dropdown and suggestion-section order, shared by both metric-backend widgets.
export const ATTRIBUTE_KIND_ORDER: AttributeKind[] = ['resource', 'scope', 'data_point']

// Built at call time, not module load, because i18n is not yet set up then.
export function attributeKindLabel(attributeKind: AttributeKind): TranslatedString {
  const { _t } = usei18n()
  const labels: Record<AttributeKind, TranslatedString> = {
    resource: _t('Resource'),
    scope: _t('Scope'),
    data_point: _t('Data point')
  }
  return labels[attributeKind]
}
