/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * Per-action form description. `ActionFormPane` switches its rendered content on
 * `type`, mirroring how `FilterDropdown` switches on a filter definition's type.
 * New action types register a component in the pane's `ACTION_FORM_COMPONENTS`
 * registry; a `confirm` action needs no inputs and renders no form component.
 */
export interface ConfirmActionForm {
  type: 'confirm'
  ident: string
}

export interface CommentActionForm {
  type: 'comment'
  ident: string
}

export type ActionFormDefinition = ConfirmActionForm | CommentActionForm

export type ConfirmActionValues = Record<string, never>

export interface CommentActionValues {
  comment: string
}

export interface AcknowledgeActionValues {
  comment: string
  sticky: boolean
  persistent: boolean
  notify: boolean
}

export interface DowntimeActionValues {
  comment: string
  hours: number
}

export type ActionFormValues =
  | ConfirmActionValues
  | CommentActionValues
  | AcknowledgeActionValues
  | DowntimeActionValues

export function defaultActionValues(definition: ActionFormDefinition): ActionFormValues {
  switch (definition.type) {
    case 'comment':
      return { comment: '' }
    case 'confirm':
      return {}
  }
}
