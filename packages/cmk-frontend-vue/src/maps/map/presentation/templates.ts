/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  DataElement,
  ElementLabel,
  PresentationElement,
  PresentationTheme,
  ShapeElement,
  TextElement
} from '@/maps/types/api'

import { createElement } from './elements'

// Slide templates for the design-first workflow: each builds a finished-looking
// 1920×1080 layout whose data tiles are UNBOUND slots — the operator applies a
// design and then fills the slots in connect-data mode. Built on createElement
// so every element starts schema-valid; colors are hex or null (theme default)
// to satisfy the backend's color validator.

export interface PresentationTemplate {
  id: string
  title: string
  description: string
  theme: PresentationTheme
  build: () => PresentationElement[]
}

interface Geo {
  x: number
  y: number
  w: number
  h: number
  z: number
}

function label(text: string | null = null, size = 14): ElementLabel {
  return {
    show: true,
    text,
    size,
    color: null,
    background: null,
    weight: 'bold',
    align: 'center'
  }
}

function textBlock(
  text: string,
  geo: Geo,
  opts: Partial<Pick<TextElement, 'font_size' | 'font_weight' | 'text_align' | 'color'>> = {}
): TextElement {
  const el = createElement('text', geo.x, geo.y)
  if (el.kind !== 'text') {
    throw new Error('unreachable')
  }
  Object.assign(el, geo, { text, text_align: 'center' as const }, opts)
  return el
}

function dataTile(
  geo: Geo,
  opts: {
    mode?: 'icon' | 'text' | 'gadget'
    gadget?: 'gauge' | 'bar' | 'trafficlight' | 'value'
  } = {}
): DataElement {
  const el = createElement('data', geo.x, geo.y)
  if (el.kind !== 'data') {
    throw new Error('unreachable')
  }
  Object.assign(el, geo)
  el.display = {
    mode: opts.mode ?? 'icon',
    ...(opts.mode === 'gadget' ? { gadget_type: opts.gadget ?? 'gauge' } : {})
  }
  el.label = label()
  return el
}

function shape(
  kind: 'rect' | 'ellipse' | 'line' | 'arrow',
  geo: Geo,
  opts: Partial<ShapeElement> = {}
): ShapeElement {
  const el = createElement(kind, geo.x, geo.y)
  if (el.kind !== 'shape') {
    throw new Error('unreachable')
  }
  Object.assign(el, geo, opts)
  return el
}

function connector(startRef: string, endRef: string, z: number): ShapeElement {
  const el = shape('line', { x: 0, y: 0, w: 10, h: 10, z })
  el.start_ref = startRef
  el.end_ref = endRef
  el.data_slot = true
  el.flow = true
  el.stroke_width = 4
  return el
}

function grid(
  cols: number,
  rows: number,
  area: { x: number; y: number; w: number; h: number },
  gap: number
): Geo[] {
  const tileW = (area.w - gap * (cols - 1)) / cols
  const tileH = (area.h - gap * (rows - 1)) / rows
  const out: Geo[] = []
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      out.push({
        x: Math.round(area.x + c * (tileW + gap)),
        y: Math.round(area.y + r * (tileH + gap)),
        w: Math.round(tileW),
        h: Math.round(tileH),
        z: 10 + r * cols + c
      })
    }
  }
  return out
}

function nocOverview(_t: (s: string) => string): PresentationElement[] {
  return [
    textBlock(
      _t('NETWORK OPERATIONS'),
      { x: 360, y: 70, w: 1200, h: 90, z: 1 },
      {
        font_size: 64
      }
    ),
    textBlock(
      _t('Live infrastructure overview'),
      { x: 560, y: 165, w: 800, h: 40, z: 2 },
      {
        font_size: 24,
        font_weight: 'normal'
      }
    ),
    shape('line', { x: 560, y: 235, w: 800, h: 4, z: 3 }, { stroke_width: 3 }),
    ...grid(3, 2, { x: 260, y: 300, w: 1400, h: 560 }, 40).map((g) =>
      dataTile(g, { mode: 'gadget', gadget: 'gauge' })
    ),
    textBlock(
      _t('Connect each tile to a host or service'),
      { x: 560, y: 930, w: 800, h: 36, z: 30 },
      {
        font_size: 18,
        font_weight: 'normal'
      }
    )
  ]
}

function statusWall(_t: (s: string) => string): PresentationElement[] {
  return [
    textBlock(_t('STATUS WALL'), { x: 460, y: 50, w: 1000, h: 76, z: 1 }, { font_size: 56 }),
    ...grid(4, 3, { x: 160, y: 190, w: 1600, h: 760 }, 32).map((g) => dataTile(g))
  ]
}

