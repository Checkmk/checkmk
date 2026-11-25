/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { pressDismissesPopup } from 'cmk-ui-library/lib/popupDismissal'
import useClickOutside from 'cmk-ui-library/lib/useClickOutside'
import { defineComponent } from 'vue'

function renderPopup(open: boolean): void {
  render(
    defineComponent({
      directives: { clickOutside: useClickOutside() },
      setup: () => ({ open, close: () => {} }),
      template: `
        <div>
          <div v-click-outside="{ open, close }">popup</div>
          <button>behind</button>
        </div>
      `
    })
  )
}

function click(target: Element, detail = 1): MouseEvent {
  target.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }))
  return new MouseEvent('click', { detail })
}

test.each([
  { open: true, target: 'behind', detail: 1, dismisses: true },
  { open: false, target: 'behind', detail: 1, dismisses: false },
  { open: true, target: 'popup', detail: 1, dismisses: false },
  { open: true, target: 'behind', detail: 0, dismisses: false }
])(
  'a click on $target with the popup open: $open, detail $detail dismisses: $dismisses',
  ({ open, target, detail, dismisses }) => {
    renderPopup(open)

    expect(pressDismissesPopup(click(screen.getByText(target), detail))).toBe(dismisses)
  }
)
