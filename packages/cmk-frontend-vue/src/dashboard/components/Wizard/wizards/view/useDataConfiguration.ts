/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { randomId } from 'cmk-ui-library/lib/randomId'
import { shallowRef } from 'vue'

import type { CopyExistingViewSelection, NewViewSelection } from './types'
import { ViewSelectionMode } from './types'

export type DataConfiguration =
  | { mode: 'create'; embeddedId: string; datasource: string; restrictedToSingle: string[] }
  | { mode: 'copy'; embeddedId: string; viewName: string }
  | { mode: 'edit'; embeddedId: string }

/** Tracks the embedded view that the data configuration stage of the view wizard writes. */
export function useDataConfiguration(editedEmbeddedId: string | undefined) {
  const configuration = shallowRef<DataConfiguration | null>(null)

  function startNewView(selection: NewViewSelection | CopyExistingViewSelection): void {
    configuration.value =
      selection.type === ViewSelectionMode.NEW
        ? {
            mode: 'create',
            embeddedId: randomId(),
            datasource: selection.datasource,
            restrictedToSingle: selection.restrictedToSingle
          }
        : { mode: 'copy', embeddedId: randomId(), viewName: selection.viewName }
  }

  function openForEdit(): void {
    const embeddedId = configuration.value?.embeddedId ?? editedEmbeddedId
    if (!embeddedId) {
      throw new Error('The widget has no embedded view')
    }
    configuration.value = { mode: 'edit', embeddedId }
  }

  return { configuration, startNewView, openForEdit }
}
