/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type IconNames } from 'cmk-shared-typing/typescript/icon'
import {
  oneColorIcons,
  themedIcons,
  twoColorIcons,
  unthemedIcons
} from 'cmk-ui-library/components/CmkIcon/icons.constants'
import type { CmkMultitoneIconNames } from 'cmk-ui-library/components/CmkIcon/types'

export const allIconNames: IconNames[] = [
  ...new Set([...Object.keys(unthemedIcons), ...Object.keys(themedIcons.light)])
].sort() as IconNames[]

export const allIconOptions = allIconNames.map((name) => {
  return { title: name, name: name }
})

export const allMultitoneIconNames: CmkMultitoneIconNames[] = [
  ...oneColorIcons,
  ...twoColorIcons
].sort()

export const allMultitoneIconOptions = allMultitoneIconNames.map((name) => {
  return { title: name, name: name }
})
