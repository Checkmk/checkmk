<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ColumnDef, RowSelectionState } from '@tanstack/vue-table'
import type { TitleMacroGroup } from 'cmk-shared-typing/typescript/custom_graph_designer'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import { CmkAddDropdown } from 'cmk-ui-library/components/CmkDropdown'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import EditableTable from '@/monitoring/shared/components/EditableTable.vue'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import ActionsCell from '@/monitoring/shared/components/cell/ActionsCell.vue'
import BaseCell from '@/monitoring/shared/components/cell/BaseCell.vue'
import CheckboxCell from '@/monitoring/shared/components/cell/CheckboxCell.vue'
import CollapsibleCell from '@/monitoring/shared/components/cell/CollapsibleCell.vue'
import ColorPickerCell from '@/monitoring/shared/components/cell/ColorPickerCell.vue'
import DragHandleCell from '@/monitoring/shared/components/cell/DragHandleCell.vue'
import DropdownCell from '@/monitoring/shared/components/cell/DropdownCell.vue'
import SwitchCell from '@/monitoring/shared/components/cell/SwitchCell.vue'
import VisibilityCell from '@/monitoring/shared/components/cell/VisibilityCell.vue'

import { useDeleteWithDependents } from '../composables/useDeleteWithDependents'
import type { GraphItemsStore } from '../composables/useGraphItems'
import { useRowLabels } from '../composables/useRowLabels'
import { useTitleMacroHelp } from '../composables/useTitleMacroHelp'
import {
  type DesignerItem,
  newConstantDraft,
  newMetricBackendDraft,
  newRrdMetricDraft,
  newScalarDraft,
  scalarColor
} from '../drafts'
import { type ItemId, isSingleLine, parseLineType } from '../types'
import DeleteWithDependentsPopup from './DeleteWithDependentsPopup.vue'
import ConstantLineForm from './forms/ConstantLineForm.vue'
import FormulaForm from './forms/FormulaForm.vue'
import MetricBackendForm from './forms/MetricBackendForm.vue'
import RrdForm from './forms/RrdForm.vue'
import ServiceReferenceLineForm from './forms/ServiceReferenceLineForm.vue'

const { store, thresholds, metricBackendAvailable, titleMacros } = defineProps<{
  store: GraphItemsStore
  thresholds: { warning: string; critical: string }
  metricBackendAvailable: boolean
  titleMacros: TitleMacroGroup[]
}>()

const emit = defineEmits<{
  'add-calculation': []
}>()

const { _t } = usei18n()
const { sourceTypeLabel, lineStyleSuggestions, lineStyleLabel } = useRowLabels()
const { renderTitleMacroHelp } = useTitleMacroHelp()

const titleMacroHelp = renderTitleMacroHelp(titleMacros)

const rowSelection = ref<RowSelectionState>({})
const expandedRows = ref<Record<string, boolean>>({})

const columns: ColumnDef<DesignerItem>[] = [
  { id: 'drag', header: '', meta: { justify: 'center' } },
  { id: 'visibility', header: '', meta: { justify: 'center' } },
  { id: 'select', header: '', meta: { selectColumn: true, justify: 'center' } },
  { id: 'id', header: _t('ID'), meta: { justify: 'left' } },
  { id: 'source', header: _t('Source'), meta: { justify: 'left' } },
  { id: 'color', header: _t('Color'), meta: { justify: 'center' } },
  {
    id: 'title',
    header: _t('Title'),
    minSize: 260,
    meta: { stretch: true, headerHelp: titleMacroHelp }
  },
  { id: 'line_style', header: _t('Line style'), meta: { justify: 'left' } },
  { id: 'mirrored', header: _t('Mirrored'), meta: { justify: 'center' } },
  { id: 'actions', header: _t('Actions') }
]

const sourceColumnIndex = columns.findIndex((column) => column.id === 'source')
const titleColumnIndex = columns.findIndex((column) => column.id === 'title')

// TanStack keeps selection entries for rows that no longer exist (e.g. deleted
// through the calculation slideout), so restrict to the rows still in the store.
const selectedIds = computed<ItemId[]>(() => {
  const known = new Set(store.items.value.map((item) => item.id))
  return Object.entries(rowSelection.value)
    .filter(([id, selected]) => selected && known.has(id))
    .map(([id]) => id)
})

/**
 * The addable source types and their dropdown titles; rrd_query is reached via the in-form toggle
 * and metric_backend only appears when the feature is available in this edition.
 */
