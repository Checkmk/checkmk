/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { randomId } from 'cmk-ui-library/lib/randomId'
import { type Ref, shallowRef } from 'vue'

import type { EmbeddedViewContent, LinkedViewContent } from '@/dashboard/types/widget'

import type { CopyExistingViewSelection, NewViewSelection } from './types'
import { ViewSelectionMode } from './types'

export type DataConfiguration =
  | { mode: 'create'; embeddedId: string; datasource: string; restrictedToSingle: string[] }
  | { mode: 'copy'; embeddedId: string; viewName: string }
  | { mode: 'duplicate'; embeddedId: string; sourceEmbeddedId: string }

/** Tracks the embedded view that the data configuration stage of the view wizard writes. */
export function useDataConfiguration(
  widgetContent: Ref<EmbeddedViewContent | LinkedViewContent | undefined>
) {
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

  function duplicateCurrentView(): void {
    const current = widgetContent.value
    if (current?.type !== 'embedded_view') {
      throw new Error('The widget has no embedded view')
    }
    configuration.value = {
      mode: 'duplicate',
      embeddedId: randomId(),
      sourceEmbeddedId: current.embedded_id
    }
  }

  return { configuration, startNewView, duplicateCurrentView }
}
