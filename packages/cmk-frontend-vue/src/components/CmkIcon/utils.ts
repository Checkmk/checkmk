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

const iconResolver = new Map(
  Object.entries(
    import.meta.glob(
      [
        '~cmk-frontend/themes/*/images/*.{png,svg}',
        // Non-icon image exceptions which are statically imported elsewhere
        '!~cmk-frontend/themes/facelift/images/checkmk_logo.svg'
      ],
      {
        import: 'default'
      }
    )
  ).flatMap(([path, resolver]) => {
    const match = path.match(/themes\/.*$/)
    return match ? [[match[0], resolver as () => Promise<string>]] : []
  })
)

export const getIconPath = async (name: SimpleIcons, theme: string): Promise<string> => {
  let filename = themedIcons[name]
  let themeToUse = theme

  if (!filename) {
    filename = unthemedIcons[name]
    themeToUse = 'facelift'
  }

  if (!filename) {
    return ''
  }

  const resolver = iconResolver.get(`themes/${themeToUse}/images/${filename}`)

  if (!resolver) {
    return ''
  }

  return resolver()
}
