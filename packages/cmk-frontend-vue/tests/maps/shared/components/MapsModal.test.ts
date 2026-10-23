/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import MapsModal from '@/maps/shared/components/MapsModal.vue'

import { mapsGlobal } from '../../support/services'

function anOpener(): HTMLButtonElement {
  const opener = document.createElement('button')
  opener.textContent = 'Open'
  document.body.appendChild(opener)
  opener.focus()
  return opener
}

describe('MapsModal', () => {
  it('takes focus when it is mounted open', async () => {
    const opener = anOpener()

    render(MapsModal, {
      props: { open: true, title: untranslated('Add comment') },
      global: mapsGlobal()
    })

    const dialog = await screen.findByRole('dialog', { name: 'Add comment' })
    await waitFor(() => expect(dialog).toHaveFocus())
    opener.remove()
  })

  it('hands focus back to what opened it when it goes away', async () => {
    const opener = anOpener()
    const { unmount } = render(MapsModal, {
      props: { open: true, title: untranslated('Add comment') },
      global: mapsGlobal()
    })
    const dialog = await screen.findByRole('dialog', { name: 'Add comment' })
    await waitFor(() => expect(dialog).toHaveFocus())

    unmount()

    expect(opener).toHaveFocus()
    opener.remove()
  })

  it('hands focus back when a button inside it closes it', async () => {
    const user = userEvent.setup()
    const opener = anOpener()
    const host = defineComponent({
      setup() {
        const open = ref(true)
        return () =>
          open.value
            ? h(
                MapsModal,
                { open: true, title: untranslated('Add comment') },
                { default: () => h('button', { onClick: () => (open.value = false) }, 'Cancel') }
              )
            : null
      }
    })
    render(host, { global: mapsGlobal() })
    const dialog = await screen.findByRole('dialog', { name: 'Add comment' })
    await waitFor(() => expect(dialog).toHaveFocus())

    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    await waitFor(() => expect(opener).toHaveFocus())
    opener.remove()
  })
})
