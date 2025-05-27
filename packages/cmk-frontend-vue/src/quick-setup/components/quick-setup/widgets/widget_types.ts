/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import type { ValidationMessages } from '@/form'

export interface FormSpecRecapWidgetProps {
  /** @property {string} id - Id of the form spec */
  id: string

  /** @property {unknown} form_spec - The form spec description */
  from_spec: unknown
}

export interface FormSpecWidgetProps {
  /** @property {object} form_spec - Form Spec data for the Form wrapper */
  form_spec: {
    /** @property {string} id - Id of the form_spec */
    id: string
    /** @property {FormSpec} spec - schema */
    spec: FormSpec

    /** @property {ValidationMessages} validation - Validation errors */
    validation?: ValidationMessages

    /** @property {unknown} data - Default data of the formspec */
    data: unknown
  }
  /** @property {object} data - User input data to be passed to the form */
  data?: StageData
  errors?: Record<string, ValidationMessages>
}

export interface ListWidgetProps {
  /** @property {ComponentSpec[]} items - Items to be rendered inside the list */
  items: ComponentSpec[]

  /** @property {string} list_type - List style (bullet ,numbers, checks) */
  list_type?: 'bullet' | 'ordered' | 'check' | string | null
}

export interface NoteTextWidgetProps {
  /** @property {string}  text - Text to be displayed */
  text: string
}

export interface DialogWidgetProps {
  /** @property {string}  text - Text to be displayed */
  text: string
}

export interface TextWidgetProps {
  /** @property {string}  text - Text to be displayed */
  text: string

  /** @property {string}  tooltip - Text used as tooltip */
  tooltip?: string | null
}

export interface CompositeWidgetProps {
  /** @property {ComponentSpec[]} items - Widgets being part of the composite element */
  items: ComponentSpec[]
  data?: StageData
  errors?: Record<string, ValidationMessages>
}

export interface CollapsibleWidgetProps extends CompositeWidgetProps {
  /** @property {boolean} open - If false, the collapsible will be rendered collapsed */
  open?: boolean

  /** @property {string} title - Title of the collapsible element */
  title: string

  /** @property {string} help_text - Help of the collapsible element */
  help_text: string | null
}

/** The conditional notification event stage widgets are a really specific solution to a really
 *  specific use case for the notification quick setup. Hence, we opted for a really specific
 *  solution which exactly covers the three use cases we have in the notification quick setup.
 *  A more generic approach has been rejected, but may be considered in the future. */
export interface ConditionalNotificationStageWidgetProps extends CompositeWidgetProps {
  condition: boolean
}

type ConditionalNotificationDialogWidgetTarget = 'svc_filter' | 'recipient'

export interface ConditionalNotificationDialogWidgetProps
  extends ConditionalNotificationStageWidgetProps {
  target: ConditionalNotificationDialogWidgetTarget
}

type SingleWidgetSpec =
  | TextWidgetProps
  | NoteTextWidgetProps
  | DialogWidgetProps
  | ListWidgetProps
  | FormSpecWidgetProps
  | FormSpecRecapWidgetProps
type CompositeWidgetSpec = CollapsibleWidgetProps | ConditionalNotificationStageWidgetProps

type SingleWidgetType = 'text' | 'note_text' | 'list_of_widgets' | 'form_spec' | 'form_spec_recap'
type CompositeWidgetType =
  | 'collapsible'
  | 'conditional_notification_host_event_stage_widget'
  | 'conditional_notification_service_event_stage_widget'
  | 'conditional_notification_ec_alert_stage_widget'
  | 'conditional_notification_dialog_widget'

type SingleComponentSpec = SingleWidgetSpec & { widget_type: SingleWidgetType }
type CompositeComponentSpec = CompositeWidgetSpec & { widget_type: CompositeWidgetType }

export type ComponentSpec = SingleComponentSpec | CompositeComponentSpec

/** @type {StageData} - User's data input, stored as {'field_name': value} */
export type StageData = Record<string, object>

/** @type {AllValidationMessages} - Formspec errors, stored as {'field_name': error} */
export type AllValidationMessages = Record<string, ValidationMessages>
