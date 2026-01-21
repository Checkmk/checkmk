/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { VariantProps } from 'class-variance-authority'
import { type IconNames } from 'cmk-shared-typing/typescript/icon'

import type { emblems, oneColorIcons, twoColorIcons } from './icons.constants'
import type { cmkIconVariants, cmkMultitoneIconVariants, iconSizes } from './icons.constants'

export type SimpleIcons = IconNames
export type IconEmblems = (typeof emblems)[number]
export type OneColorIcons = (typeof oneColorIcons)[number]
export type TwoColorIcons = (typeof twoColorIcons)[number]

export type CmkMultitoneIconNames = OneColorIcons | TwoColorIcons
export type CmkIconVariants = VariantProps<typeof cmkIconVariants>

export type CmkMultitoneIconColor = VariantProps<typeof cmkMultitoneIconVariants>['color']
export type IconSizeNames = keyof typeof iconSizes

export interface CustomIconColor {
  custom: string
}

export interface CmkIconProps {
  /** @property {SimpleIcons} name - Name of the icon */
  name: SimpleIcons

  /** @property {undefined | CmkIconVariants['variant']} variant - Styling variant of the icon */
  variant?: CmkIconVariants['variant'] | undefined

  /** @property {undefined | CmkIconVariants['size']} size - Width and height of the icon */
  size?: IconSizeNames | undefined

  /** @property {undefined | CmkIconVariants['colored']} colored - Whether the icon is colored or black and white */
  colored?: CmkIconVariants['colored'] | undefined

  /** @property {undefined | number} rotate - Transform rotate value in degrees */
  rotate?: number | undefined

  /** @property {undefined | string} title - Title to be displayed on hover */
  title?: string | undefined
}