function kpiDashboard(_t: (s: string) => string): PresentationElement[] {
  return [
    textBlock(
      _t('SERVICE KPIs'),
      { x: 80, y: 60, w: 900, h: 80, z: 1 },
      {
        font_size: 56,
        text_align: 'left'
      }
    ),
    ...grid(4, 1, { x: 80, y: 220, w: 1760, h: 330 }, 40).map((g) =>
      dataTile(g, { mode: 'gadget', gadget: 'gauge' })
    ),
    ...grid(2, 1, { x: 80, y: 610, w: 1760, h: 300 }, 40).map((g) =>
      dataTile(g, { mode: 'gadget', gadget: 'bar' })
    )
  ]
}

function weathermap(_t: (s: string) => string): PresentationElement[] {
  const core = shape('rect', { x: 810, y: 440, w: 300, h: 180, z: 20 }, { data_slot: true })
  core.label = label(_t('Core'), 18)
  core.name = _t('Core')
  const sites: Geo[] = [
    { x: 160, y: 120, w: 260, h: 150, z: 21 },
    { x: 830, y: 90, w: 260, h: 150, z: 22 },
    { x: 1500, y: 120, w: 260, h: 150, z: 23 },
    { x: 160, y: 780, w: 260, h: 150, z: 24 },
    { x: 1500, y: 780, w: 260, h: 150, z: 25 }
  ]
  // Named elements: the layers panel and the connector endpoint dropdowns
  // would otherwise show five anonymous "Rect"/"Line" entries.
  const nodes = sites.map((g, i) => {
    const el = shape('rect', g, { data_slot: true })
    el.label = label(`${_t('Site')} ${i + 1}`, 16)
    el.name = `${_t('Site')} ${i + 1}`
    return el
  })
  const links = nodes.map((n, i) => {
    const link = connector(core.id, n.id, 5 + i)
    link.name = `${_t('Link')} ${i + 1}`
    return link
  })
  return [
    textBlock(
      _t('NETWORK WEATHERMAP'),
      { x: 510, y: 950, w: 900, h: 60, z: 40 },
      {
        font_size: 36
      }
    ),
    ...links,
    core,
    ...nodes
  ]
}

function incidentMap(_t: (s: string) => string): PresentationElement[] {
  return [
    textBlock(
      _t('CRITICAL SERVICES'),
      { x: 360, y: 80, w: 1200, h: 90, z: 1 },
      {
        font_size: 64
      }
    ),
    ...grid(3, 1, { x: 200, y: 280, w: 1520, h: 420 }, 48).map((g) =>
      dataTile(g, { mode: 'text' })
    ),
    textBlock(
      _t('All states update live'),
      { x: 660, y: 800, w: 600, h: 40, z: 20 },
      {
        font_size: 20,
        font_weight: 'normal'
      }
    )
  ]
}

function locationStatus(_t: (s: string) => string): PresentationElement[] {
  const img = createElement('image', 120, 220)
  if (img.kind !== 'image') {
    throw new Error('unreachable')
  }
  Object.assign(img, { w: 800, h: 640, z: 5 })
  return [
    textBlock(_t('LOCATION STATUS'), { x: 460, y: 60, w: 1000, h: 80, z: 1 }, { font_size: 56 }),
    img,
    ...grid(2, 2, { x: 1000, y: 220, w: 800, h: 640 }, 32).map((g) => dataTile(g))
  ]
}

export function presentationTemplates(_t: (s: string) => string): PresentationTemplate[] {
  return [
    {
      id: 'blank',
      title: _t('Blank'),
      description: _t('Start from an empty slide'),
      theme: 'midnight',
      build: () => []
    },
    {
      id: 'noc-overview',
      title: _t('NOC Overview'),
      description: _t('Headline and six gauge tiles for the big screen'),
      theme: 'midnight',
      build: () => nocOverview(_t)
    },
    {
      id: 'status-wall',
      title: _t('Status Wall'),
      description: _t('Twelve status tiles at a glance'),
      theme: 'midnight',
      build: () => statusWall(_t)
    },
    {
      id: 'kpi-dashboard',
      title: _t('KPI Dashboard'),
      description: _t('Four gauges and two bars on a dark ops theme'),
      theme: 'ops',
      build: () => kpiDashboard(_t)
    },
    {
      id: 'weathermap',
      title: _t('Network Weathermap'),
      description: _t('Core and five sites with animated flow links'),
      theme: 'midnight',
      build: () => weathermap(_t)
    },
    {
      id: 'incident-map',
      title: _t('Incident wall'),
      description: _t('Three large state tiles for war-room walls'),
      theme: 'aurora',
      build: () => incidentMap(_t)
    },
    {
      id: 'location-status',
      title: _t('Location Status'),
      description: _t('Floor plan or photo beside four status tiles'),
      theme: 'paper',
      build: () => locationStatus(_t)
    }
  ]
}
