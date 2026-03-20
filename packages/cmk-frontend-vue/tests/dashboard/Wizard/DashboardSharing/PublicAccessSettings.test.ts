/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'

import PublicAccessSettings from '@/dashboard/components/Wizard/wizards/dashboard-sharing/PublicAccessSettings.vue'
import { DashboardFeatures } from '@/dashboard/types/dashboard'

function renderPublicSettings(options: {
  hasValidity?: boolean
  validUntil?: Date | null
  comment?: string
  validate?: () => boolean
  validationError?: string[]
  dashboardFeatures?: DashboardFeatures
}) {
  const hasValidity = ref(options.hasValidity ?? false)
  const validUntil = ref<Date | null>(options.validUntil ?? null)
  const comment = ref(options.comment ?? '')
  const validate = options.validate ?? (() => true)
  const validationError = options.validationError ?? []
  const dashboardFeatures = options.dashboardFeatures ?? DashboardFeatures.UNRESTRICTED

  const wrapper = defineComponent({
    components: { PublicAccessSettings },
    emits: ['updateSettings'],
    setup() {
      return { hasValidity, validUntil, comment, validate, validationError, dashboardFeatures }
    },
    template: `
      <PublicAccessSettings
        v-model:has-validity="hasValidity"
        v-model:valid-until="validUntil"
        v-model:comment="comment"
        :validate="validate"
        :validation-error="validationError"
        :dashboard-features="dashboardFeatures"
        @update-settings="$emit('updateSettings')"
      />
    `
  })

  const result = render(wrapper)
  return { ...result, hasValidity, validUntil, comment }
}

describe('PublicAccessSettings', () => {
  describe('Rendering', () => {
    it('renders the "Link settings" heading', () => {
      renderPublicSettings({})
      expect(screen.getByText('Link settings')).toBeInTheDocument()
    })

    it('renders the "Set expiration date" checkbox', () => {
      renderPublicSettings({})
      expect(screen.getByRole('checkbox', { name: 'Set expiration date' })).toBeInTheDocument()
    })

    it('renders the "Save changes" button', () => {
      renderPublicSettings({})
      expect(screen.getByRole('button', { name: 'Save changes' })).toBeInTheDocument()
    })

    it('renders the comment input field', () => {
      renderPublicSettings({})
      expect(
        screen.getByPlaceholderText('Internal comment, not visible to viewers')
      ).toBeInTheDocument()
    })

    it('does not render the date input when hasValidity=false', () => {
      renderPublicSettings({ hasValidity: false })
      expect(screen.queryByRole('textbox', { name: /expiration/i })).not.toBeInTheDocument()
      expect(document.querySelector('input[type="date"]')).not.toBeInTheDocument()
    })

    it('renders the date input when hasValidity=true', () => {
      renderPublicSettings({ hasValidity: true, validUntil: new Date('2030-01-15') })
      expect(document.querySelector('input[type="date"]')).toBeInTheDocument()
    })
  })

  describe('RESTRICTED feature tier', () => {
    it('renders the checkbox as disabled in RESTRICTED mode', () => {
      renderPublicSettings({ dashboardFeatures: DashboardFeatures.RESTRICTED })
      const checkbox = screen.getByRole('checkbox', { name: 'Set expiration date' })
      expect(checkbox).toBeDisabled()
    })

    it('checkbox is not disabled in UNRESTRICTED mode', () => {
      renderPublicSettings({ dashboardFeatures: DashboardFeatures.UNRESTRICTED })
      const checkbox = screen.getByRole('checkbox', { name: 'Set expiration date' })
      expect(checkbox).not.toBeDisabled()
    })
  })

  describe('Checkbox toggles date field', () => {
    it('shows the date input after checking the validity checkbox', async () => {
      renderPublicSettings({ hasValidity: false })

      expect(document.querySelector('input[type="date"]')).not.toBeInTheDocument()

      await userEvent.click(screen.getByRole('checkbox', { name: 'Set expiration date' }))

      expect(document.querySelector('input[type="date"]')).toBeInTheDocument()
    })

    it('hides the date input after unchecking the validity checkbox', async () => {
      renderPublicSettings({ hasValidity: true, validUntil: new Date('2030-01-15') })

      expect(document.querySelector('input[type="date"]')).toBeInTheDocument()

      await userEvent.click(screen.getByRole('checkbox', { name: 'Set expiration date' }))

      expect(document.querySelector('input[type="date"]')).not.toBeInTheDocument()
    })
  })

  describe('Save changes', () => {
    it('emits updateSettings and shows success message when validate() returns true', async () => {
      const validate = vi.fn(() => true)
      const { emitted } = renderPublicSettings({ validate })

      await fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

      await nextTick()

      expect(validate).toHaveBeenCalledOnce()
      expect(await screen.findByText('Link settings saved.')).toBeInTheDocument()
      expect(emitted()['updateSettings']).toHaveLength(1)
    })

    it('does not emit updateSettings and hides success message when validate() returns false', async () => {
      const validate = vi.fn(() => false)
      const { emitted } = renderPublicSettings({ validate })

      await fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

      expect(validate).toHaveBeenCalledOnce()
      expect(emitted()['updateSettings']).toBeUndefined()
      expect(screen.queryByText('Link settings saved.')).not.toBeInTheDocument()
    })

    it('hides the success message when the user changes the comment after saving', async () => {
      const validate = vi.fn(() => true)
      renderPublicSettings({ validate })

      // Save successfully
      await fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
      expect(await screen.findByText('Link settings saved.')).toBeInTheDocument()

      // Modify comment — success message should disappear
      const commentInput = screen.getByPlaceholderText('Internal comment, not visible to viewers')
      await userEvent.type(commentInput, 'x')

      expect(screen.queryByText('Link settings saved.')).not.toBeInTheDocument()
    })

    it('hides the success message when the checkbox is toggled after saving', async () => {
      const validate = vi.fn(() => true)
      renderPublicSettings({ validate, hasValidity: false })

      await fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
      expect(await screen.findByText('Link settings saved.')).toBeInTheDocument()

      await userEvent.click(screen.getByRole('checkbox', { name: 'Set expiration date' }))

      expect(screen.queryByText('Link settings saved.')).not.toBeInTheDocument()
    })
  })

  describe('Validation error display', () => {
    it('shows external validation error on the date input', () => {
      renderPublicSettings({
        hasValidity: true,
        validUntil: new Date('2020-01-01'),
        validationError: ['Expiration date cannot be in the past.']
      })

      expect(screen.getByText('Expiration date cannot be in the past.')).toBeInTheDocument()
    })
  })

  describe('v-model bindings', () => {
    it('pre-fills the date input with the formatted validUntil date', () => {
      renderPublicSettings({ hasValidity: true, validUntil: new Date('2030-06-15T12:00:00') })
      const dateInput = document.querySelector('input[type="date"]') as HTMLInputElement
      expect(dateInput.value).toBe('2030-06-15')
    })

    it('updates the comment ref when the user types in the comment field', async () => {
      const { comment } = renderPublicSettings({ comment: '' })
      const commentInput = screen.getByPlaceholderText('Internal comment, not visible to viewers')

      await userEvent.type(commentInput, 'hello')

      expect(comment.value).toContain('hello')
    })
  })
})
