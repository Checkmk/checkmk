/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Component } from 'vue'

import type { CmkIconProps } from '@/components/CmkIcon'
import type { SlideInVariants } from '@/components/CmkSlideIn'
import type { CmkTabProps } from '@/components/CmkTabs/CmkTab.vue'

/**
 * A single tab rendered inside {@link CmkSlideInTabbed}.
 *
 * The consuming page owns the tab's content component and its data loading, so
 * the generic container never imports feature-specific code. When the tab is
 * activated for the first time, `load` is awaited and its result is handed to
 * `component` via a `data` prop; the container renders a loading indicator
 * until the promise settles and an error message if it rejects.
 */
export interface SlideInTab {
  /** Stable identifier, also used as the tab's routing value. */
  id: string
  /** Human readable, translated label shown on the tab trigger. */
  title: string
  /** The component rendered in the tab body, receiving the loaded `data`. */
  component: Component
  /** Optional async data loader; the resolved value is passed as `data`. */
  load?: (() => Promise<unknown>) | undefined
  /**
   * Optional skeleton component shown while `load` is pending. Falls back to a
   * generic loading indicator when not provided.
   */
  skeleton?: Component | undefined
  /** Static props forwarded verbatim to `component`. */
  props?: Record<string, unknown> | undefined
  /** Optional colour variant for the tab trigger. */
  variant?: CmkTabProps['variant']
  /** Whether the tab is disabled. */
  disabled?: boolean | undefined
}

export type SlideInTabStatus = 'loading' | 'loaded' | 'error'

export interface SlideInTabState {
  status: SlideInTabStatus
  data?: unknown
  error?: unknown
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
   * When true, the tabs (and the `actions` slot) are hidden and the `override`
   * slot is rendered in their place. The `above-tabs` slot stays visible, so a
   * page can swap the tabbed body for a focused sub-view (e.g. an action form)
   * while keeping the panel header.
   */
  overrideActive?: boolean | undefined
}
