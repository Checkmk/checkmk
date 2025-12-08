/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cva } from 'class-variance-authority'
import { type IconSizes } from 'cmk-shared-typing/typescript/icon'

export const emblems = [
  'add',
  'api',
  'disable',
  'download',
  'downtime',
  'edit',
  'enable',
  'more',
  'pending',
  'refresh',
  'remove',
  'rulesets',
  'search',
  'settings',
  'sign',
  'statistic',
  'time',
  'trans',
  'warning'
] as const

export const oneColorIcons = [
  'changes',
  'customize',
  'error',
  'help',
  'monitoring',
  'search',
  'services',
  'setup',
  'show-less',
  'show-more',
  'sidebar',
  'success',
  'user',
  'warning',
  'back',
  'chain',
  'broken-chain'
] as const
export const twoColorIcons = ['aggr'] as const

export const iconSizes: Record<IconSizes[number], number> = {
  xxsmall: 8,
  xsmall: 10,
  small: 12,
  medium: 15,
  large: 18,
  xlarge: 20,
  xxlarge: 32,
  xxxlarge: 77
}

export const cmkIconVariants = cva('', {
  variants: {
    variant: {
      plain: '',
      inline: 'cmk-icon--inline'
    },
    colored: {
      true: '',
      false: 'cmk-icon--colorless'
    }
  },
  defaultVariants: {
    variant: 'plain',
    colored: true
  }
})

export const cmkMultitoneIconVariants = cva('', {
  variants: {
    color: {
      success: 'green',
      hosts: 'blue',
      info: 'blue',
      warning: 'yellow',
      services: 'yellow',
      danger: 'red',
      customization: 'pink',
      others: 'grey',
      users: 'purple',
      specialAgents: 'cyan',
      font: 'font'
    }
  }
})
