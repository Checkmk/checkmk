/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'

import { filterHelp, filterPlaceholder } from '@/maps/map/edit/filterText'
import type { TranslateFn } from '@/maps/utils/dropdownOptions'

// Fills the placeholders in, as the real translation does.
const t: TranslateFn = (message: string, args: Parameters<TranslateFn>[1] = {}) =>
  untranslated(
    Object.entries(args).reduce(
      (text, [key, value]) => text.replace(`%{${key}}`, String(value)),
      message
    )
  )

describe('filterText', () => {
  it('gives an example that names a host by the column of the hosts table', () => {
    expect(filterPlaceholder(t, false, 'host')).toBe('Filter: name ~ ^web')
    expect(filterHelp(t, 'host')).toBe(
      'One Filter: line per condition, for example Filter: name ~ ^web.'
    )
  })

  it('gives an example of a service by its description', () => {
    expect(filterPlaceholder(t, false, 'service')).toBe('Filter: description ~ ^CPU')
  })

  it('says what a grid without a filter adds instead of giving an example', () => {
    expect(filterPlaceholder(t, true, 'service')).toBe('Empty: all services')
  })
})
