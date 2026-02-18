/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { iconSizes, themedIcons, unthemedIcons } from './icons.constants'
import { type IconSizeNames, type SimpleIcons } from './types'

export function iconSizeNametoNumber(sizeName: IconSizeNames | undefined) {
  let size
  if (sizeName === undefined) {
    size = iconSizes['medium']
  } else {
    size = iconSizes[sizeName]
  }
  return size
}

export function getIconPath(name: SimpleIcons, theme: string): string {
  let internalTheme = 'dark'
  if (theme === 'facelift') {
    internalTheme = 'light'
  }

  const found = themedIcons[internalTheme]![name]
  if (found !== undefined) {
    return found
  }

  const filename = unthemedIcons[name]
  if (!filename) {
    return ''
  }

  return filename
}
