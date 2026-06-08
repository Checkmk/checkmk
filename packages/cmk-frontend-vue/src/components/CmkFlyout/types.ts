/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from '@/lib/i18nString'

/** Props for `CmkFlyout`. */
export interface FlyoutProps {
  /**
   * Whether the popup is open. `CmkFlyout` is fully controlled: it never mutates this itself, it
   * only reflects it and emits `cancel` when the user dismisses (Escape / outside press / focus
   * leaving). The owner reacts to `cancel` (and any trigger interaction) by writing `open`.
   */
  open: boolean
  /** Accessible name for the popup dialog (sets `aria-label`). */
  label?: TranslatedString | undefined
  /**
   * Called when the popup closes while focus is inside it — restore focus to the control that owns
   * the popup (the element carrying the trigger `aria`, e.g. the trigger button). The flyout decides
   * *when* to restore (only on a close with focus still inside the popup); the owner decides *what*
   * to focus. The flyout cannot do this itself: the focusable control lives in the slot, not on the
   * wrapper the flyout owns.
   */
  restoreFocus: () => void
}

/**
 * ARIA attributes describing the trigger→popup relationship, handed to the flyout's `trigger` slot.
 * Bind these onto the focusable trigger element (e.g. `<MyInput v-bind="aria" />`) so assistive
 * technology announces that the control opens a dialog and whether it is currently open.
 */
export interface TriggerAria {
  'aria-haspopup': 'dialog'
  'aria-expanded': boolean
  'aria-controls': string | undefined
}

/** Props handed to a flyout `trigger` slot. */
export interface FlyoutTriggerSlotProps {
  /** Whether the popup is currently open. */
  open: boolean
  /**
   * ARIA attributes describing the popup-trigger relationship. Bind these onto the focusable
   * trigger element (e.g. `<MyInput v-bind="aria" />`) so assistive technology announces that the
   * control opens a dialog and whether it is currently open. The flyout cannot apply them itself:
   * the focusable control lives inside the slot, not on the wrapper the flyout owns.
   * See {@link TriggerAria}.
   */
  aria: TriggerAria
}

/** The slots the flyout exposes. */
export interface FlyoutSlots {
  /**
   * The always-visible control that toggles the popup. Render a focusable element and bind
   * {@link FlyoutTriggerSlotProps.aria} onto it.
   */
  trigger?: (props: FlyoutTriggerSlotProps) => unknown
  /** The popup body, rendered only while the flyout is open. */
  default?: () => unknown
}
