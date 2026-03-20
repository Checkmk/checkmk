/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import PopupDialog from '@/dashboard/components/PopupDialog.vue'

// radix-vue DialogPortal renders outside the jsdom document body hierarchy,
// so we stub all Dialog* primitives to render their children inline.
vi.mock('radix-vue', () => ({
  DialogRoot: defineComponent({
    name: 'DialogRoot',
    props: { open: Boolean },
    setup(props, { slots }) {
      return () =>
        props.open ? h('div', { 'data-testid': 'dialog-root' }, slots.default?.()) : null
    }
  }),
  DialogPortal: defineComponent({
    name: 'DialogPortal',
    setup(_, { slots }) {
      return () => h('div', slots.default?.())
    }
  }),
  DialogOverlay: defineComponent({
    name: 'DialogOverlay',
    setup(_, { slots, attrs }) {
      return () => h('div', { 'data-testid': 'dialog-overlay', ...attrs }, slots.default?.())
    }
  }),
  DialogContent: defineComponent({
    name: 'DialogContent',
    setup(_, { slots, attrs }) {
      return () => h('div', { 'data-testid': 'dialog-content', ...attrs }, slots.default?.())
    }
  })
}))

function renderPopupDialog(props: Record<string, unknown> = {}) {
  return render(PopupDialog, { props: { open: true, message: 'Test message', ...props } })
}

describe('PopupDialog', () => {
  describe('Rendering', () => {
    it('renders nothing when open=false', () => {
      renderPopupDialog({ open: false })
      expect(screen.queryByTestId('dialog-root')).not.toBeInTheDocument()
    })

    it('renders the dialog when open=true', () => {
      renderPopupDialog()
      expect(screen.getByTestId('dialog-root')).toBeInTheDocument()
    })

    it('renders the title when provided', () => {
      renderPopupDialog({ title: 'My Title' })
      expect(screen.getByText('My Title')).toBeInTheDocument()
    })

    it('does not render a title span when title is not provided', () => {
      renderPopupDialog()
      expect(screen.queryByText('My Title')).not.toBeInTheDocument()
    })

    it('renders a single message', () => {
      renderPopupDialog({ message: 'Hello world' })
      expect(screen.getByText('Hello world')).toBeInTheDocument()
    })

    it('renders multiple message paragraphs from an array', () => {
      renderPopupDialog({ message: ['First paragraph', 'Second paragraph'] })
      expect(screen.getByText('First paragraph')).toBeInTheDocument()
      expect(screen.getByText('Second paragraph')).toBeInTheDocument()
    })

    it('renders action buttons with correct labels', () => {
      renderPopupDialog({
        buttons: [
          { title: 'Confirm' as const, variant: 'primary', onclick: vi.fn() },
          { title: 'Cancel' as const, variant: 'secondary', onclick: vi.fn() }
        ]
      })
      expect(screen.getByRole('button', { name: 'Confirm' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
    })

    it('renders the dismissal button when provided', () => {
      renderPopupDialog({ dismissal_button: { title: 'Dismiss' as const, key: 'dismiss' } })
      expect(screen.getByRole('button', { name: 'Dismiss' })).toBeInTheDocument()
    })

    it('does not render the dismissal button when not provided', () => {
      renderPopupDialog()
      expect(screen.queryByRole('button', { name: 'Dismiss' })).not.toBeInTheDocument()
    })

    it('renders slot preContent when provided', () => {
      const wrapper = defineComponent({
        components: { PopupDialog },
        template: `
          <PopupDialog :open="true" message="msg">
            <template #preContent><span data-testid="pre-slot">pre</span></template>
          </PopupDialog>
        `
      })
      render(wrapper)
      expect(screen.getByTestId('pre-slot')).toBeInTheDocument()
    })

    it('renders slot postContent when provided', () => {
      const wrapper = defineComponent({
        components: { PopupDialog },
        template: `
          <PopupDialog :open="true" message="msg">
            <template #postContent><span data-testid="post-slot">post</span></template>
          </PopupDialog>
        `
      })
      render(wrapper)
      expect(screen.getByTestId('post-slot')).toBeInTheDocument()
    })
  })

  describe('Variant CSS classes', () => {
    it.each(['info', 'warning', 'danger', 'success'] as const)(
      'applies db-popup-dialog__container-%s class for variant=%s',
      (variant) => {
        renderPopupDialog({ variant })
        const content = screen.getByTestId('dialog-content')
        expect(content.className).toContain(`db-popup-dialog__container-${variant}`)
      }
    )

    it('does not apply a variant class when variant is not provided', () => {
      renderPopupDialog()
      const content = screen.getByTestId('dialog-content')
      expect(content.className).not.toMatch(
        /db-popup-dialog__container-(info|warning|danger|success)/
      )
    })
  })

  describe('Emits', () => {
    it('emits close when the close icon is clicked', async () => {
      const { emitted } = renderPopupDialog()
      // The close icon is rendered via CmkIcon with @click="emit('close')"
      const closeIcon = document.querySelector('.cmk-icon')
      expect(closeIcon).toBeTruthy()
      await fireEvent.click(closeIcon!)
      expect(emitted()['close']).toHaveLength(1)
    })

    it('emits close when the overlay is clicked', async () => {
      const { emitted } = renderPopupDialog()
      await fireEvent.click(screen.getByTestId('dialog-overlay'))
      expect(emitted()['close']).toHaveLength(1)
    })

    it('emits close when the dismissal button is clicked', async () => {
      const { emitted } = renderPopupDialog({
        dismissal_button: { title: 'Dismiss' as const, key: 'dismiss' }
      })
      await fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
      expect(emitted()['close']).toHaveLength(1)
    })
  })

  describe('Button interactions', () => {
    it('calls onclick handler when an action button is clicked', async () => {
      const onclick = vi.fn()
      renderPopupDialog({ buttons: [{ title: 'Confirm' as const, variant: 'primary', onclick }] })
      await fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))
      expect(onclick).toHaveBeenCalledOnce()
    })

    it("calls each button's own onclick independently", async () => {
      const onClickA = vi.fn()
      const onClickB = vi.fn()
      renderPopupDialog({
        buttons: [
          { title: 'A' as const, variant: 'primary', onclick: onClickA },
          { title: 'B' as const, variant: 'secondary', onclick: onClickB }
        ]
      })
      await fireEvent.click(screen.getByRole('button', { name: 'B' }))
      expect(onClickB).toHaveBeenCalledOnce()
      expect(onClickA).not.toHaveBeenCalled()
    })
  })
})
