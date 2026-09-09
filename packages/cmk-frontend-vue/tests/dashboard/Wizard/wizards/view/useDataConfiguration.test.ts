/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import type {
  CopyExistingViewSelection,
  NewViewSelection
} from '@/dashboard/components/Wizard/wizards/view/types'
import { ViewSelectionMode } from '@/dashboard/components/Wizard/wizards/view/types'
import { useDataConfiguration } from '@/dashboard/components/Wizard/wizards/view/useDataConfiguration'

const newView: NewViewSelection = {
  type: ViewSelectionMode.NEW,
  datasource: 'hosts',
  restrictedToSingle: ['host']
}

const copiedView: CopyExistingViewSelection = {
  type: ViewSelectionMode.COPY,
  viewName: 'allhosts'
}

describe('startNewView', () => {
  it('creates a view from the selected data source', () => {
    const { configuration, startNewView } = useDataConfiguration(undefined)

    startNewView(newView)

    expect(configuration.value).toEqual({
      mode: 'create',
      embeddedId: expect.any(String),
      datasource: 'hosts',
      restrictedToSingle: ['host']
    })
  })

  it('copies the selected view', () => {
    const { configuration, startNewView } = useDataConfiguration(undefined)

    startNewView(copiedView)

    expect(configuration.value).toEqual({
      mode: 'copy',
      embeddedId: expect.any(String),
      viewName: 'allhosts'
    })
  })

  it('uses a new embedded view for every selection', () => {
    const { configuration, startNewView } = useDataConfiguration(undefined)

    startNewView(newView)
    const firstId = configuration.value!.embeddedId
    startNewView(newView)

    expect(configuration.value!.embeddedId).not.toBe(firstId)
  })
})

describe('openForEdit', () => {
  it('edits the embedded view of the widget', () => {
    const { configuration, openForEdit } = useDataConfiguration('view-of-the-widget')

    openForEdit()

    expect(configuration.value).toEqual({ mode: 'edit', embeddedId: 'view-of-the-widget' })
  })

  it('edits the embedded view of the previous stage', () => {
    const { configuration, startNewView, openForEdit } = useDataConfiguration(undefined)

    startNewView(newView)
    const createdId = configuration.value!.embeddedId
    openForEdit()

    expect(configuration.value).toEqual({ mode: 'edit', embeddedId: createdId })
  })

  it('refuses a widget without an embedded view', () => {
    const { openForEdit } = useDataConfiguration(undefined)

    expect(() => openForEdit()).toThrow('The widget has no embedded view')
  })
})
