/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'
import { type ModelRef, nextTick, ref } from 'vue'

import {
  determineSizingMode,
  legacySizeValue,
  useRelativeGridLayout,
  widgetHasTitle
} from '@/dashboard/components/RelativeGrid/composables/useRelativeGridLayout'
import { SIZING_MODE, WIDGET_MIN_SIZE } from '@/dashboard/components/RelativeGrid/types'
import type { ContentRelativeGrid } from '@/dashboard/types/dashboard'
import type { RelativeGridWidget } from '@/dashboard/types/widget'

import {
  STANDARD_DASHBOARD_DIMS,
  makeRelativeGridContent,
  makeRelativeGridWidget
} from '../testHelpers'

// ─── Helper functions ──────────────────────────────────────────────────────────

describe('widgetHasTitle', () => {
  it('should return true for with_background render mode', () => {
    const widget = makeRelativeGridWidget({ render_mode: 'with_background' })

    const result = widgetHasTitle(widget)

    expect(result).toBe(true)
  })

  it('should return true for without_background render mode', () => {
    const widget = makeRelativeGridWidget({ render_mode: 'without_background' })

    const result = widgetHasTitle(widget)

    expect(result).toBe(true)
  })

  it('should return false for hidden render mode', () => {
    const widget = makeRelativeGridWidget({ render_mode: 'hidden' })

    const result = widgetHasTitle(widget)

    expect(result).toBe(false)
  })
})

describe('legacySizeValue', () => {
  it('should return 0 for "auto"', () => {
    const result = legacySizeValue('auto')

    expect(result).toBe(0)
  })

  it('should return -1 for "max"', () => {
    const result = legacySizeValue('max')

    expect(result).toBe(-1)
  })

  it('should return the number as-is for numeric values', () => {
    const result20 = legacySizeValue(20)
    const result1 = legacySizeValue(1)

    expect(result20).toBe(20)
    expect(result1).toBe(1)
  })

  it('should throw for unsupported string values', () => {
    expect(() => legacySizeValue('invalid' as never)).toThrow('Unsupported size value')
  })
})

describe('determineSizingMode', () => {
  it('should return MAX for -1', () => {
    const result = determineSizingMode(-1)

    expect(result).toBe(SIZING_MODE.MAX)
  })

  it('should return GROW for 0', () => {
    const result = determineSizingMode(0)

    expect(result).toBe(SIZING_MODE.GROW)
  })

  it('should return MANUAL for positive numbers', () => {
    const result20 = determineSizingMode(20)
    const result1 = determineSizingMode(1)

    expect(result20).toBe(SIZING_MODE.MANUAL)
    expect(result1).toBe(SIZING_MODE.MANUAL)
  })

  it('should return MANUAL for other negative numbers (not -1)', () => {
    const result = determineSizingMode(-2)

    expect(result).toBe(SIZING_MODE.MANUAL)
  })
})

// ─── useRelativeGridLayout composable ──────────────────────────────────────────