const addSourceSuggestions = computed(() => {
  const suggestions = [
    { name: 'rrd_metric', title: _t('Checkmk RRD') },
    { name: 'constant', title: _t('Constant line') },
    { name: 'scalar', title: _t('Service reference line') }
  ]
  if (metricBackendAvailable) {
    suggestions.push({ name: 'metric_backend', title: _t('Metrics backend') })
  }
  return { type: 'fixed' as const, suggestions }
})

function onAddSource(value: string): void {
  const id = store.addItem((assigned): DesignerItem => {
    switch (value) {
      case 'rrd_metric':
        return newRrdMetricDraft(assigned, store.nextColor.value)
      case 'constant':
        return newConstantDraft(assigned, store.nextColor.value)
      case 'scalar':
        return newScalarDraft(assigned, scalarColor('warning', store.nextColor.value, thresholds))
      case 'metric_backend':
        return newMetricBackendDraft(assigned)
      default:
        throw new Error(`Unknown source type: ${value}`)
    }
  })
  expandedRows.value = { ...expandedRows.value, [id]: true }
}

const rowActions: CellAction[] = [
  { id: 'clone', label: _t('Clone'), icon: 'clone' },
  { id: 'delete', label: _t('Delete'), icon: 'delete' }
]

const rowDelete = useDeleteWithDependents(store, () => {
  rowSelection.value = {}
})

function onRowAction(row: DesignerItem, action: CellAction): void {
  if (action.id === 'clone') {
    store.clone([row.id])
  } else if (action.id === 'delete') {
    rowDelete.request([row.id])
  }
}

function onBulkClone(): void {
  store.clone(selectedIds.value)
  rowSelection.value = {}
}

function onLineStyleChange(row: DesignerItem, value: string | null): void {
  const lineType = parseLineType(value)
  if (lineType !== undefined) {
    store.patch(row.id, { line_type: lineType })
  }
}

function onTitleChange(row: DesignerItem, title: string | undefined): void {
  store.patch(row.id, { title: title ?? '' })
}
</script>

