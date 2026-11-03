<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import codeExample from './UclEditableTable.vue?raw'

export const a11yData = [
  {
    keys: ['Tab', 'Space', 'Enter'],
    description:
      'All editing controls (visibility toggle, dropdown, color picker, switch, chevron, action buttons) are native buttons/inputs and keyboard-operable. The expansion chevron exposes aria-expanded and aria-controls.'
  },
  {
    keys: ['—'],
    description:
      'Row reordering via the drag handle is mouse-only, matching the existing drag handles in CmkList and the graph designer.'
  }
]
</script>

<script setup lang="ts">
import type { ColumnDef, RowSelectionState } from '@tanstack/vue-table'
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout
} from '@ucl/_ucl/components/detail-page'
import CmkAddDropdown from 'cmk-ui-library/components/CmkDropdown/CmkAddDropdown.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { h, ref } from 'vue'

import EditableTable from '@/monitoring/shared/components/EditableTable.vue'
import ActionsCell, { type CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import CheckboxCell from '@/monitoring/shared/components/cell/CheckboxCell.vue'
import CollapsibleCell from '@/monitoring/shared/components/cell/CollapsibleCell.vue'
import ColorPickerCell from '@/monitoring/shared/components/cell/ColorPickerCell.vue'
import DragHandleCell from '@/monitoring/shared/components/cell/DragHandleCell.vue'
import DropdownCell from '@/monitoring/shared/components/cell/DropdownCell.vue'
import StringCell from '@/monitoring/shared/components/cell/StringCell.vue'
import SwitchCell from '@/monitoring/shared/components/cell/SwitchCell.vue'
import VisibilityCell from '@/monitoring/shared/components/cell/VisibilityCell.vue'

defineProps<{ screenshotMode: boolean }>()

interface DemoLine {
  id: string
  source: string
  color: string
  title: string
  lineStyle: string | null
  visible: boolean
  mirrored: boolean
}

const columns: ColumnDef<DemoLine>[] = [
  { id: 'drag', header: '' },
  { id: 'select', header: '', meta: { selectColumn: true, justify: 'center' } },
  {
    id: 'visibility',
    header: () =>
      h(CmkMultitoneIcon, {
        name: 'eye',
        primaryColor: { custom: 'var(--color-mist-grey-60)' },
        size: 'medium'
      }),
    meta: { headerTitle: untranslated('Visibility'), justify: 'center' }
  },
  { id: 'id', header: 'ID' },
  { id: 'source', header: 'Source' },
  { id: 'color', header: 'Color' },
  { id: 'title', header: 'Title', meta: { stretch: true } },
  { id: 'line-style', header: 'Line style' },
  { id: 'mirrored', header: 'Mirrored' },
  { id: 'actions', header: 'Actions', meta: { justify: 'right' } }
]

const SOURCE_TITLES: Record<string, string> = {
  otel_metrics: 'OpenTelemetry metrics',
  cmk_rrd: 'CMK RRD',
  calculated: 'Calculated metric',
  reference: 'Reference line'
}

const SOURCE_OPTIONS: Suggestions = {
  type: 'fixed',
  suggestions: Object.entries(SOURCE_TITLES).map(([name, title]) => ({
    name,
    title: untranslated(title)
  }))
}

const LINE_STYLE_OPTIONS: Suggestions = {
  type: 'fixed',
  suggestions: [
    { name: 'line', title: untranslated('Line') },
    { name: 'area', title: untranslated('Area') },
    { name: 'stack', title: untranslated('Stack') }
  ]
}

const ACTIONS: CellAction[] = [
  { id: 'clone', label: untranslated('Clone'), icon: 'clone' },
  { id: 'delete', label: untranslated('Delete'), icon: 'delete' }
]

let nextId = 0
function makeLine(sourceName: string): DemoLine {
  nextId += 1
  return {
    id: `line-${nextId}`,
    source: SOURCE_TITLES[sourceName] ?? sourceName,
    color: '#e69138',
    title: '$DEFAULT_TITLE$',
    lineStyle: 'line',
    visible: true,
    mirrored: false
  }
}

const lines = ref<DemoLine[]>([
  { ...makeLine('otel_metrics'), title: 'CPU $METRIC_NAME$ - system', color: '#3c85f2' },
  { ...makeLine('cmk_rrd'), title: 'accounting > Check_MK > cmk_time_agent', color: '#e69138' },
  { ...makeLine('cmk_rrd'), title: 'accounting > Check_MK > cmk_time_agent', color: '#6fd7d0' },
  { ...makeLine('calculated'), title: 'Sum B+C', color: '#f2b26d' },
  { ...makeLine('reference'), title: 'Constant: 1 <graph unit>', color: '#d64545' }
])

const rowSelection = ref<RowSelectionState>({})
const expandedRows = ref<Record<string, boolean>>({})

function rowLabel(index: number): string {
  return String.fromCharCode('A'.charCodeAt(0) + (index % 26))
}

function onReorder(fromIndex: number, toIndex: number): void {
  const next = [...lines.value]
  const moved = next.splice(fromIndex, 1)[0]!
  next.splice(toIndex, 0, moved)
  lines.value = next
}

function onAction(line: DemoLine, index: number, action: CellAction): void {
  const next = [...lines.value]
  if (action.id === 'clone') {
    nextId += 1
    next.splice(index + 1, 0, { ...line, id: `line-${nextId}` })
  } else if (action.id === 'delete') {
    next.splice(index, 1)
  }
  lines.value = next
}

function addLine(sourceName: string): void {
  const line = makeLine(sourceName)
  lines.value = [...lines.value, line]
  expandedRows.value[line.id] = true
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>Editable table</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-editable-table__viewport">
        <EditableTable
          v-model:row-selection="rowSelection"
          :expanded-rows="expandedRows"
          :rows="lines"
          :columns="columns"
          :get-row-key="(line) => line.id"
          row-height="40px"
          @reorder="onReorder"
        >
          <template #row="{ row, tableRow, index }">
            <DragHandleCell column-id="drag" vertical-align="middle" />
            <CheckboxCell
              column-id="select"
              :aria-label="untranslated('Select row')"
              vertical-align="middle"
              :model-value="tableRow.getIsSelected()"
              @update:model-value="tableRow.toggleSelected($event)"
            />
            <VisibilityCell v-model="row.visible" column-id="visibility" vertical-align="middle" />
            <StringCell column-id="id" :value="rowLabel(index)" vertical-align="middle" />
            <StringCell column-id="source" :value="row.source" vertical-align="middle" no-wrap />
            <ColorPickerCell v-model="row.color" column-id="color" vertical-align="middle" />
            <CollapsibleCell
              column-id="title"
              vertical-align="middle"
              :expanded="expandedRows[row.id] ?? false"
              :controls-id="`expansion-${row.id}`"
              @update:expanded="(value: boolean) => (expandedRows[row.id] = value)"
            >
              <CmkInput v-model="row.title" type="text" field-size="fill" />
            </CollapsibleCell>
            <DropdownCell
              v-model="row.lineStyle"
              column-id="line-style"
              vertical-align="middle"
              :options="LINE_STYLE_OPTIONS"
              :label="untranslated('Line style')"
            />
            <SwitchCell v-model="row.mirrored" column-id="mirrored" vertical-align="middle" />
            <ActionsCell
              column-id="actions"
              :actions="ACTIONS"
              vertical-align="middle"
              @select="onAction(row, index, $event)"
            />
          </template>

          <template #expansion="{ row, index }">
            <td colspan="4"></td>
            <td :id="`expansion-${row.id}`" colspan="6">
              <div class="ucl-editable-table__expansion-panel">
                Row-specific content for line {{ rowLabel(index) }} ({{ row.title }}) — an arbitrary
                form goes here.
              </div>
            </td>
          </template>

          <template #footer>
            <td colspan="4"></td>
            <td colspan="6" class="ucl-editable-table__footer-cell">
              <CmkAddDropdown
                :options="SOURCE_OPTIONS"
                :label="untranslated('Add scope')"
                @select="addLine"
              />
            </td>
          </template>
        </EditableTable>
      </div>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-editable-table__viewport {
  width: 100%;
}

.ucl-editable-table__expansion-panel {
  margin: var(--dimension-4) 0;
  padding: var(--dimension-6);
  background: var(--ux-theme-2);
  border-radius: var(--border-radius);
}

/* Align the add control with the cell content (BaseCell uses the same
   horizontal padding). */
.ucl-editable-table__footer-cell {
  padding: var(--dimension-4) 0 var(--dimension-4) var(--dimension-4);
}
</style>
