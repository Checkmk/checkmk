/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'

import { useInternalBreakpointConfig } from '@/dashboard/components/ResponsiveGrid/composables/useInternalBreakpointConfig'
import {
  createWidgetLayout,
  useResponsiveGridLayout
} from '@/dashboard/components/ResponsiveGrid/composables/useResponsiveGridLayout'
import type {
  ContentResponsiveGrid,
  DashboardConstants,
  ResponsiveGridBreakpoint
} from '@/dashboard/types/dashboard'

import {
  breakpointSettings,
  makeLayoutWidget,
  makeRGContent,
  widgetConstraints
} from '../testHelpers'

describe('useResponsiveGridLayout', () => {
  function setup(content: ContentResponsiveGrid) {
    const breakpointConfig = useInternalBreakpointConfig(breakpointSettings)
    const contentRef = ref(content)
    return useResponsiveGridLayout(breakpointConfig, contentRef, widgetConstraints)
  }

  function setupWithConstraints(
    content: ContentResponsiveGrid,
    constraints: DashboardConstants['widgets']
  ) {
    const breakpointConfig = useInternalBreakpointConfig(breakpointSettings)
    const contentRef = ref(content)
    const composable = useResponsiveGridLayout(breakpointConfig, contentRef, constraints)
    return { composable, contentRef }
  }

  function makeWidgetConstraints(
    responsive: Partial<
      Record<
        ResponsiveGridBreakpoint,
        {
          minimum_size: { columns: number; rows: number }
          initial_size: { columns: number; rows: number }
        }
      >
    >
  ): DashboardConstants['widgets'][string] {
    return {
      filter_context: { restricted_to_single: [] },
      title_macros: [],
      layout: {
        relative: {
          initial_size: { width: 1, height: 1 },
          minimum_size: { width: 1, height: 1 },
          initial_position: { x: 0, y: 0 },
          is_resizable: true
        },
        responsive
      }
    }
  }

  describe('layout computation', () => {
    it('should compute internal layouts from widget definitions', () => {
      const content = makeRGContent({
        widget_1: makeLayoutWidget({
          default: {
            L: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 8 } },
            XL: { position: { x: 0, y: 0 }, size: { columns: 8, rows: 8 } }
          }
        })
      })

      const composable = setup(content)

      const layout = composable.selectedLayout.value
      expect(layout['md']).toBeDefined()
      expect(layout['lg']).toBeDefined()
      expect(layout['md']!.length).toBe(1)
      expect(layout['md']![0]!.i).toBe('widget_1')
      expect(layout['md']![0]!.x).toBe(0)
      expect(layout['md']![0]!.y).toBe(0)
      expect(layout['md']![0]!.w).toBe(6)
      expect(layout['md']![0]!.h).toBe(8)
    })

    it('should merge multiple widgets into the same arrangement', () => {
      const content = makeRGContent({
        w1: makeLayoutWidget({
          default: {
            L: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } }
          }
        }),
        w2: makeLayoutWidget({
          default: {
            L: { position: { x: 6, y: 0 }, size: { columns: 6, rows: 4 } }
          }
        })
      })

      const composable = setup(content)
      const arrangement = composable.selectedLayout.value['md']!

      expect(arrangement.length).toBe(2)
      const ids = arrangement.map((e) => e.i).sort()
      expect(ids).toEqual(['w1', 'w2'])
    })

    it('should initialize empty arrangements for configured breakpoints without widgets', () => {
      const content = makeRGContent({}, ['L', 'XL'])
      const composable = setup(content)

      expect(composable.selectedLayout.value['md']).toEqual([])
      expect(composable.selectedLayout.value['lg']).toEqual([])
    })

    it('should clamp widget size to minimum from widget constraints', () => {
      const constraints: DashboardConstants['widgets'] = {
        static_text: makeWidgetConstraints({
          L: {
            minimum_size: { columns: 6, rows: 2 },
            initial_size: { columns: 6, rows: 4 }
          }
        })
      }
      const content = makeRGContent(
        {
          w1: makeLayoutWidget({
            default: {
              L: { position: { x: 0, y: 0 }, size: { columns: 3, rows: 1 } }
            }
          })
        },
        ['L']
      )

      const { composable } = setupWithConstraints(content, constraints)
      const element = composable.selectedLayout.value['md']![0]!

      expect(element.w).toBe(6) // clamped from 3
      expect(element.h).toBe(2) // clamped from 1
      expect(element.minW).toBe(6)
      expect(element.minH).toBe(2)
    })

    it('should not change size when already at or above minimum', () => {
      const constraints: DashboardConstants['widgets'] = {
        static_text: {
          filter_context: { restricted_to_single: [] },
          title_macros: [],
          layout: {
            relative: {
              initial_size: { width: 1, height: 1 },
              minimum_size: { width: 1, height: 1 },
              initial_position: { x: 0, y: 0 },
              is_resizable: true
            },
            responsive: {
              L: {
                minimum_size: { columns: 4, rows: 3 },
                initial_size: { columns: 6, rows: 4 }
              }
            }
          }
        }
      }
      const content = makeRGContent(
        {
          w1: makeLayoutWidget({
            default: {
              L: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } }
            }
          })
        },
        ['L']
      )

      const { composable } = setupWithConstraints(content, constraints)
      const element = composable.selectedLayout.value['md']![0]!

      expect(element.w).toBe(6)
      expect(element.h).toBe(4)
    })

    it('should use fallback minimums when widget type has no constraints', () => {
      const content = makeRGContent(
        {
          w1: makeLayoutWidget({
            default: {
              L: { position: { x: 0, y: 0 }, size: { columns: 2, rows: 5 } }
            }
          })
        },
        ['L']
      )

      const composable = setup(content)
      const element = composable.selectedLayout.value['md']![0]!

      // fallback for L: columns=3, rows=7
      expect(element.w).toBe(3) // clamped from 2
      expect(element.h).toBe(7) // clamped from 5
      expect(element.minW).toBe(3)
      expect(element.minH).toBe(7)
    })
  })

  describe('availableLayouts', () => {
    it('should list available layout names', () => {
      const content = makeRGContent({})
      const composable = setup(content)

      expect(composable.availableLayouts.value).toContain('default')
    })
  })

  describe('selectLayout', () => {
    it('should select an existing layout', () => {
      const content = makeRGContent({})
      const composable = setup(content)

      composable.selectLayout('default')
      expect(composable.selectedLayoutName.value).toBe('default')
    })

    it('should throw when selecting a non-existent layout', () => {
      const content = makeRGContent({})
      const composable = setup(content)

      expect(() => composable.selectLayout('nonexistent')).toThrow('does not exist')
    })
  })

  describe('updateSelectedLayout', () => {
    it('should update widget positions in the content model', () => {
      const content = makeRGContent({
        w1: makeLayoutWidget({
          default: {
            L: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } }
          }
        })
      })

      const contentRef = ref(content)
      const breakpointConfig = useInternalBreakpointConfig(breakpointSettings)
      const composable = useResponsiveGridLayout(breakpointConfig, contentRef, widgetConstraints)

      composable.updateSelectedLayout('md', [{ i: 'w1', x: 2, y: 3, w: 4, h: 5, minW: 3, minH: 8 }])

      const updatedLayout = contentRef.value.widgets['w1']!.layout.layouts['default']!['L']!
      expect(updatedLayout.position).toEqual({ x: 2, y: 3 })
      expect(updatedLayout.size).toEqual({ columns: 4, rows: 5 })
    })

    it('should warn and skip when widget is not found in content', () => {
      const content = makeRGContent({
        w1: makeLayoutWidget({
          default: {
            L: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } }
          }
        })
      })

      const contentRef = ref(content)
      const breakpointConfig = useInternalBreakpointConfig(breakpointSettings)
      const composable = useResponsiveGridLayout(breakpointConfig, contentRef, widgetConstraints)

      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      composable.updateSelectedLayout('md', [
        { i: 'nonexistent', x: 0, y: 0, w: 4, h: 4, minW: 3, minH: 8 }
      ])

      expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('nonexistent'))
      // existing widget should remain unchanged
      const w1Layout = contentRef.value.widgets['w1']!.layout.layouts['default']!['L']!
      expect(w1Layout.position).toEqual({ x: 0, y: 0 })
      expect(w1Layout.size).toEqual({ columns: 6, rows: 4 })
      warnSpy.mockRestore()
    })

    it('should handle empty arrangement without modifying content', () => {
      const content = makeRGContent({
        w1: makeLayoutWidget({
          default: {
            L: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } }
          }
        })
      })

      const contentRef = ref(content)
      const breakpointConfig = useInternalBreakpointConfig(breakpointSettings)
      const composable = useResponsiveGridLayout(breakpointConfig, contentRef, widgetConstraints)

      composable.updateSelectedLayout('md', [])

      const w1Layout = contentRef.value.widgets['w1']!.layout.layouts['default']!['L']!
      expect(w1Layout.position).toEqual({ x: 0, y: 0 })
      expect(w1Layout.size).toEqual({ columns: 6, rows: 4 })
    })

    it('should update multiple widgets in one call', () => {
      const content = makeRGContent({
        w1: makeLayoutWidget({
          default: { L: { position: { x: 0, y: 0 }, size: { columns: 4, rows: 4 } } }
        }),
        w2: makeLayoutWidget({
          default: { L: { position: { x: 4, y: 0 }, size: { columns: 4, rows: 4 } } }
        }),
        w3: makeLayoutWidget({
          default: { L: { position: { x: 8, y: 0 }, size: { columns: 4, rows: 4 } } }
        })
      })

      const contentRef = ref(content)
      const breakpointConfig = useInternalBreakpointConfig(breakpointSettings)
      const composable = useResponsiveGridLayout(breakpointConfig, contentRef, widgetConstraints)

      composable.updateSelectedLayout('md', [
        { i: 'w1', x: 0, y: 4, w: 6, h: 3, minW: 3, minH: 8 },
        { i: 'w2', x: 6, y: 4, w: 6, h: 3, minW: 3, minH: 8 },
        { i: 'w3', x: 0, y: 7, w: 12, h: 2, minW: 3, minH: 8 }
      ])

      expect(contentRef.value.widgets['w1']!.layout.layouts['default']!['L']!.position).toEqual({
        x: 0,
        y: 4
      })
      expect(contentRef.value.widgets['w2']!.layout.layouts['default']!['L']!.size).toEqual({
        columns: 6,
        rows: 3
      })
      expect(contentRef.value.widgets['w3']!.layout.layouts['default']!['L']!.position).toEqual({
        x: 0,
        y: 7
      })
    })
  })

  describe('cloneWidgetLayout', () => {
    it('should clone the layout of an existing widget with a new position', () => {
      const content = makeRGContent({
        w1: makeLayoutWidget({
          default: {
            L: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 8 } },
            XL: { position: { x: 0, y: 0 }, size: { columns: 8, rows: 8 } }
          }
        })
      })

      const composable = setup(content)
      const clonedLayout = composable.cloneWidgetLayout('w1')

      expect(clonedLayout).not.toBeNull()
      expect(clonedLayout!.type).toBe('responsive_grid')

      const clonedBreakpoint = clonedLayout!.layouts['default']!['L']!
      expect(clonedBreakpoint.size).toEqual({ columns: 6, rows: 8 })
      expect(clonedBreakpoint.position).toBeDefined()
    })

    it('should return null if the widget does not exist', () => {
      const content = makeRGContent({
        w1: makeLayoutWidget({
          default: {
            L: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } },
            XL: { position: { x: 0, y: 0 }, size: { columns: 8, rows: 4 } }
          }
        })
      })

      const composable = setup(content)
      expect(composable.cloneWidgetLayout('nonexistent')).toBeNull()
    })

    it('should return null if widget is missing from one breakpoint', () => {
      // w1 only has L layout, but content is configured for L and XL
      const content = makeRGContent({
        w1: makeLayoutWidget({
          default: {
            L: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } }
          }
        })
      })

      const composable = setup(content)
      expect(composable.cloneWidgetLayout('w1')).toBeNull()
    })

    it('should place cloned widget at a different position than original', () => {
      const content = makeRGContent(
        {
          w1: makeLayoutWidget({
            default: {
              L: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } }
            }
          })
        },
        ['L']
      )

      const composable = setup(content)
      const clonedLayout = composable.cloneWidgetLayout('w1')

      expect(clonedLayout).not.toBeNull()
      const clonedPos = clonedLayout!.layouts['default']!['L']!.position
      // original is at (0,0) with size 6x4, so clone must be elsewhere
      expect(clonedPos).not.toEqual({ x: 0, y: 0 })
    })
  })

  describe('multiple named layouts', () => {
    it('should compute layouts for multiple named layouts', () => {
      const content = makeRGContent(
        {
          w1: makeLayoutWidget({
            default: {
              L: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } }
            },
            secondary: {
              XL: { position: { x: 0, y: 0 }, size: { columns: 12, rows: 6 } }
            }
          })
        },
        ['L'],
        {
          default: { title: 'Default', breakpoints: ['L'] },
          secondary: { title: 'Secondary', breakpoints: ['XL'] }
        }
      )

      const composable = setup(content)

      expect(composable.availableLayouts.value).toContain('default')
      expect(composable.availableLayouts.value).toContain('secondary')

      const defaultLayout = composable.layouts.value['default']!
      expect(defaultLayout['md']!.length).toBe(1)
      expect(defaultLayout['md']![0]!.w).toBe(6)

      const secondaryLayout = composable.layouts.value['secondary']!
      expect(secondaryLayout['lg']!.length).toBe(1)
      expect(secondaryLayout['lg']![0]!.w).toBe(12)
    })

    it('should have empty arrangements when widget is only in one layout', () => {
      const content = makeRGContent(
        {
          w1: makeLayoutWidget({
            default: {
              L: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } }
            }
          })
        },
        ['L'],
        {
          default: { title: 'Default', breakpoints: ['L'] },
          secondary: { title: 'Secondary', breakpoints: ['L'] }
        }
      )

      const composable = setup(content)
      composable.selectLayout('secondary')
      // w1 has no layout data for 'secondary', so it shouldn't appear there
      expect(composable.selectedLayout.value['md']).toEqual([])
    })

    it('should switch to the selected layout', () => {
      const content = makeRGContent(
        {
          w1: makeLayoutWidget({
            default: {
              L: { position: { x: 0, y: 0 }, size: { columns: 4, rows: 8 } }
            },
            secondary: {
              L: { position: { x: 1, y: 1 }, size: { columns: 8, rows: 10 } }
            }
          })
        },
        ['L'],
        {
          default: { title: 'Default', breakpoints: ['L'] },
          secondary: { title: 'Secondary', breakpoints: ['L'] }
        }
      )

      const composable = setup(content)
      expect(composable.selectedLayoutName.value).toBe('default')
      expect(composable.selectedLayout.value['md']!.length).toBe(1)
      const defaultWidgetLayout = composable.selectedLayout.value['md']![0]!
      expect(defaultWidgetLayout.w).toBe(4)
      expect(defaultWidgetLayout.h).toBe(8)

      composable.selectLayout('secondary')
      expect(composable.selectedLayoutName.value).toBe('secondary')
      expect(composable.selectedLayout.value['md']!.length).toBe(1)
      const secondaryWidgetLayout = composable.selectedLayout.value['md']![0]!
      expect(secondaryWidgetLayout.w).toBe(8)
      expect(secondaryWidgetLayout.h).toBe(10)
    })
  })

  describe('reactivity', () => {
    it('should reflect added widgets in selectedLayout', () => {
      const content = makeRGContent({}, ['L'])
      const contentRef = ref(content)
      const breakpointConfig = useInternalBreakpointConfig(breakpointSettings)
      const composable = useResponsiveGridLayout(breakpointConfig, contentRef, widgetConstraints)

      expect(composable.selectedLayout.value['md']).toEqual([])

      contentRef.value.widgets['w1'] = makeLayoutWidget({
        default: {
          L: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } }
        }
      })

      expect(composable.selectedLayout.value['md']!.length).toBe(1)
      expect(composable.selectedLayout.value['md']![0]!.i).toBe('w1')
    })

    it('should update availableLayouts when content changes', () => {
      const content = makeRGContent({}, ['L'])
      const contentRef = ref(content)
      const breakpointConfig = useInternalBreakpointConfig(breakpointSettings)
      const composable = useResponsiveGridLayout(breakpointConfig, contentRef, widgetConstraints)

      expect(composable.availableLayouts.value).toEqual(['default'])

      contentRef.value = makeRGContent({}, ['L'], {
        default: { title: 'Default', breakpoints: ['L'] },
        extra: { title: 'Extra', breakpoints: ['L'] }
      })

      expect(composable.availableLayouts.value).toContain('default')
      expect(composable.availableLayouts.value).toContain('extra')
    })
  })

  describe('enforce constraints on content type change', () => {
    it('should resize widget when content type changes to a type with larger minimums', async () => {
      const constraints: DashboardConstants['widgets'] = {
        static_text: makeWidgetConstraints({
          L: { minimum_size: { columns: 3, rows: 2 }, initial_size: { columns: 4, rows: 3 } }
        }),
        gauge: makeWidgetConstraints({
          L: { minimum_size: { columns: 8, rows: 6 }, initial_size: { columns: 10, rows: 8 } }
        })
      }
      const content = makeRGContent(
        {
          w1: makeLayoutWidget({
            default: {
              L: { position: { x: 0, y: 0 }, size: { columns: 4, rows: 3 } }
            }
          })
        },
        ['L']
      )

      const { composable, contentRef } = setupWithConstraints(content, constraints)
      expect(composable.selectedLayout.value['md']![0]!.w).toBe(4)

      contentRef.value.widgets['w1']!.content.type = 'gauge'
      await nextTick()

      const layout = contentRef.value.widgets['w1']!.layout.layouts['default']!['L']!
      expect(layout.size.columns).toBe(8)
      expect(layout.size.rows).toBe(6)
    })

    it('should not mutate layout when current size already meets new type minimums', async () => {
      const constraints: DashboardConstants['widgets'] = {
        static_text: makeWidgetConstraints({
          L: { minimum_size: { columns: 3, rows: 2 }, initial_size: { columns: 6, rows: 4 } }
        }),
        gauge: makeWidgetConstraints({
          L: { minimum_size: { columns: 4, rows: 3 }, initial_size: { columns: 6, rows: 4 } }
        })
      }
      const content = makeRGContent(
        {
          w1: makeLayoutWidget({
            default: {
              L: { position: { x: 2, y: 3 }, size: { columns: 6, rows: 4 } }
            }
          })
        },
        ['L']
      )

      const { contentRef } = setupWithConstraints(content, constraints)

      contentRef.value.widgets['w1']!.content.type = 'gauge'
      await nextTick()

      const layout = contentRef.value.widgets['w1']!.layout.layouts['default']!['L']!
      expect(layout.size).toEqual({ columns: 6, rows: 4 })
      expect(layout.position).toEqual({ x: 2, y: 3 })
    })

    it('should enforce constraints across multiple breakpoints', async () => {
      const constraints: DashboardConstants['widgets'] = {
        static_text: makeWidgetConstraints({
          L: { minimum_size: { columns: 3, rows: 2 }, initial_size: { columns: 4, rows: 3 } },
          XL: { minimum_size: { columns: 3, rows: 2 }, initial_size: { columns: 6, rows: 4 } }
        }),
        gauge: makeWidgetConstraints({
          L: { minimum_size: { columns: 6, rows: 5 }, initial_size: { columns: 8, rows: 6 } },
          XL: { minimum_size: { columns: 10, rows: 8 }, initial_size: { columns: 12, rows: 10 } }
        })
      }
      const content = makeRGContent(
        {
          w1: makeLayoutWidget({
            default: {
              L: { position: { x: 0, y: 0 }, size: { columns: 4, rows: 3 } },
              XL: { position: { x: 0, y: 0 }, size: { columns: 6, rows: 4 } }
            }
          })
        },
        ['L', 'XL']
      )

      const { contentRef } = setupWithConstraints(content, constraints)

      contentRef.value.widgets['w1']!.content.type = 'gauge'
      await nextTick()

      const layoutL = contentRef.value.widgets['w1']!.layout.layouts['default']!['L']!
      expect(layoutL.size.columns).toBe(6)
      expect(layoutL.size.rows).toBe(5)

      const layoutXL = contentRef.value.widgets['w1']!.layout.layouts['default']!['XL']!
      expect(layoutXL.size.columns).toBe(10)
      expect(layoutXL.size.rows).toBe(8)
    })

    it('should reposition widget to avoid overlap when it grows', async () => {
      const constraints: DashboardConstants['widgets'] = {
        static_text: makeWidgetConstraints({
          L: { minimum_size: { columns: 2, rows: 2 }, initial_size: { columns: 3, rows: 3 } }
        }),
        gauge: makeWidgetConstraints({
          L: { minimum_size: { columns: 8, rows: 4 }, initial_size: { columns: 8, rows: 4 } }
        })
      }
      // w1 is small, w2 occupies columns 3-11 in row 0
      // when w1 grows to 8 columns, it can't fit in row 0 next to w2
      const content = makeRGContent(
        {
          w1: makeLayoutWidget({
            default: {
              L: { position: { x: 0, y: 0 }, size: { columns: 3, rows: 3 } }
            }
          }),
          w2: makeLayoutWidget({
            default: {
              L: { position: { x: 3, y: 0 }, size: { columns: 9, rows: 4 } }
            }
          })
        },
        ['L']
      )

      const { contentRef } = setupWithConstraints(content, constraints)

      contentRef.value.widgets['w1']!.content.type = 'gauge'
      await nextTick()

      const layout = contentRef.value.widgets['w1']!.layout.layouts['default']!['L']!
      expect(layout.size.columns).toBe(8)
      expect(layout.size.rows).toBe(4)
      // w2 occupies (3,0)-(12,4), so w1 (8 cols wide) must go below
      expect(layout.position.y).toBeGreaterThanOrEqual(4)
    })

    it('should enforce constraints across multiple named layouts', async () => {
      const constraints: DashboardConstants['widgets'] = {
        static_text: makeWidgetConstraints({
          L: { minimum_size: { columns: 2, rows: 2 }, initial_size: { columns: 3, rows: 3 } }
        }),
        gauge: makeWidgetConstraints({
          L: { minimum_size: { columns: 6, rows: 5 }, initial_size: { columns: 6, rows: 5 } }
        })
      }
      const content = makeRGContent(
        {
          w1: makeLayoutWidget({
            default: {
              L: { position: { x: 0, y: 0 }, size: { columns: 3, rows: 3 } }
            },
            secondary: {
              L: { position: { x: 0, y: 0 }, size: { columns: 4, rows: 3 } }
            }
          })
        },
        ['L'],
        {
          default: { title: 'Default', breakpoints: ['L'] },
          secondary: { title: 'Secondary', breakpoints: ['L'] }
        }
      )

      const { contentRef } = setupWithConstraints(content, constraints)

      contentRef.value.widgets['w1']!.content.type = 'gauge'
      await nextTick()

      const defaultLayout = contentRef.value.widgets['w1']!.layout.layouts['default']!['L']!
      expect(defaultLayout.size.columns).toBe(6)
      expect(defaultLayout.size.rows).toBe(5)

      const secondaryLayout = contentRef.value.widgets['w1']!.layout.layouts['secondary']!['L']!
      expect(secondaryLayout.size.columns).toBe(6)
      expect(secondaryLayout.size.rows).toBe(5)
    })
  })
})

