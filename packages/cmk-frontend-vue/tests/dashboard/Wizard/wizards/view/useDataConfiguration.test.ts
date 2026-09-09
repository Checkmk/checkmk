/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import type {
  CopyExistingViewSelection,
  NewViewSelection
} from '@/dashboard/components/Wizard/wizards/view/types'
import { ViewSelectionMode } from '@/dashboard/components/Wizard/wizards/view/types'
import { useDataConfiguration } from '@/dashboard/components/Wizard/wizards/view/useDataConfiguration'
import type { EmbeddedViewContent, LinkedViewContent } from '@/dashboard/types/widget'

const newView: NewViewSelection = {
  type: ViewSelectionMode.NEW,
  datasource: 'hosts',
  restrictedToSingle: ['host']
}

const copiedView: CopyExistingViewSelection = {
  type: ViewSelectionMode.COPY,
  viewName: 'allhosts'
}

function embeddedView(embeddedId: string): EmbeddedViewContent {
  return {
    type: 'embedded_view',
    embedded_id: embeddedId,
    datasource: 'hosts',
    restricted_to_single: []
  }
}

function noContent() {
  return ref<EmbeddedViewContent | LinkedViewContent | undefined>(undefined)
}

describe('startNewView', () => {
  it('creates a view from the selected data source', () => {
    const { configuration, startNewView } = useDataConfiguration(noContent())

    startNewView(newView)

    expect(configuration.value).toEqual({
      mode: 'create',
      embeddedId: expect.any(String),
      datasource: 'hosts',
      restrictedToSingle: ['host']
    })
  })

  it('copies the selected view', () => {
    const { configuration, startNewView } = useDataConfiguration(noContent())

    startNewView(copiedView)

    expect(configuration.value).toEqual({
      mode: 'copy',
      embeddedId: expect.any(String),
      viewName: 'allhosts'
    })
  })

  it('uses a new embedded view for every selection', () => {
    const { configuration, startNewView } = useDataConfiguration(noContent())

    startNewView(newView)
    const firstId = configuration.value!.embeddedId
    startNewView(newView)

    expect(configuration.value!.embeddedId).not.toBe(firstId)
  })
})

describe('duplicateCurrentView', () => {
  it('duplicates the view of the widget into a new one', () => {
    const content = ref(embeddedView('view-of-the-widget'))
    const { configuration, duplicateCurrentView } = useDataConfiguration(content)

    duplicateCurrentView()

    expect(configuration.value).toEqual({
      mode: 'duplicate',
      embeddedId: expect.any(String),
      sourceEmbeddedId: 'view-of-the-widget'
    })
    expect(configuration.value!.embeddedId).not.toBe('view-of-the-widget')
  })

  it('duplicates the view that the widget got in the previous stage', () => {
    const content = ref(embeddedView('view-of-the-widget'))
    const { configuration, duplicateCurrentView } = useDataConfiguration(content)

    content.value = embeddedView('view-of-the-previous-stage')
    duplicateCurrentView()

    expect(configuration.value).toEqual({
      mode: 'duplicate',
      embeddedId: expect.any(String),
      sourceEmbeddedId: 'view-of-the-previous-stage'
    })
  })

  it('keeps the source when the previous stage saved nothing', () => {
    const content = ref(embeddedView('view-of-the-widget'))
    const { configuration, duplicateCurrentView } = useDataConfiguration(content)

    duplicateCurrentView()
    const plannedId = configuration.value!.embeddedId
    duplicateCurrentView()

    expect(configuration.value).toEqual({
      mode: 'duplicate',
      embeddedId: expect.any(String),
      sourceEmbeddedId: 'view-of-the-widget'
    })
    expect(configuration.value!.embeddedId).not.toBe(plannedId)
  })

  it('refuses a widget without content', () => {
    const { duplicateCurrentView } = useDataConfiguration(noContent())

    expect(() => duplicateCurrentView()).toThrow('The widget has no embedded view')
  })

  it('refuses a widget that links a view', () => {
    const content = ref<LinkedViewContent>({ type: 'linked_view', view_name: 'allhosts' })
    const { duplicateCurrentView } = useDataConfiguration(content)

    expect(() => duplicateCurrentView()).toThrow('The widget has no embedded view')
  })
})
