/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { widgetTypeToSelectorMatcher } from '@/dashboard/components/WizardSelector/utils'

describe('widgetTypeToSelectorMatcher', () => {
  it('edits a custom graph widget in the link-existing custom graph wizard', () => {
    const contentType = 'custom_graph'

    const wizardKey = widgetTypeToSelectorMatcher(contentType)

    expect(wizardKey).toBe('link_custom_graph')
  })
})