describe('createWidgetLayout', () => {
  const constants: DashboardConstants = {
    responsive_grid_breakpoints: breakpointSettings,
    widgets: {
      static_text: {
        filter_context: {
          restricted_to_single: []
        },
        title_macros: [],
        layout: {
          relative: {
            initial_size: { width: 1, height: 1 },
            minimum_size: { width: 1, height: 1 },
            initial_position: { x: 1, y: 1 },
            is_resizable: true
          },
          responsive: {
            L: {
              minimum_size: { columns: 2, rows: 2 },
              initial_size: { columns: 4, rows: 4 }
            },
            XL: {
              minimum_size: { columns: 2, rows: 3 },
              initial_size: { columns: 4, rows: 5 }
            }
          }
        }
      }
    }
  }

  it('should create a layout for a new widget with default sizes', () => {
    const content = makeRGContent({}, ['L', 'XL'])
    const layout = createWidgetLayout(content, 'static_text', constants)

    expect(layout.type).toBe('responsive_grid')
    expect(layout.layouts['default']).toBeDefined()
    expect(layout.layouts['default']!['L']).toBeDefined()
    expect(layout.layouts['default']!['XL']).toBeDefined()
  })

  it('should place the new widget at position (0, 0) on an empty grid', () => {
    const content = makeRGContent({}, ['L'])
    const layout = createWidgetLayout(content, 'static_text', constants)

    expect(layout.layouts['default']!['L']!.position).toEqual({ x: 0, y: 0 })
  })

  it('should place the new widget in a non-overlapping position on a populated grid', () => {
    // initial size for the widget is 4x4 on L breakpoint (12 columns total)
    const content = makeRGContent(
      {
        // first row is too short (3 < 4)
        row_1: makeLayoutWidget({
          default: {
            L: { position: { x: 0, y: 0 }, size: { columns: 4, rows: 3 } }
          }
        }),
        // take up entire second row (so we limit the first row height)
        row_2: makeLayoutWidget({
          default: {
            L: { position: { x: 0, y: 3 }, size: { columns: 12, rows: 4 } }
          }
        }),
        // take up slightly too much of the third row
        row_3: makeLayoutWidget({
          default: {
            L: { position: { x: 0, y: 7 }, size: { columns: 9, rows: 4 } }
          }
        }),
        // 1/3 of fourth row
        row_4_1: makeLayoutWidget({
          default: {
            L: { position: { x: 0, y: 11 }, size: { columns: 4, rows: 4 } }
          }
        }),
        // another 1/3 of fourth row, leaving space to the right of it
        row_4_2: makeLayoutWidget({
          default: {
            L: { position: { x: 4, y: 11 }, size: { columns: 4, rows: 4 } }
          }
        }),
        // take up entire fifth row
        row_5: makeLayoutWidget({
          default: {
            L: { position: { x: 0, y: 15 }, size: { columns: 12, rows: 4 } }
          }
        })
      },
      ['L']
    )
    const layout = createWidgetLayout(content, 'static_text', constants)
    // empty spot to the right of row_4_2, don't put it below w4
    expect(layout.layouts['default']!['L']!.position).toEqual({ x: 8, y: 11 })
  })

  it('should use widget constraints for minimum and initial sizes', () => {
    const content = makeRGContent({}, ['L', 'XL'])
    const layout = createWidgetLayout(content, 'static_text', constants)

    expect(layout.layouts['default']!['L']!.size).toEqual({ columns: 4, rows: 4 })
    expect(layout.layouts['default']!['XL']!.size).toEqual({ columns: 4, rows: 5 })
  })

  it('should use fallback sizes when widget type has no constraints', () => {
    const content = makeRGContent({}, ['L', 'XL'])
    // 'unknown_widget' is not in constants.widgets
    const layout = createWidgetLayout(content, 'unknown_widget', constants)

    // fallback for L/XL: columns=3, rows=7
    expect(layout.layouts['default']!['L']!.size).toEqual({ columns: 3, rows: 7 })
    expect(layout.layouts['default']!['XL']!.size).toEqual({ columns: 3, rows: 7 })
  })

  it('should fall back when breakpoint is missing from widget constraints', () => {
    // constants define responsive layout only for L and XL, but dashboard uses M too
    const content = makeRGContent({}, ['M', 'L'])
    const layout = createWidgetLayout(content, 'static_text', constants)

    // M is not defined in static_text responsive constraints, so falls back
    // For M breakpoint (not L/XL), fallback is columns=4, rows=7
    expect(layout.layouts['default']!['M']!.size).toEqual({ columns: 4, rows: 7 })
    // L is defined with initial_size
    expect(layout.layouts['default']!['L']!.size).toEqual({ columns: 4, rows: 4 })
  })
})
