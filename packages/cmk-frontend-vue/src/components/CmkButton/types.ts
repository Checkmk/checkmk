/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type VariantProps, cva } from 'class-variance-authority'

const buttonVariants = cva('', {
  variants: {
    variant: {
      primary: 'cmk-button--variant-primary',
      secondary: 'cmk-button--variant-secondary',
      optional: 'cmk-button--variant-optional',
      success: 'cmk-button--variant-success',
      warning: 'cmk-button--variant-warning',
      danger: 'cmk-button--variant-danger',
      info: 'cmk-button--variant-info'
    },
    size: {
      medium: 'cmk-button--size-medium',
      small: 'cmk-button--size-small',
      iconOnly: 'cmk-button--size-icon-only'
    },
    disabled: {
      true: 'cmk-button--disabled',
      false: ''
    }
  },
  defaultVariants: {
    variant: 'optional',
    size: 'medium',
    disabled: false
  }
})

export { buttonVariants }

export type ButtonVariants = VariantProps<typeof buttonVariants>

export interface ButtonProps {
  variant?: ButtonVariants['variant']
  size?: ButtonVariants['size']
  disabled?: boolean | string | undefined
  title?: string | undefined
  href?: string | undefined
  target?: string | undefined
}
