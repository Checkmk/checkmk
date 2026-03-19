/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { useGraphRenderOptions } from '@/dashboard/components/Wizard/components/GraphRenderOptions/useGraphRenderOptions'

describe('useGraphRenderOptions', () => {
  describe('default values', () => {
    it('should initialize with correct defaults when called with no arguments', () => {
      const opts = useGraphRenderOptions()
      expect(opts.horizontalAxis.value).toBe(true)
      expect(opts.verticalAxis.value).toBe(true)
      expect(opts.verticalAxisWidthMode.value).toBe('fixed')
      expect(opts.fixedVerticalAxisWidth.value).toBe(8)
      expect(opts.fontSize.value).toBe(8)
      expect(opts.timestamp.value).toBe(false)
      expect(opts.roundMargin.value).toBe(false)
      expect(opts.graphLegend.value).toBe(false)
      expect(opts.clickToPlacePin.value).toBe(true)
      expect(opts.showBurgerMenu.value).toBe(false)
      expect(opts.dontFollowTimerange.value).toBe(false)
    })
  })

  describe('initialization with custom data', () => {
    it('should initialize from provided GraphRenderOptions', () => {
      const opts = useGraphRenderOptions({
        show_time_axis: false,
        show_vertical_axis: false,
        vertical_axis_width: 42,
        font_size_pt: 12,
        show_graph_time: true,
        show_margin: true,
        show_legend: true,
        show_pin: false,
        show_controls: true,
        fixed_timerange: true
      })
      expect(opts.horizontalAxis.value).toBe(false)
      expect(opts.verticalAxis.value).toBe(false)
      expect(opts.verticalAxisWidthMode.value).toBe('absolute')
      expect(opts.fixedVerticalAxisWidth.value).toBe(42)
      expect(opts.fontSize.value).toBe(12)
      expect(opts.timestamp.value).toBe(true)
      expect(opts.roundMargin.value).toBe(true)
      expect(opts.graphLegend.value).toBe(true)
      expect(opts.clickToPlacePin.value).toBe(false)
      expect(opts.showBurgerMenu.value).toBe(true)
      expect(opts.dontFollowTimerange.value).toBe(true)
    })
  })

  describe('verticalAxisWidthMode detection', () => {
    it('should detect "absolute" when vertical_axis_width is a number', () => {
      const opts = useGraphRenderOptions({ vertical_axis_width: 20 })
      expect(opts.verticalAxisWidthMode.value).toBe('absolute')
    })

    it('should detect "fixed" when vertical_axis_width is "fixed"', () => {
      const opts = useGraphRenderOptions({ vertical_axis_width: 'fixed' })
      expect(opts.verticalAxisWidthMode.value).toBe('fixed')
    })

    it('should detect "fixed" when vertical_axis_width is undefined', () => {
      const opts = useGraphRenderOptions({})
      expect(opts.verticalAxisWidthMode.value).toBe('fixed')
    })
  })

  describe('graphRenderOptions computed', () => {
    it('should map refs to spec fields correctly', () => {
      const opts = useGraphRenderOptions()
      expect(opts.graphRenderOptions.value).toEqual({
        show_time_axis: true,
        show_vertical_axis: true,
        vertical_axis_width: 'fixed',
        font_size_pt: 8,
        show_graph_time: false,
        show_margin: false,
        show_legend: false,
        show_pin: true,
        show_controls: false,
        fixed_timerange: false
      })
    })

    it('should output numeric vertical_axis_width in absolute mode', () => {
      const opts = useGraphRenderOptions({ vertical_axis_width: 30 })
      expect(opts.graphRenderOptions.value.vertical_axis_width).toBe(30)
    })

    it('should output "fixed" string for vertical_axis_width in fixed mode', () => {
      const opts = useGraphRenderOptions()
      expect(opts.graphRenderOptions.value.vertical_axis_width).toBe('fixed')
    })

    it('should update reactively when refs are mutated', () => {
      const opts = useGraphRenderOptions()

      opts.horizontalAxis.value = false
      opts.fontSize.value = 14
      opts.graphLegend.value = true

      expect(opts.graphRenderOptions.value.show_time_axis).toBe(false)
      expect(opts.graphRenderOptions.value.font_size_pt).toBe(14)
      expect(opts.graphRenderOptions.value.show_legend).toBe(true)
    })

    it('should update vertical_axis_width when switching mode and size', () => {
      const opts = useGraphRenderOptions()
      expect(opts.graphRenderOptions.value.vertical_axis_width).toBe('fixed')

      opts.verticalAxisWidthMode.value = 'absolute'
      opts.fixedVerticalAxisWidth.value = 25
      expect(opts.graphRenderOptions.value.vertical_axis_width).toBe(25)

      opts.fixedVerticalAxisWidth.value = 50
      expect(opts.graphRenderOptions.value.vertical_axis_width).toBe(50)

      opts.verticalAxisWidthMode.value = 'fixed'
      expect(opts.graphRenderOptions.value.vertical_axis_width).toBe('fixed')
    })
  })
})