describe('useRelativeGridLayout', () => {
  function setup(content: ContentRelativeGrid) {
    const contentRef = ref(content) as ModelRef<ContentRelativeGrid>
    return {
      composable: useRelativeGridLayout(contentRef, WIDGET_MIN_SIZE),
      contentRef
    }
  }

  function setupWithDashboard(content: ContentRelativeGrid) {
    const { composable, contentRef } = setup(content)
    composable.updateDashboardLayout(STANDARD_DASHBOARD_DIMS, { x: 0, y: 0 })
    return { composable, contentRef }
  }

  describe('absoluteWidgetLayouts', () => {
    it('should return empty record for content with no widgets', () => {
      const { composable } = setupWithDashboard(makeRelativeGridContent())

      expect(composable.getAbsoluteLayout).toBeDefined()
    })

    it('should compute absolute layout for a single widget', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget({ position: { x: 1, y: 1 }, size: { width: 20, height: 10 } })
      })
      const { composable } = setupWithDashboard(content)

      const layout = composable.getAbsoluteLayout('w1')

      expect(layout.frame.position.left).toBe(0)
      expect(layout.frame.position.top).toBe(0)
      expect(layout.frame.dimensions.width).toBe(200)
      expect(layout.frame.dimensions.height).toBe(100)
    })

    it('should detect anchor position from widget position', () => {
      const content = makeRelativeGridContent({
        topLeft: makeRelativeGridWidget({ position: { x: 1, y: 1 } }),
        bottomRight: makeRelativeGridWidget({ position: { x: -1, y: -1 } })
      })
      const { composable } = setupWithDashboard(content)

      const topLeftAnchor = composable.getAnchorPosition('topLeft')
      const bottomRightAnchor = composable.getAnchorPosition('bottomRight')

      expect(topLeftAnchor).toBe('top-left')
      expect(bottomRightAnchor).toBe('bottom-right')
    })

    it('should determine dimension modes from size values', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget({ size: { width: 'max', height: 'auto' } })
      })
      const { composable } = setupWithDashboard(content)

      const modes = composable.getDimensionModes('w1')

      expect(modes.width).toBe(SIZING_MODE.MAX)
      expect(modes.height).toBe(SIZING_MODE.GROW)
    })

    it('should report MANUAL mode for numeric sizes', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget({ size: { width: 30, height: 20 } })
      })
      const { composable } = setupWithDashboard(content)

      const modes = composable.getDimensionModes('w1')

      expect(modes.width).toBe(SIZING_MODE.MANUAL)
      expect(modes.height).toBe(SIZING_MODE.MANUAL)
    })
  })

  describe('bringToFront', () => {
    it('should set z-index to 80 for the target widget', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget(),
        w2: makeRelativeGridWidget()
      })
      const { composable } = setup(content)

      composable.bringToFront('w1')

      expect(composable.getLayoutZIndex('w1')).toBe(80)
    })

    it('should reset other widgets to z-index 1', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget(),
        w2: makeRelativeGridWidget()
      })
      const { composable } = setup(content)

      composable.bringToFront('w1')

      expect(composable.getLayoutZIndex('w1')).toBe(80)
      expect(composable.getLayoutZIndex('w2')).toBe(1)
    })

    it('should update z-indexes when bringing a different widget to front', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget(),
        w2: makeRelativeGridWidget()
      })
      const { composable } = setup(content)

      composable.bringToFront('w1')
      expect(composable.getLayoutZIndex('w1')).toBe(80)
      expect(composable.getLayoutZIndex('w2')).toBe(1)

      composable.bringToFront('w2')
      expect(composable.getLayoutZIndex('w1')).toBe(1)
      expect(composable.getLayoutZIndex('w2')).toBe(80)
    })
  })

  describe('updateDashboardLayout', () => {
    it('should update dashboard dimensions and position', () => {
      const content = makeRelativeGridContent()
      const { composable } = setup(content)

      composable.updateDashboardLayout({ width: 500, height: 400 }, { x: 10, y: 20 })

      expect(composable.dashboardState.dimensions).toEqual({ width: 500, height: 400 })
      expect(composable.dashboardState.position).toEqual({ x: 10, y: 20 })
    })

    it('should compute layout extending beyond dashboard when widget does not fit', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget({ position: { x: 1, y: 1 }, size: { width: 20, height: 10 } })
      })
      const { composable } = setup(content)

      composable.updateDashboardLayout({ width: 100, height: 80 }, { x: 0, y: 0 })

      const layout = composable.getAbsoluteLayout('w1')
      expect(layout.frame.dimensions.width).toBeGreaterThan(100)
      expect(layout.frame.dimensions.height).toBeGreaterThan(80)
    })
  })

  describe('updateLayoutPosition', () => {
    it('should update widget position', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget({ position: { x: 1, y: 1 } })
      })
      const { composable, contentRef } = setup(content)

      composable.updateLayoutPosition('w1', { x: 5, y: 10 })

      expect(contentRef.value.widgets['w1']!.layout.position).toEqual({ x: 5, y: 10 })
    })
  })

  describe('updateLayoutDimensions', () => {
    it('should update numeric dimensions', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget({ size: { width: 20, height: 10 } })
      })
      const { composable, contentRef } = setup(content)

      composable.updateLayoutDimensions('w1', { width: 30, height: 15 })

      expect(contentRef.value.widgets['w1']!.layout.size.width).toBe(30)
      expect(contentRef.value.widgets['w1']!.layout.size.height).toBe(15)
    })
  })

  describe('toggleSizing', () => {
    it('should cycle MANUAL → GROW for width', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget({ size: { width: 20, height: 10 } })
      })
      const { composable, contentRef } = setupWithDashboard(content)

      composable.toggleSizing('w1', 'width')

      expect(contentRef.value.widgets['w1']!.layout.size.width).toBe('auto')
    })

    it('should cycle GROW → MAX for width', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget({ size: { width: 'auto', height: 10 } })
      })
      const { composable, contentRef } = setupWithDashboard(content)

      composable.toggleSizing('w1', 'width')

      expect(contentRef.value.widgets['w1']!.layout.size.width).toBe('max')
    })

    it('should cycle MAX → MANUAL for width', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget({ size: { width: 'max', height: 10 } })
      })
      const { composable, contentRef } = setupWithDashboard(content)

      composable.toggleSizing('w1', 'width')

      const width = contentRef.value.widgets['w1']!.layout.size.width
      expect(typeof width).toBe('number')
      expect(width).toBe(100)
    })

    it('should bring widget to front after toggle', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget({ size: { width: 20, height: 10 } }),
        w2: makeRelativeGridWidget({ size: { width: 20, height: 10 } })
      })
      const { composable } = setupWithDashboard(content)

      composable.toggleSizing('w1', 'width')

      expect(composable.getLayoutZIndex('w1')).toBe(80)
      expect(composable.getLayoutZIndex('w2')).toBe(1)
    })
  })

  describe('selectAnchor', () => {
    it('should be a no-op when selecting the same anchor', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget({ position: { x: 1, y: 1 } })
      })
      const { composable, contentRef } = setupWithDashboard(content)
      const positionBefore = { ...contentRef.value.widgets['w1']!.layout.position }

      composable.selectAnchor('w1', 'top-left')

      const positionAfter = contentRef.value.widgets['w1']!.layout.position
      expect(positionAfter).toEqual(positionBefore)
    })

    it('should recalculate position when changing anchor', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget({
          position: { x: 1, y: 1 },
          size: { width: 20, height: 10 }
        })
      })
      const { composable, contentRef } = setupWithDashboard(content)

      composable.selectAnchor('w1', 'top-right')

      expect(contentRef.value.widgets['w1']!.layout.position.x).toBeLessThan(0)
    })

    it('should recalculate position when changing to bottom-left anchor', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget({
          position: { x: 1, y: 1 },
          size: { width: 20, height: 10 }
        })
      })
      const { composable, contentRef } = setupWithDashboard(content)

      composable.selectAnchor('w1', 'bottom-left')

      expect(contentRef.value.widgets['w1']!.layout.position.x).toBeGreaterThan(0)
      expect(contentRef.value.widgets['w1']!.layout.position.y).toBeLessThan(0)
    })

    it('should recalculate position when changing to bottom-right anchor', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget({
          position: { x: 1, y: 1 },
          size: { width: 20, height: 10 }
        })
      })
      const { composable, contentRef } = setupWithDashboard(content)

      composable.selectAnchor('w1', 'bottom-right')

      expect(contentRef.value.widgets['w1']!.layout.position.x).toBeLessThan(0)
      expect(contentRef.value.widgets['w1']!.layout.position.y).toBeLessThan(0)
    })

    it('should recalculate position when changing from bottom-right to top-left', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget({
          position: { x: -1, y: -1 },
          size: { width: 20, height: 10 }
        })
      })
      const { composable, contentRef } = setupWithDashboard(content)

      composable.selectAnchor('w1', 'top-left')

      expect(contentRef.value.widgets['w1']!.layout.position.x).toBeGreaterThan(0)
      expect(contentRef.value.widgets['w1']!.layout.position.y).toBeGreaterThan(0)
    })
  })

  describe('z-index management', () => {
    it('should initialize z-indexes for all widgets', () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget(),
        w2: makeRelativeGridWidget()
      })

      const { composable } = setup(content)

      expect(composable.getLayoutZIndex('w1')).toBe(1)
      expect(composable.getLayoutZIndex('w2')).toBe(1)
    })

    it('should clean up z-indexes when widgets are removed', async () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget(),
        w2: makeRelativeGridWidget()
      })
      const { composable, contentRef } = setup(content)
      expect(composable.getLayoutZIndex('w2')).toBe(1)

      const newWidgets = { ...contentRef.value.widgets }
      delete newWidgets['w2']
      contentRef.value = makeRelativeGridContent(newWidgets as Record<string, RelativeGridWidget>)
      await nextTick()

      expect(composable.getLayoutZIndex('w2')).toBeNull()
    })

    it('should bring new widget to front when added after initialization', async () => {
      const content = makeRelativeGridContent({
        w1: makeRelativeGridWidget()
      })
      const { composable, contentRef } = setup(content)

      contentRef.value = makeRelativeGridContent({
        ...contentRef.value.widgets,
        w2: makeRelativeGridWidget()
      })
      await nextTick()

      expect(composable.getLayoutZIndex('w2')).toBe(80)
      expect(composable.getLayoutZIndex('w1')).toBe(1)
    })
  })
})
