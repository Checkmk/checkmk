/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, readonly, ref } from 'vue'

import { HOST_TAB_OVERVIEW } from './hostSlideInTabs'

/** The tab state of the host slide-in, shared by every page and widget that opens it. */
export interface HostSlideInTabs {
  tabId: Ref<string | undefined>
  /**
   * Counted rather than flagged: clicking the relation count of the host the panel already shows
   * has to scroll there again, and a flag that is already set changes nothing.
   */
  revealRelationsRequest: Readonly<Ref<number>>
  /** The panel opens on a host; `revealRelations` asks for the overview tab at its relations. */
  open(revealRelations: boolean): void
  /** The user switched to the tab `id`. */
  selectTab(id: string): void
}

export function useHostSlideInTabs(): HostSlideInTabs {
  const tabId = ref<string | undefined>(undefined)
  const revealRelationsRequest = ref(0)

  return {
    tabId,
    revealRelationsRequest: readonly(revealRelationsRequest),
    open(revealRelations: boolean): void {
      if (revealRelations) {
        tabId.value = HOST_TAB_OVERVIEW
        revealRelationsRequest.value += 1
      } else {
        revealRelationsRequest.value = 0
      }
    },
    selectTab(id: string): void {
      tabId.value = id
      if (id !== HOST_TAB_OVERVIEW) {
        revealRelationsRequest.value = 0
      }
    }
  }
}
