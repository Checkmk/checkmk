/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import type { MapElement, MonitoringState, ObjectState } from '@/maps/types/api'
import { sanitizeTemplateHtml } from '@/maps/utils/sanitize'
import { formatServicesSummary, interpolateTemplate, resolveTemplate } from '@/maps/utils/template'

import { anObject } from '../support/fixtures'
import { aState } from '../support/fixtures'

// Concrete builders (not Partial spreads) so the objects satisfy
// `exactOptionalPropertyTypes` without ever assigning `undefined`.
function makeObject(
  fields: {
    host_name?: string
    service_description?: string
    label?: MapElement['label']
  } = {}
): MapElement {
  const obj: MapElement = anObject({ id: 'o1', type: 'host', x: 0, y: 0, url_target: '_blank' })
  if (fields.host_name !== undefined) {
    obj.host_name = fields.host_name
  }
  if (fields.service_description !== undefined) {
    obj.service_description = fields.service_description
  }
  if (fields.label !== undefined) {
    obj.label = fields.label
  }
  return obj
}

function makeState(
  fields: {
    state?: MonitoringState
    output?: string
    perf_data?: string
    acknowledged?: boolean
    in_downtime?: boolean
    stale?: boolean
  } = {}
): ObjectState {
  return aState({
    object_id: 'o1',
    type: 'host',
    state: fields.state ?? 'UP',
    output: fields.output ?? '',
    perf_data: fields.perf_data ?? '',
    acknowledged: fields.acknowledged ?? false,
    in_downtime: fields.in_downtime ?? false,
    stale: fields.stale ?? false
  })
}

describe('interpolateTemplate', () => {
  it('resolves basic object/state placeholders', () => {
    const obj = makeObject({ host_name: 'web01', service_description: 'CPU' })
    const state = makeState({ state: 'WARNING', output: 'high load' })
    const out = interpolateTemplate('{{host}}/{{service}} is {{state}}: {{output}}', obj, state)
    expect(out).toBe('web01/CPU is WARNING: high load')
  })

  it('uses the label text for {{name}} when set', () => {
    const obj = makeObject({
      host_name: 'web01',
      label: {
        show: true,
        text: 'Frontend',
        x: 0,
        y: 0,
        size: 10,
        color: '#fff',
        background: 'transparent'
      }
    })
    expect(interpolateTemplate('{{name}}', obj, makeState())).toBe('Frontend')
  })

  it('{{output}} is the first line only, {{long_output}} keeps everything', () => {
    const state = makeState({ output: 'summary line\ndetail 1\ndetail 2' })
    expect(interpolateTemplate('{{output}}', makeObject(), state)).toBe('summary line')
    expect(interpolateTemplate('{{long_output}}', makeObject(), state)).toBe(
      'summary line\ndetail 1\ndetail 2'
    )
  })

  it('escapes interpolated values but keeps the authored template markup', () => {
    // A monitored host controls its plugin output; markup in it must not survive
    // as markup, while the author's own template tags stay intact.
    const state = makeState({ output: '<a href="ssh://evil">x</a> & <b>bold</b>' })
    expect(interpolateTemplate('<b>Status:</b> {{output}}', makeObject(), state)).toBe(
      '<b>Status:</b> &lt;a href=&quot;ssh://evil&quot;&gt;x&lt;/a&gt; &amp; &lt;b&gt;bold&lt;/b&gt;'
    )
  })

  it('renders boolean flags as true/false strings', () => {
    const state = makeState({ acknowledged: true, in_downtime: false, stale: true })
    expect(
      interpolateTemplate('{{acknowledged}} {{in_downtime}} {{stale}}', makeObject(), state)
    ).toBe('true false true')
  })

  it('resolves the first perf metric and a named metric', () => {
    const state = makeState({ perf_data: 'rta=0.5ms;100;200 pl=0%' })
    expect(interpolateTemplate('{{metric}}', makeObject(), state)).toBe('0.5ms')
    expect(interpolateTemplate('{{metric_unit}}', makeObject(), state)).toBe('ms')
    expect(interpolateTemplate('{{metric:pl}}', makeObject(), state)).toBe('0%')
  })

  it('returns empty string for an unknown named metric', () => {
    const state = makeState({ perf_data: 'rta=0.5ms' })
    expect(interpolateTemplate('[{{metric:missing}}]', makeObject(), state)).toBe('[]')
  })

  it('returns empty string for unknown placeholders and missing state', () => {
    expect(interpolateTemplate('[{{nope}}]', makeObject(), undefined)).toBe('[]')
    expect(interpolateTemplate('[{{state}}]', makeObject(), undefined)).toBe('[]')
  })
})

describe('interpolateTemplate → sanitizeTemplateHtml pipeline', () => {
  // The two functions are a security pair: interpolation escapes the untrusted
  // monitoring data (plugin output) it injects, so it can never become markup,
  // and sanitization is the second line of defense on the authored template.
  it('neutralises a link smuggled through plugin output', () => {
    const state = makeState({ output: '<a href=" ssh://-oProxyCommand=curl+evil@h">x</a>' })
    const html = sanitizeTemplateHtml(interpolateTemplate('{{output}}', makeObject(), state))
    expect(html).not.toContain('<a')
    expect(html).toContain('&lt;a')
  })

  it('neutralises a <script> smuggled through plugin output', () => {
    const state = makeState({ output: '<script>alert(1)</script>SAFE' })
    const html = sanitizeTemplateHtml(interpolateTemplate('<b>{{output}}</b>', makeObject(), state))
    // No live <script>: the smuggled tag survives only as inert escaped text,
    // while the author's own <b> tag is preserved.
    expect(html).not.toContain('<script')
    expect(html).toContain('&lt;script&gt;')
    expect(html).toContain('SAFE')
    expect(html).toContain('<b>')
  })

  it('neutralises event-handler markup smuggled through plugin output', () => {
    const state = makeState({ output: '<img src=x onerror="alert(1)">marker' })
    const html = sanitizeTemplateHtml(interpolateTemplate('<b>{{output}}</b>', makeObject(), state))
    // No live <img>/attribute — escaped to text.
    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;img')
    expect(html).toContain('marker')
  })
})

describe('resolveTemplate', () => {
  it('prefers object, then map, then global', () => {
    expect(resolveTemplate('obj', 'map', 'global')).toBe('obj')
    expect(resolveTemplate(null, 'map', 'global')).toBe('map')
    expect(resolveTemplate('', '', 'global')).toBe('global')
    expect(resolveTemplate(null, undefined, null)).toBeNull()
  })
})

describe('formatServicesSummary', () => {
  it('orders counts worst-first and omits zero buckets', () => {
    expect(formatServicesSummary({ ok: 12, warning: 2, critical: 1, unknown: 0, pending: 0 })).toBe(
      '1 CRIT · 2 WARN · 12 OK'
    )
  })

  it('returns empty string when there is no summary', () => {
    expect(formatServicesSummary(undefined)).toBe('')
  })
})
