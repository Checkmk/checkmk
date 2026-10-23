/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { isUnboundSlot } from '@/maps/map/presentation/binding'
import { presentationTemplates } from '@/maps/map/presentation/templates'

// Mirrors of the backend validators (presentation.py) — templates must only
// produce values these accept.
const COLOR_RE = /^(#[0-9a-fA-F]{3,8}|[a-zA-Z]{1,32}|transparent)$/
const FONT_RE = /^[a-zA-Z0-9 ,_'"\-.]{1,128}$/

const t = (s: string) => s

describe('presentationTemplates', () => {
  const templates = presentationTemplates(t)

  it('offers a blank template plus real designs', () => {
    expect(templates.find((x) => x.id === 'blank')?.build()).toEqual([])
    expect(templates.length).toBeGreaterThanOrEqual(6)
  })

  it.each(templates.filter((x) => x.id !== 'blank').map((x) => [x.id, x] as const))(
    '%s builds a valid slide',
    (_id, template) => {
      const els = template.build()
      expect(els.length).toBeGreaterThan(0)

      const ids = els.map((e) => e.id)
      expect(new Set(ids).size).toBe(ids.length)

      for (const el of els) {
        expect(el.x).toBeGreaterThanOrEqual(0)
        expect(el.y).toBeGreaterThanOrEqual(0)
        expect(el.x + el.w).toBeLessThanOrEqual(1920)
        expect(el.y + el.h).toBeLessThanOrEqual(1080)
        if ('fill' in el && el.fill) {
          expect(el.fill).toMatch(COLOR_RE)
        }
        if ('stroke' in el && el.stroke) {
          expect(el.stroke).toMatch(COLOR_RE)
        }
        if (el.kind === 'text' && el.font_family) {
          expect(el.font_family).toMatch(FONT_RE)
        }
        if (el.kind === 'shape' && (el.start_ref || el.end_ref)) {
          if (el.start_ref) {
            expect(ids).toContain(el.start_ref)
          }
          if (el.end_ref) {
            expect(ids).toContain(el.end_ref)
          }
        }
      }

      // Every design ships at least one unbound slot for the connect walkthrough.
      expect(els.some(isUnboundSlot)).toBe(true)
    }
  )

  it('builds fresh element ids on every call', () => {
    const tpl = templates.find((x) => x.id === 'noc-overview')!
    const a = tpl.build().map((e) => e.id)
    const b = tpl.build().map((e) => e.id)
    expect(a.some((id) => b.includes(id))).toBe(false)
  })
})
