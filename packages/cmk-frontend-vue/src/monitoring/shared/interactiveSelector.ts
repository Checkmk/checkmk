/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/** What a keyboard user can click in a view. */
export const INTERACTIVE_SELECTOR = [
  'a[href]',
  'button:not(:disabled)',
  'summary',
  '[role="button"]:not([aria-disabled="true"])',
  '[role="menuitem"]',
  '[role="tab"]',
  'input:is([type="checkbox"], [type="radio"]):not(:disabled)',
  'select:not(:disabled)'
].join(', ')
