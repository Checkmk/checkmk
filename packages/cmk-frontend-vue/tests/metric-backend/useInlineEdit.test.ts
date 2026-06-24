/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import type { Ref } from 'vue'
import { defineComponent, h, nextTick, ref, useTemplateRef } from 'vue'

import useInlineEdit from '@/metric-backend/useInlineEdit'

// Mount a host that drives the composable and renders a real pane element bound
// to the `paneRef` template ref it passes in, so the document mousedown-capture
// listener fires and `paneRef.value.contains(...)` resolves against an attached
// DOM subtree.
function mountEditor(open: Ref<boolean>) {
  const onLeave = vi.fn()
  let api!: ReturnType<typeof useInlineEdit>
  const host = defineComponent({
    setup() {
      const paneRef = useTemplateRef<HTMLElement>('editPaneRef')
      api = useInlineEdit({ isOpen: () => open.value, paneRef, onLeave })
      return () =>
        open.value
          ? h('div', { ref: 'editPaneRef', 'data-pane': '' }, [h('span', { 'data-inside': '' })])
          : null
    }
  })
  render(host)
  return { api, onLeave }
}

function inside(): HTMLElement {
  return document.querySelector<HTMLElement>('[data-pane] [data-inside]')!
}

describe('useInlineEdit', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  test('does not leave on the opening click tail bubble, only once armed', async () => {
    const open = ref(false)
    const { api, onLeave } = mountEditor(open)

    open.value = true
    await nextTick()

    // The click that opened the editor keeps bubbling; before the arm timer
    // fires it must not count as the editor's own first leave.
    api.onOutsideClick()
    expect(onLeave).not.toHaveBeenCalled()

    vi.advanceTimersByTime(0)
    api.onOutsideClick()
    expect(onLeave).toHaveBeenCalledTimes(1)
    expect(onLeave).toHaveBeenCalledWith('outside')
  })

  test('suppresses an outside click whose mousedown started inside the pane', () => {
    const open = ref(true)
    const { api, onLeave } = mountEditor(open)
    vi.advanceTimersByTime(0) // arm

    inside().dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
    api.onOutsideClick()
    expect(onLeave).not.toHaveBeenCalled()

    // A subsequent click that started outside still leaves.
    document.body.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
    api.onOutsideClick()
    expect(onLeave).toHaveBeenCalledTimes(1)
    expect(onLeave).toHaveBeenCalledWith('outside')
  })

  test('lets an open dropdown swallow Escape instead of leaving', () => {
    const open = ref(true)
    const { api, onLeave } = mountEditor(open)
    inside().setAttribute('aria-expanded', 'true')

    api.onEscapeCapture()
    api.onEscape()
    expect(onLeave).not.toHaveBeenCalled()

    // With no dropdown open, the next Escape leaves the editor.
    inside().removeAttribute('aria-expanded')
    api.onEscapeCapture()
    api.onEscape()
    expect(onLeave).toHaveBeenCalledTimes(1)
    expect(onLeave).toHaveBeenCalledWith('escape')
  })
})
