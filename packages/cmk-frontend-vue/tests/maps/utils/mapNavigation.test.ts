/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'

import {
  buildServiceStateViewUrl,
  hostStateOn,
  openUrl,
  svcStateOn
} from '@/maps/utils/mapNavigation'

describe('svcStateOn / hostStateOn', () => {
  it('maps monitoring states to Checkmk filter checkboxes', () => {
    expect(svcStateOn('OK')).toBe('st0')
    expect(svcStateOn('WARNING')).toBe('st1')
    expect(svcStateOn('CRITICAL')).toBe('st2')
    expect(svcStateOn('UNKNOWN')).toBe('st3')
    expect(svcStateOn('PENDING')).toBe('stp')
    expect(hostStateOn('UP')).toBe('hst0')
    expect(hostStateOn('DOWN')).toBe('hst1')
    expect(hostStateOn('UNREACHABLE')).toBe('hst2')
  })
})

describe('buildServiceStateViewUrl', () => {
  const cmk = 'http://h/SITE/check_mk/'

  // The link is wrapped in index.py?start_url=… to keep Checkmk's chrome; the
  // real view.py target lives (relative) inside the decoded start_url param.
  function innerView(url: string | null): string {
    expect(url).toContain('/SITE/check_mk/index.py')
    return new URL(url!, 'http://h').searchParams.get('start_url') ?? ''
  }

  it('builds the host-scoped allservices view with the state checkbox on', () => {
    const inner = innerView(buildServiceStateViewUrl(cmk, { host: 'web01' }, 'CRITICAL'))
    expect(inner).toContain('view.py?')
    expect(inner).toContain('view_name=allservices')
    expect(inner).toContain('host=web01')
    expect(inner).toContain('st2=on')
    expect(inner).toContain('_active=svcstate%3Bhost')
  })

  it('switches to the site filter for site targets', () => {
    const inner = innerView(buildServiceStateViewUrl(cmk, { site: 'remote1' }, 'WARNING'))
    expect(inner).toContain('site=remote1')
    expect(inner).toContain('st1=on')
    expect(inner).toContain('_active=svcstate%3Bsite')
  })

  it('returns null outside a Checkmk deployment or without a target', () => {
    expect(buildServiceStateViewUrl(null, { host: 'web01' }, 'OK')).toBeNull()
    expect(buildServiceStateViewUrl(cmk, {}, 'OK')).toBeNull()
  })

  it('links PENDING to the svcstate "stp" checkbox', () => {
    const inner = innerView(buildServiceStateViewUrl(cmk, { host: 'web01' }, 'PENDING'))
    expect(inner).toContain('view_name=allservices')
    expect(inner).toContain('host=web01')
    expect(inner).toContain('stp=on')
  })

  it('returns null for states the svcstate filter cannot express', () => {
    expect(buildServiceStateViewUrl(cmk, { host: 'web01' }, 'DOWN')).toBeNull()
  })
})

describe('openUrl', () => {
  function clickedHrefs(run: () => void): string[] {
    const hrefs: string[] = []
    const orig = HTMLAnchorElement.prototype.click
    HTMLAnchorElement.prototype.click = function (this: HTMLAnchorElement) {
      hrefs.push(this.href)
    }
    try {
      run()
    } finally {
      HTMLAnchorElement.prototype.click = orig
    }
    return hrefs
  }

  it('opens http(s)/mailto/tel and relative URLs', () => {
    const hrefs = clickedHrefs(() => {
      openUrl('https://example.com/x', '_blank')
      openUrl('mailto:ops@example.com', '_blank')
      openUrl('/relative/path', '_self')
    })
    expect(hrefs).toHaveLength(3)
  })

  it('refuses javascript: URLs even with embedded control characters', () => {
    // Each refusal warns about the blocked scheme; capture it so the warning is
    // asserted rather than leaking to the console.
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const hrefs = clickedHrefs(() => {
      openUrl('javascript:alert(1)', '_blank')
      openUrl('java\tscript:alert(1)', '_blank')
      openUrl('java\nscript:alert(1)', '_blank')
      openUrl('data:text/html,<script>alert(1)</script>', '_blank')
    })
    expect(hrefs).toHaveLength(0)
    expect(warn).toHaveBeenCalled()
    warn.mockRestore()
  })
})
