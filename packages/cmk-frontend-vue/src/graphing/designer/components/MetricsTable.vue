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
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, nextTick, onMounted, ref, useTemplateRef, watch } from 'vue'

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
import { type GraphItemsStore, retainKnownRows } from '../composables/useGraphItems'
import { useItemValidation } from '../composables/useItemValidation'
import { useRowLabels } from '../composables/useRowLabels'
import { useTitleMacroHelp } from '../composables/useTitleMacroHelp'
import { useValidationMessages } from '../composables/useValidationMessages'
import {
  type DesignerItem,
  newConstantDraft,
  newMetricBackendDraft,
  newRrdMetricDraft,
  newScalarDraft,
  scalarColor
} from '../drafts'
import { type ItemId, type MetricBackendItem, isSingleLine, parseLineType } from '../types'
import type { RowIssue } from '../validation'
import DeleteWithDependentsPopup from './DeleteWithDependentsPopup.vue'
import MetricBackendRuleSlideIn from './MetricBackendRuleSlideIn.vue'
import RowEditor from './forms/RowEditor.vue'

/** Shared so an unaffected row keeps the same identity across renders. */
const NO_ISSUES: readonly RowIssue[] = Object.freeze([])

const {
  store,
  thresholds,
  metricBackendAvailable,
  createServicesAvailable,
  metricBackendDefaultTitle,
  titleMacros,
  issuesByRow,
  resolvedTitles
} = defineProps<{
  store: GraphItemsStore
  thresholds: { warning: string; critical: string }
  metricBackendAvailable: boolean
  createServicesAvailable: boolean
  /** What the engine expands `$DEFAULT_TITLE$` to for a metric-backend row. */
  metricBackendDefaultTitle: string
  titleMacros: TitleMacroGroup[]
  issuesByRow: ReadonlyMap<ItemId, RowIssue[]>
  resolvedTitles: ReadonlyMap<ItemId, string>
}>()

const emit = defineEmits<{
  'add-calculation': []
}>()

const { _t } = usei18n()
const { sourceTypeLabel, lineStyleSuggestions, lineStyleLabel } = useRowLabels()
const { isValid } = useItemValidation(store.items)
const { renderTitleMacroHelp } = useTitleMacroHelp()
const { issueMessage } = useValidationMessages()

const titleMacroHelp = renderTitleMacroHelp(titleMacros)

const rowSelection = ref<RowSelectionState>({})
const expandedRows = ref<Record<string, boolean>>({})

function isExpanded(row: DesignerItem): boolean {
  return expandedRows.value[row.id] === true
}

watch(
  () => store.items.value,
  (rows) => {
    rowSelection.value = retainKnownRows(rowSelection.value, rows)
    expandedRows.value = retainKnownRows(expandedRows.value, rows)
  }
)

const table = useTemplateRef<{ scrollToRow: (key: ItemId) => void }>('table')
const addSource = useTemplateRef<InstanceType<typeof CmkAddDropdown>>('addSource')

onMounted(() => {
  if (store.items.value.length === 0) {
    addSource.value?.focus()
  }
})

async function scrollToRow(id: ItemId): Promise<void> {
  await nextTick()
  table.value?.scrollToRow(id)
}

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
    meta: { headerHelp: titleMacroHelp }
  },
  { id: 'display_name', header: _t('Display name'), meta: { stretch: true, justify: 'left' } },
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
    ...(metricBackendAvailable ? [{ name: 'metric_backend', title: _t('Metrics backend') }] : []),
    { name: 'scalar', title: _t('Service reference line') },
    { name: 'constant', title: _t('Constant line') }
  ]
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
  void scrollToRow(id)
}

const rowActions: CellAction[] = [
  { id: 'clone', label: _t('Clone'), icon: 'clone' },
  { id: 'delete', label: _t('Delete'), icon: 'delete' }
]

/** Metric-backend rows gain an "Add rule" action once their query is complete. */
function rowActionsFor(row: DesignerItem): CellAction[] {
  if (
    metricBackendAvailable &&
    createServicesAvailable &&
    row.type === 'metric_backend' &&
    isValid(row)
  ) {
    return [
      ...rowActions,
      { id: 'add-rule', label: _t('Add rule: Metric backend (Custom query)'), icon: 'add-rule' }
    ]
  }
  return rowActions
}

const metricBackendRuleItem = ref<MetricBackendItem | null>(null)

const rowDelete = useDeleteWithDependents(store, () => {
  rowSelection.value = {}
})

function onRowAction(row: DesignerItem, action: CellAction): void {
  if (action.id === 'clone') {
    const [created] = store.clone([row.id])
    if (created !== undefined) {
      void scrollToRow(created)
    }
  } else if (action.id === 'delete') {
    rowDelete.request([row.id])
  } else if (action.id === 'add-rule' && row.type === 'metric_backend' && isValid(row)) {
    metricBackendRuleItem.value = row
  }
}

