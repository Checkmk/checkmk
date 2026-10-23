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
      const opts = useGraphRenderOptions(undefined, true)
      expect(opts.horizontalAxis.value).toBe(true)
      expect(opts.verticalAxis.value).toBe(true)
      expect(opts.verticalAxisWidthMode.value).toBe('fixed')
      expect(opts.fixedVerticalAxisWidth.value).toBe(8)
      expect(opts.timestamp.value).toBe(false)
      expect(opts.roundMargin.value).toBe(false)
      expect(opts.graphLegend.value).toBe(true)
      expect(opts.graphLegendStyle.value).toBe('compact')
      expect(opts.clickToPlacePin.value).toBe(true)
      expect(opts.showBurgerMenu.value).toBe(false)
      expect(opts.dontFollowTimerange.value).toBe(false)
    })

    it('keeps the legend off for stored options without it', () => {
      const opts = useGraphRenderOptions({}, false)
      expect(opts.graphLegend.value).toBe(false)
    })

    it('keeps the legend off for a stored widget without any options', () => {
      const opts = useGraphRenderOptions(undefined, false)
      expect(opts.graphLegend.value).toBe(false)
    })
  })

  describe('initialization with custom data', () => {
    it('should initialize from provided GraphRenderOptions', () => {
      const opts = useGraphRenderOptions(
        {
          show_time_axis: false,
          show_vertical_axis: false,
          vertical_axis_width: 42,
          show_graph_time: true,
          show_margin: true,
          show_legend: true,
          legend_style: 'extended',
          show_pin: false,
          show_controls: true,
          fixed_timerange: true
        },
        false
      )
      expect(opts.horizontalAxis.value).toBe(false)
      expect(opts.verticalAxis.value).toBe(false)
      expect(opts.verticalAxisWidthMode.value).toBe('absolute')
      expect(opts.fixedVerticalAxisWidth.value).toBe(42)
      expect(opts.timestamp.value).toBe(true)
      expect(opts.roundMargin.value).toBe(true)
      expect(opts.graphLegend.value).toBe(true)
      expect(opts.graphLegendStyle.value).toBe('extended')
      expect(opts.clickToPlacePin.value).toBe(false)
      expect(opts.showBurgerMenu.value).toBe(true)
      expect(opts.dontFollowTimerange.value).toBe(true)
    })
  })

  describe('verticalAxisWidthMode detection', () => {
    it('should detect "absolute" when vertical_axis_width is a number', () => {
      const opts = useGraphRenderOptions({ vertical_axis_width: 20 }, false)
      expect(opts.verticalAxisWidthMode.value).toBe('absolute')
    })

    it('should detect "fixed" when vertical_axis_width is "fixed"', () => {
      const opts = useGraphRenderOptions({ vertical_axis_width: 'fixed' }, false)
      expect(opts.verticalAxisWidthMode.value).toBe('fixed')
    })

    it('should detect "fixed" when vertical_axis_width is undefined', () => {
      const opts = useGraphRenderOptions({}, false)
      expect(opts.verticalAxisWidthMode.value).toBe('fixed')
    })
  })

  describe('graphRenderOptions computed', () => {
    it('should map refs to spec fields correctly', () => {
      const opts = useGraphRenderOptions(undefined, true)
      expect(opts.graphRenderOptions.value).toEqual({
        show_time_axis: true,
        show_vertical_axis: true,
        vertical_axis_width: 'fixed',
        show_graph_time: false,
        show_margin: false,
        show_legend: true,
        legend_style: 'compact',
        show_pin: true,
        show_controls: false,
        fixed_timerange: false
      })
    })

    it('should output numeric vertical_axis_width in absolute mode', () => {
      const opts = useGraphRenderOptions({ vertical_axis_width: 30 }, false)
      expect(opts.graphRenderOptions.value.vertical_axis_width).toBe(30)
    })

    it('should output "fixed" string for vertical_axis_width in fixed mode', () => {
      const opts = useGraphRenderOptions(undefined, true)
      expect(opts.graphRenderOptions.value.vertical_axis_width).toBe('fixed')
    })

    it('should update reactively when refs are mutated', () => {
      const opts = useGraphRenderOptions(undefined, true)

      opts.horizontalAxis.value = false
      opts.graphLegend.value = false
      opts.graphLegendStyle.value = 'extended'

      expect(opts.graphRenderOptions.value.show_time_axis).toBe(false)
      expect(opts.graphRenderOptions.value.show_legend).toBe(false)
      expect(opts.graphRenderOptions.value.legend_style).toBe('extended')
    })

    it('should update vertical_axis_width when switching mode and size', () => {
      const opts = useGraphRenderOptions(undefined, true)
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
