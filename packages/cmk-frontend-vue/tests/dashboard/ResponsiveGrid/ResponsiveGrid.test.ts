/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { flushPromises, mount } from '@vue/test-utils'
import { GridLayout } from 'grid-layout-plus'
import { defineComponent, nextTick, ref } from 'vue'

import type { ContentPropsRecord } from '@/dashboard/components/DashboardContent/types'
import ResponsiveGrid from '@/dashboard/components/ResponsiveGrid/ResponsiveGrid.vue'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { useProvideMissingRuntimeFiltersAction } from '@/dashboard/composables/useProvideMissingRuntimeFiltersAction'
import type { ContentResponsiveGrid, DashboardConstants } from '@/dashboard/types/dashboard'

import {
  breakpointSettings,
  makeContentProps,
  makeLayoutWidget,
  makeRGContent
} from './testHelpers'

const dashboardConstants: DashboardConstants = {
  responsive_grid_breakpoints: breakpointSettings,
  widgets: {}
}

function makeContentPropsRecord(widgetIds: string[]): ContentPropsRecord {
  const result: Record<string, ContentPropsRecord[string]> = {}
  for (const id of widgetIds) {
    result[id] = makeContentProps(id)
  }
  return result
}

// grid-layout-plus determines breakpoint from wrapper's offsetWidth.
// In jsdom, offsetWidth defaults to 0, which maps to the smallest breakpoint (xxs -> XS).
// We must configure all breakpoints to avoid errors when grid-layout-plus selects
// a breakpoint that the dashboard hasn't initialized.
const allBreakpoints: ['XS', 'S', 'M', 'L', 'XL'] = ['XS', 'S', 'M', 'L', 'XL']

function responsiveGridWrapper(options: {
  content: ContentResponsiveGrid
  contentProps: ContentPropsRecord
  isEditing?: boolean
  allFiltersApplied?: boolean
  width?: number
}) {
  const contentRef = ref(options.content)
  const allFiltersApplied = ref(options.allFiltersApplied ?? true)

  const wrapperComponent = defineComponent({
    components: { ResponsiveGrid },
    setup() {
      useProvideDashboardConstants(dashboardConstants)
      useProvideMissingRuntimeFiltersAction(allFiltersApplied, () => {})
      return {
        content: contentRef,
        contentProps: options.contentProps,
        isEditing: options.isEditing ?? false,
        width: options.width
      }
    },
    template: `
      <div :style="{width: width ? width + 'px' : 'unset'}">
        <ResponsiveGrid
          v-model:content="content"
          :dashboard-key="{ owner: 'admin', name: 'test' }"
          :content-props="contentProps"
          :updated-widget-render-keys="{}"
          :is-editing="isEditing"
        />
      </div>
    `
  })

  return { wrapperComponent, contentRef, allFiltersApplied }
}

function renderResponsiveGrid(options: {
  content: ContentResponsiveGrid
  contentProps: ContentPropsRecord
  isEditing?: boolean
  allFiltersApplied?: boolean
}) {
  const { wrapperComponent, contentRef, allFiltersApplied } = responsiveGridWrapper({
    ...options,
    width: 1300
  })

  const result = render(wrapperComponent)
  return { ...result, contentRef, allFiltersApplied }
}

function mountResponsiveGrid(options: {
  content: ContentResponsiveGrid
  contentProps: ContentPropsRecord
  isEditing?: boolean
  allFiltersApplied?: boolean
}) {
  const { wrapperComponent, contentRef, allFiltersApplied } = responsiveGridWrapper(options)

  const wrapper = mount(wrapperComponent, { attachTo: document.body })
  return { wrapper, contentRef, allFiltersApplied }
}

