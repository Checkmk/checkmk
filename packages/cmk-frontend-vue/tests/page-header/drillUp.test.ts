/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { drillUpTarget } from '@/page-header/drillUp'

const ORIGIN = 'https://monitoring.example'
const DASHBOARD = `${ORIGIN}/site/check_mk/dashboard.py?name=main`
const PAGE = `${ORIGIN}/site/check_mk/view.py?view_name=allhosts`

describe('drillUpTarget', () => {
  it('goes back in the history of a tab that has one', () => {
    expect(drillUpTarget(2, DASHBOARD, PAGE)).toBe('history')
  })

  it('opens the referrer in a tab without history', () => {
    expect(drillUpTarget(1, DASHBOARD, PAGE)).toEqual(new URL(DASHBOARD))
  })

  it('loses the way back without history and referrer', () => {
    expect(drillUpTarget(1, '', PAGE)).toBeNull()
  })

  it('opens no page of another site', () => {
    expect(drillUpTarget(1, 'https://evil.example/', PAGE)).toBeNull()
  })

  it('runs no script a referrer named', () => {
    expect(drillUpTarget(1, 'javascript:alert(1)', PAGE)).toBeNull()
  })
})