function onBulkClone(): void {
  const [firstCreated] = store.clone(selectedIds.value)
  rowSelection.value = {}
  if (firstCreated !== undefined) {
    void scrollToRow(firstCreated)
  }
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

function issuesOf(row: DesignerItem): readonly RowIssue[] {
  return issuesByRow.get(row.id) ?? NO_ISSUES
}

function isBlocking(row: DesignerItem): boolean {
  return issuesOf(row).length > 0
}

function rowVariant(row: DesignerItem): 'error' | null {
  return isBlocking(row) ? 'error' : null
}

function titleMessages(row: DesignerItem): TranslatedString[] {
  return issuesOf(row)
    .filter((issue) => issue.field === 'title')
    .map(issueMessage)
}
</script>

<template>
  <div class="graphing-metrics-table">
    <div class="graphing-metrics-table__toolbar">
      <div v-if="selectedIds.length > 0" class="graphing-metrics-table__bulk-actions">
        <span class="graphing-metrics-table__selection-count" aria-live="polite">
          {{ _t('Selected rows: %{count}', { count: selectedIds.length }) }}
        </span>
        <CmkButton
          size="small"
          :aria-label="_t('Delete selected sources')"
          @click="rowDelete.request(selectedIds)"
        >
          <CmkIcon name="delete" variant="inline" size="small" />
          {{ _t('Delete') }}
        </CmkButton>
        <CmkButton size="small" :aria-label="_t('Clone selected sources')" @click="onBulkClone">
          <CmkIcon name="clone" variant="inline" size="small" />
          {{ _t('Clone') }}
        </CmkButton>
      </div>
      <CmkButton class="graphing-metrics-table__add-calculation" @click="emit('add-calculation')">
        {{ _t('Add calculation') }}
      </CmkButton>
    </div>

    <CmkScrollContainer
      height="auto"
      max-height="none"
      class="graphing-metrics-table__scroll"
      :style="{ overflow: 'var(--graphing-designer-body-table-overflow, auto)' }"
    >
      <EditableTable
        ref="table"
        v-model:row-selection="rowSelection"
        :rows="[...store.items.value]"
        :columns="columns"
        :get-row-key="(row: DesignerItem) => row.id"
        :get-row-variant="rowVariant"
        :is-row-expanded="isExpanded"
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
            :expanded="isExpanded(row)"
            @update:expanded="expandedRows = { ...expandedRows, [row.id]: $event }"
          >
            <div class="graphing-metrics-table__title">
              <CmkIcon
                v-if="isBlocking(row)"
                name="inline-error"
                size="large"
                :aria-label="_t('Source %{id} prevents saving', { id: row.id })"
              />
              <CmkInput
                :model-value="row.title"
                :aria-label="_t('Title')"
                field-size="large"
                :external-errors="titleMessages(row)"
                @update:model-value="onTitleChange(row, $event)"
              />
            </div>
          </CollapsibleCell>
          <BaseCell column-id="display_name" vertical-align="middle" no-wrap>{{
            resolvedTitles.get(row.id) ?? row.title
          }}</BaseCell>
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
            :actions="rowActionsFor(row)"
            :max-visible="3"
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
              <RowEditor
                :row="row"
                :store="store"
                :thresholds="thresholds"
                :issues="issuesOf(row)"
              />
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
              ref="addSource"
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

    <MetricBackendRuleSlideIn
      v-if="metricBackendRuleItem !== null"
      open
      :item="metricBackendRuleItem"
      :default-title="metricBackendDefaultTitle"
      @close="metricBackendRuleItem = null"
    />
  </div>
</template>

<style scoped>
.graphing-metrics-table {
  display: flex;
  flex-direction: column;
  flex: 0 1 auto;
  min-height: 0;
}

.graphing-metrics-table__scroll {
  flex: 0 1 auto;
  min-height: 0;
}

.graphing-metrics-table__title {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

.graphing-metrics-table__toolbar {
  display: flex;
  flex-shrink: 0;
  justify-content: flex-end;
  align-items: flex-end;
  gap: var(--dimension-4);
  margin-bottom: var(--dimension-5);
}

.graphing-metrics-table__bulk-actions {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  margin-right: auto;
}

.graphing-metrics-table__selection-count {
  font-weight: var(--font-weight-bold);
}

/* Indent to the title input: the title cell's padding, its chevron, and the gap between them. */
.graphing-metrics-table__expansion {
  padding: 0 0 0 var(--dimension-8);
}

/* Fill the source cell without the global 10em floor forcing the column wider. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.graphing-metrics-table__add-source :deep(.cmk-dropdown-button--width-fill) {
  min-width: 0;
}
</style>
