/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { useProvideFilterDefinitions } from 'cmk-ui-library/components/filter'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'

import { useContextualLink } from '@/dashboard/components/Wizard/components/ContextualLink/useContextualLink'
import WidgetInteraction from '@/dashboard/components/Wizard/components/WidgetInteraction/WidgetInteraction.vue'
import type { HostStatisticsContent } from '@/dashboard/components/Wizard/types'

const controlsProps = { clickToPlacePin: true, showBurgerMenu: false }
const titleProps = { titleUrlEnabled: false, titleUrl: '' }

function renderWithContextualLink() {
  const contextualLink = useContextualLink<HostStatisticsContent>(
    { modes: ['default'], filters: [], filter_keys: {} },
    undefined
  )
  render(
    defineComponent({
      setup() {
        useProvideFilterDefinitions({ definitions: {}, groups: {} })
        return () => h(WidgetInteraction, { contextualLink })
      }
    })
  )
}

describe('WidgetInteraction', () => {
  describe('controls', () => {
    it('reflects the graph control settings', () => {
      render(WidgetInteraction, { props: controlsProps })

      expect(screen.getByRole('checkbox', { name: 'Click on graph to place pin' })).toBeChecked()
      expect(
        screen.getByRole('checkbox', { name: 'Show burger menu for graph options' })
      ).not.toBeChecked()
    })

    it('are hidden when not bound', () => {
      render(WidgetInteraction, { props: titleProps })

      expect(screen.queryByText('Controls')).not.toBeInTheDocument()
    })
  })

  describe('title link', () => {
    it('hides the link input while linking is disabled', () => {
      render(WidgetInteraction, { props: titleProps })

      expect(screen.getByRole('checkbox', { name: 'Link title to' })).not.toBeChecked()
      expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    })

    it('shows the link input while linking is enabled', () => {
      render(WidgetInteraction, { props: { ...titleProps, titleUrlEnabled: true } })

      expect(screen.getByRole('checkbox', { name: 'Link title to' })).toBeChecked()
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    it('shows validation errors for the link', () => {
      render(WidgetInteraction, {
        props: { ...titleProps, titleUrlEnabled: true, titleUrlValidationErrors: ['Invalid URL'] }
      })

      expect(screen.getByText('Invalid URL')).toBeInTheDocument()
    })

    it('is hidden when not bound', () => {
      render(WidgetInteraction, { props: controlsProps })

      expect(screen.queryByRole('checkbox', { name: 'Link title to' })).not.toBeInTheDocument()
    })
  })

  describe('read only', () => {
    it('reflects the setting when bound', () => {
      render(WidgetInteraction, { props: { ...titleProps, readOnlyTitle: true } })

      expect(screen.getByRole('checkbox', { name: 'Read only' })).toBeChecked()
    })

    it('is hidden when not bound', () => {
      render(WidgetInteraction, { props: titleProps })

      expect(screen.queryByRole('checkbox', { name: 'Read only' })).not.toBeInTheDocument()
    })
  })

  describe('contextual links', () => {
    it('are shown when a handler is bound', () => {
      renderWithContextualLink()

      expect(screen.getByText('Links to views and dashboards')).toBeInTheDocument()
    })

    it('are hidden when no handler is bound', () => {
      render(WidgetInteraction, { props: controlsProps })

      expect(screen.queryByText('Links to views and dashboards')).not.toBeInTheDocument()
    })
  })
})
