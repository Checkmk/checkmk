import type { FormSpec } from '@/vue_formspec_components'

export interface FormSpecWidgetProps {
  id: string
  schema: FormSpec
  data?: object
}

export interface ListWidgetProps {
  items: ComponentSpec[]
  list_type?: 'bullet' | 'ordered' | string | null
}

export interface NoteTextWidgetProps {
  text: string
}

export interface TextWidgetProps {
  text: string
  tooltip?: string | null
}

export interface CompositeWidgetProps {
  components: ComponentSpec[]
}

export interface CollapsibleWidgetProps extends CompositeWidgetProps {
  open: boolean
  label: string
}

type SingleWidgetSpec =
  | TextWidgetProps
  | NoteTextWidgetProps
  | ListWidgetProps
  | FormSpecWidgetProps
type CompositeWidgetSpec = CollapsibleWidgetProps

type SingleWigetType = 'text' | 'note_text' | 'list' | 'form_spec'
type CompositeWidgetType = 'collapsible'

type SingleComponentSpec = SingleWidgetSpec & { widget_type: SingleWigetType }
type CompositeComponentSpec = CompositeWidgetSpec & { widget_type: CompositeWidgetType }

export type ComponentSpec = SingleComponentSpec | CompositeComponentSpec