describe('ResponsiveGrid', () => {
  describe('edit mode column guides', () => {
    it('shows column guide divs when isEditing is true', async () => {
      const content = makeRGContent({}, allBreakpoints)
      renderResponsiveGrid({
        content,
        contentProps: {},
        isEditing: true
      })

      await nextTick()

      const columnGuides = document.querySelectorAll('.db-responsive-grid__edit-column')
      expect(columnGuides.length).toBeGreaterThan(0)
    })

    it('hides column guides when isEditing is false', async () => {
      const content = makeRGContent({}, allBreakpoints)
      renderResponsiveGrid({
        content,
        contentProps: {},
        isEditing: false
      })

      await nextTick()

      const columnGuides = document.querySelectorAll('.db-responsive-grid__edit-column')
      expect(columnGuides.length).toBe(0)
    })
  })

  describe('missing runtime filters dialog', () => {
    it('shows dialog when filters are not applied', async () => {
      const content = makeRGContent({}, allBreakpoints)
      renderResponsiveGrid({
        content,
        contentProps: {},
        allFiltersApplied: false
      })

      await nextTick()

      expect(screen.getByText('Runtime filters are required to load data.')).toBeInTheDocument()
    })

    it('hides dialog when filters are applied', async () => {
      const content = makeRGContent({}, allBreakpoints)
      renderResponsiveGrid({
        content,
        contentProps: {},
        allFiltersApplied: true
      })

      await nextTick()

      expect(
        screen.queryByText('Runtime filters are required to load data.')
      ).not.toBeInTheDocument()
    })
  })

  describe('breakpoint switching', () => {
    it('updates content model sizes when grid-layout-plus switches breakpoints', async () => {
      const content = makeRGContent(
        {
          w1: makeLayoutWidget({
            default: {
              XS: { position: { x: 0, y: 0 }, size: { columns: 2, rows: 2 } },
              S: { position: { x: 0, y: 0 }, size: { columns: 4, rows: 3 } },
              M: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } },
              L: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 5 } },
              XL: { position: { x: 0, y: 0 }, size: { columns: 12, rows: 6 } }
            }
          })
        },
        allBreakpoints
      )

      const { wrapper } = mountResponsiveGrid({
        content,
        contentProps: makeContentPropsRecord(['w1']),
        isEditing: false
      })

      await flushPromises()
      await nextTick()

      // grid-layout-plus exposes its reactive state including `width` via setup expose().
      // Setting state.width triggers the library's internal responsive logic:
      //   width change → getBreakpointFromWidth() → responsiveGridLayout() →
      //   emits breakpoint-changed with the computed layout for that breakpoint →
      //   ResponsiveGrid.onBreakpointChange → updateSelectedLayout → content model updated
      const gridLayout = wrapper.findComponent(GridLayout)
      // Access the exposed state — vue-test-utils exposes it via vm.$.exposed
      const gridState = (gridLayout.vm.$ as unknown as { exposed: { state: { width: number } } })
        .exposed.state

      // grid-layout-plus renders each item as a .vgl-item with inline style
      // containing width/height in px — this is what we check to verify the
      // rendered widget dimensions actually change between breakpoints
      function getRenderedWidgetStyle(): CSSStyleDeclaration {
        const item = wrapper.find('.vgl-item')
        return (item.element as HTMLElement).style
      }

      // Trigger XL breakpoint (lg internal, width > 1217)
      gridState.width = 1300
      await flushPromises()
      await nextTick()

      const xlWidth = getRenderedWidgetStyle().width
      const xlHeight = getRenderedWidgetStyle().height

      // Trigger L breakpoint (md internal, width between 961 and 1217)
      gridState.width = 1000
      await flushPromises()
      await nextTick()

      const lWidth = getRenderedWidgetStyle().width
      const lHeight = getRenderedWidgetStyle().height

      // The library computed different pixel dimensions for each breakpoint.
      // XL has 12/24 columns = 50% width, L has 6/12 columns = 50% width,
      // but at different container widths (1300 vs 1000), so pixel widths differ.
      expect(xlWidth).not.toBe(lWidth)
      // The height should not change between breakpoints
      expect(xlHeight).toBe(lHeight)

      wrapper.unmount()
    })

    it('renders widget items within the grid', async () => {
      const content = makeRGContent(
        {
          w1: makeLayoutWidget({
            default: {
              XS: { position: { x: 0, y: 0 }, size: { columns: 4, rows: 4 } },
              S: { position: { x: 0, y: 0 }, size: { columns: 4, rows: 4 } },
              M: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } },
              L: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } },
              XL: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } }
            }
          })
        },
        allBreakpoints
      )

      const { wrapper } = mountResponsiveGrid({
        content,
        contentProps: makeContentPropsRecord(['w1']),
        isEditing: false
      })

      await flushPromises()
      await nextTick()

      expect(wrapper.findAll('[aria-label="Widget"]').length).toBe(1)

      wrapper.unmount()
    })
  })
})