<template>
  <div class="graphing-metrics-table">
    <div class="graphing-metrics-table__toolbar">
      <div v-if="selectedIds.length > 0" class="graphing-metrics-table__bulk-actions">
        <CmkButton
          :aria-label="_t('Delete selected sources')"
          @click="rowDelete.request(selectedIds)"
        >
          <CmkIcon name="delete" variant="inline" size="small" />
          {{ _t('Delete') }}
        </CmkButton>
        <CmkButton :aria-label="_t('Clone selected sources')" @click="onBulkClone">
          <CmkIcon name="clone" variant="inline" size="small" />
          {{ _t('Clone') }}
        </CmkButton>
      </div>
      <CmkButton class="graphing-metrics-table__add-calculation" @click="emit('add-calculation')">
        {{ _t('Add calculation') }}
      </CmkButton>
    </div>

    <CmkScrollContainer height="auto" max-height="none" class="graphing-metrics-table__scroll">
      <EditableTable
        v-model:row-selection="rowSelection"
        :rows="[...store.items.value]"
        :columns="columns"
        :get-row-key="(row: DesignerItem) => row.id"
        :expanded-rows="expandedRows"
        @reorder="(from: number, to: number) => store.move(from, to)"
      >
        <template #row="{ row, tableRow }">
          <DragHandleCell column-id="drag" vertical-align="middle" />
          <VisibilityCell
            column-id="visibility"
            vertical-align="middle"
            :model-value="row.visible"
            @update:model-value="store.setVisibility([row.id], $event)"
          />
          <CheckboxCell
            column-id="select"
            vertical-align="middle"
            :model-value="tableRow.getIsSelected()"
            :aria-label="_t('Select row')"
            @update:model-value="tableRow.toggleSelected($event)"
          />
          <BaseCell column-id="id" vertical-align="middle">{{ row.id }}</BaseCell>
          <BaseCell column-id="source" vertical-align="middle" no-wrap>{{
            sourceTypeLabel(row.type)
          }}</BaseCell>
          <ColorPickerCell
            v-if="isSingleLine(row)"
            column-id="color"
            vertical-align="middle"
            :model-value="row.color"
            @update:model-value="store.patch(row.id, { color: $event })"
          />
          <BaseCell v-else column-id="color" vertical-align="middle" />
          <CollapsibleCell
            column-id="title"
            vertical-align="middle"
            :expanded="expandedRows[row.id] === true"
            @update:expanded="expandedRows = { ...expandedRows, [row.id]: $event }"
          >
            <CmkInput
              :model-value="row.title"
              :aria-label="_t('Title')"
              field-size="large"
              @update:model-value="onTitleChange(row, $event)"
            />
          </CollapsibleCell>
          <DropdownCell
            column-id="line_style"
            vertical-align="middle"
            :model-value="row.line_type"
            :options="lineStyleSuggestions"
            :label="lineStyleLabel"
            @update:model-value="onLineStyleChange(row, $event)"
          />
          <SwitchCell
            column-id="mirrored"
            vertical-align="middle"
            :model-value="row.mirrored"
            @update:model-value="store.patch(row.id, { mirrored: $event })"
          />
          <ActionsCell
            column-id="actions"
            vertical-align="middle"
            :actions="rowActions"
            :max-visible="2"
            @select="onRowAction(row, $event)"
          />
        </template>

        <template #expansion="{ row }">
          <tr>
            <td v-if="titleColumnIndex > 0" :colspan="titleColumnIndex" />
            <td
              :colspan="columns.length - titleColumnIndex"
              class="graphing-metrics-table__expansion"
            >
              <FormulaForm v-if="row.type === 'rrd_formula'" :item="row" :store="store" />
              <div v-else class="graphing-metrics-table__editor-panel">
                <RrdForm
                  v-if="row.type === 'rrd_metric' || row.type === 'rrd_query'"
                  :item="row"
                  :store="store"
                />
                <ConstantLineForm v-else-if="row.type === 'constant'" :item="row" :store="store" />
                <ServiceReferenceLineForm
                  v-else-if="row.type === 'scalar'"
                  :item="row"
                  :store="store"
                  :thresholds="thresholds"
                />
                <MetricBackendForm
                  v-else-if="row.type === 'metric_backend'"
                  :item="row"
                  :store="store"
                />
              </div>
            </td>
          </tr>
        </template>

        <template #footer>
          <td v-if="sourceColumnIndex > 0" :colspan="sourceColumnIndex" />
          <BaseCell
            column-id="source"
            vertical-align="middle"
            class="graphing-metrics-table__add-source"
          >
            <CmkAddDropdown
              width="fill"
              floating
              :options="addSourceSuggestions"
              :label="_t('Add source')"
              @select="onAddSource"
            />
          </BaseCell>
          <td
            v-if="columns.length - sourceColumnIndex - 1 > 0"
            :colspan="columns.length - sourceColumnIndex - 1"
          />
        </template>

        <template #empty-state>
          {{ _t('No data sources yet — add one below.') }}
        </template>
      </EditableTable>
    </CmkScrollContainer>

    <DeleteWithDependentsPopup
      v-if="rowDelete.pending.value !== null"
      open
      :ids="rowDelete.pending.value.ids"
      :dependents="rowDelete.pending.value.dependents"
      @confirm="rowDelete.confirm()"
      @close="rowDelete.cancel()"
    />
  </div>
</template>

<style scoped>
.graphing-metrics-table {
  display: flex;
  flex-direction: column;
  flex: 0 1 auto;
  min-height: 0;

  --graphing-metrics-table-panel-border: var(--color-mid-grey-10);
}

body[data-theme='modern-dark'] .graphing-metrics-table {
  --graphing-metrics-table-panel-border: var(--color-mid-grey-90);
}

.graphing-metrics-table__scroll {
  flex: 0 1 auto;
  min-height: 0;
}

.graphing-metrics-table__toolbar {
  display: flex;
  flex-shrink: 0;
  justify-content: flex-end;
  align-items: center;
  gap: var(--dimension-4);
  margin-bottom: var(--dimension-5);
}

.graphing-metrics-table__bulk-actions {
  display: flex;
  gap: var(--dimension-4);
  margin-right: auto;
}

.graphing-metrics-table__expansion {
  padding: var(--dimension-5);
  padding-left: 0;
}

.graphing-metrics-table__editor-panel {
  overflow: hidden;
  border: 1px solid var(--graphing-metrics-table-panel-border);
  border-radius: var(--border-radius);
}

/* Fill the source cell without the global 10em floor forcing the column wider. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.graphing-metrics-table__add-source :deep(.cmk-dropdown-button--width-fill) {
  min-width: 0;
}
</style>
