/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import type { Components } from 'cmk-shared-typing/typescript/vue_formspec_components'

export function isHorizontalCascadingChoice(parameterForm: FormSpec.FormSpec): boolean {
  const spec = parameterForm as Components
  return spec.type === 'cascading_single_choice' && spec.layout === 'horizontal'
}

export function rendersHelpItself(parameterForm: FormSpec.FormSpec): boolean {
  return (
    isHorizontalCascadingChoice(parameterForm) && 'label' in parameterForm && !!parameterForm.label
  )
}

/** The help a parent shows at the title it renders for the field; a hidden field shows none itself. */
export function helpAtTitle(parameterForm: FormSpec.FormSpec, fieldShown: boolean = true): string {
  return fieldShown && rendersHelpItself(parameterForm) ? '' : parameterForm.help
}
