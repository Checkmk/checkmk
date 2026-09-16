/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CmkAsyncContentProps } from 'cmk-ui-library/components/CmkAsyncContent'
import type { CmkIconProps } from 'cmk-ui-library/components/CmkIcon'
import type { SlideInVariants } from 'cmk-ui-library/components/CmkSlideIn'
import type { CmkTabProps } from 'cmk-ui-library/components/CmkTabs/CmkTab.vue'

/**
 * A single tab rendered inside {@link CmkSlideInTabbed}: a body with a name to
 * reach it by. What it renders, and how that is loaded, is the body's own
 * business - the panel only says where it goes.
 */
export interface SlideInTab extends CmkAsyncContentProps {
  /** Stable identifier, also used as the tab's routing value. */
  id: string
  /** Human readable, translated label shown on the tab trigger. */
  title: string
  /** Optional colour variant for the tab trigger. */
  variant?: CmkTabProps['variant']
  /** Whether the tab is disabled. */
  disabled?: boolean | undefined
}

export interface CmkSlideInTabbedProps {
  open: boolean
  tabs: SlideInTab[]
  header?:
    | {
        title: string
        icon?: CmkIconProps | undefined
        closeButton: boolean
      }
    | undefined
  size?: SlideInVariants['size']
  borderColor?: SlideInVariants['borderColor']
  /** Id of the tab shown first; defaults to the first tab. */
  defaultTabId?: string | undefined
  /**
   * The tab on show, as a `v-model:activeTabId`. Bind it when the tab has to
   * outlive the panel - a page persisting it in the URL, say. Left unbound, the
   * container keeps the active tab to itself and `defaultTabId` decides where
   * each opening starts.
   */
  activeTabId?: string | undefined
  /**
   * When true, the tabs (and the `actions` slot) are hidden and the `override`
   * slot is rendered in their place. The `above-tabs` slot stays visible, so a
   * page can swap the tabbed body for a focused sub-view (e.g. an action form)
   * while keeping the panel header.
   */
  overrideActive?: boolean | undefined
  /**
   * Bump this (e.g. a counter) to make every tab re-fetch its data next time it
   * is shown - useful after an action changes something the open tabs
   * displayed.
   */
  reloadToken?: number | undefined
}
