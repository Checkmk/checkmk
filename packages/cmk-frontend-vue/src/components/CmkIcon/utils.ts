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

const imageMap = new Map(
  Object.entries(
    import.meta.glob('~cmk-frontend/themes/**/*.{png,svg}', {
      eager: true,
      import: 'default'
    })
  ).flatMap(([path, url]) => {
    const match = path.match(/themes\/.*$/)
    return match ? [[match[0], url as string]] : []
  })
)

export const getIconPath = (name: SimpleIcons, theme: string): string => {
  let filename = themedIcons[name]
  let themeToUse = theme

  if (!filename) {
    filename = unthemedIcons[name]
    themeToUse = 'facelift'
  }

  if (!filename) {
    return ''
  }

  const suffix = `themes/${themeToUse}/images/${filename}`
  return imageMap.get(suffix) || ''
}
