/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
const TEXT_ENTRY_SELECTOR = 'textarea, select, [contenteditable], input'
const NON_TEXT_INPUT_TYPES = new Set([
  'checkbox',
  'radio',
  'button',
  'submit',
  'reset',
  'range',
  'color',
  'file'
])

export function isTextEntry(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) {
    return false
  }
  const field = target.closest<HTMLElement>(TEXT_ENTRY_SELECTOR)
  if (!field) {
    return false
  }
  return !(field instanceof HTMLInputElement && NON_TEXT_INPUT_TYPES.has(field.type))
}
