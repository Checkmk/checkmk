/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

/** Cheat sheet hints (CMK-38372) for the monitoring tables; scrolling needs a click first, see CMK-38639. */
export function tableKeyboardHints(): TranslatedString[] {
  const { _t } = usei18n()
  return [
    _t('Press [/] to search the table'),
    _t('Press [Enter] on a column header to sort by it'),
    _t(
      "Press [Enter] on a column's filter button to filter for that column, [ArrowDown]/[ArrowUp] to move between the rows, [Escape] to close"
    ),
    _t('Press [Space] on a quick filter chip to filter for unhandled problems'),
    _t("Press [Space] on a row's checkbox to select it, on the header checkbox to select all"),
    _t(
      'Press [ArrowUp]/[ArrowDown]/[ArrowLeft]/[ArrowRight] to move the focus to the nearest clickable element, while no menu or widget uses them; with nothing focused, [ArrowUp]/[ArrowDown] scroll the table'
    ),
    _t('Press [Escape] to let go of the focus'),
    _t('Click into the table, then press [PageUp]/[PageDown]/[Home]/[End] to scroll it'),
    _t(
      "Press [ContextMenu] (or [Shift]+[F10]) to open the menu of the focused element or its row, e.g. a host's ... menu"
    ),
    _t(
      'Type letters to focus the first clickable text containing them, [ArrowDown]/[ArrowUp] for the next/previous match, [Enter] to activate it, [Escape] to clear'
    )
  ]
}
