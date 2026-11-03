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

function embeddedView(dashboardUrl: string): string {
  const variables = new URLSearchParams({
    dashboard_name: 'main',
    drill_down_source_url: dashboardUrl
  })
  return `${ORIGIN}/site/check_mk/widget_iframe_view.py?${variables.toString()}`
}

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

  it('opens the dashboard around the embedded view whose column link opened the tab', () => {
    expect(drillUpTarget(1, embeddedView(DASHBOARD), PAGE)).toEqual(new URL(DASHBOARD))
  })

  it('loses the way back from an embedded view that names no dashboard', () => {
    expect(drillUpTarget(1, `${ORIGIN}/site/check_mk/widget_iframe_view.py`, PAGE)).toBeNull()
  })

  it('opens no page of another site an embedded view names', () => {
    expect(drillUpTarget(1, embeddedView('https://evil.example/'), PAGE)).toBeNull()
  })
})
