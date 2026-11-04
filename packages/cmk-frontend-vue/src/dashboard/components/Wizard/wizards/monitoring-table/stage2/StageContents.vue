<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import CmkList from 'cmk-ui-library/components/CmkList'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import CmkMultiselectList from 'cmk-ui-library/components/user-input/CmkMultiselectList.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref, watch } from 'vue'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'
import type { MonitoringTableContent } from '@/dashboard/types/widget'
import { dateFormatChoices, timestampFormatChoices } from '@/monitoring/shared/displayOptionChoices'
import type { DisplayOptions } from '@/monitoring/shared/types'
import type { MonitoringTableColumn } from '@/monitoring/table-widget/tableDescriptors'

import ActionBar from '../../../components/ActionBar.vue'
import ActionButton from '../../../components/ActionButton.vue'
import FieldComponent from '../../../components/TableForm/FieldComponent.vue'
import FieldDescription from '../../../components/TableForm/FieldDescription.vue'
import TableForm from '../../../components/TableForm/TableForm.vue'
import TableFormRow from '../../../components/TableForm/TableFormRow.vue'
import {
  MAX_ROW_LIMIT,
  type RowLimitChoice,
  type Sorter,
  isValidRowLimit,
  parseSorters,
  rowLimitChoice,
  rowLimitOf,
  sortableColumns,
  withColumns,
  withSorters
} from '../dataConfiguration'

const { _t } = usei18n()

const props = defineProps<{
  viewTitle: TranslatedString
  catalog: MonitoringTableColumn[]
}>()

const emit = defineEmits<{
  goPrev: []
  goNext: []
}>()

const content = defineModel<MonitoringTableContent>('content', { required: true })

const limitChoice = ref<RowLimitChoice>(rowLimitChoice(content.value.limit))
const customLimit = ref<number | undefined>(content.value.limit)
const limit = computed(() => rowLimitOf(limitChoice.value, customLimit.value))
// An invalid custom limit is never stored, so that the stage reopens with the last valid one.
watch(limit, (value) => {
  if (value !== null) {
    content.value = { ...content.value, limit: value }
  }
})

const columnItems = computed(() =>
  props.catalog.map(({ id, title }) => ({ name: id, title: untranslated(title) }))
)

const columns = computed<string[]>({
  get: () => content.value.columns,
  set: (value) => (content.value = withColumns(content.value, value))
})

const sorters = computed(() => parseSorters(content.value.sort))
const sortable = computed(() => sortableColumns(content.value, props.catalog))
const unsortedColumns = computed(() =>
  sortable.value.filter(({ id }) => !sorters.value.some((sorter) => sorter.column === id))
)

function sorterColumnChoices(sorter: Sorter) {
  return sortable.value
    .filter(({ id }) => id === sorter.column || unsortedColumns.value.some((c) => c.id === id))
    .map(({ id, title }) => ({ name: id, title: untranslated(title) }))
}

function replaceSorter(index: number, sorter: Sorter | null) {
  content.value = withSorters(
    content.value,
    sorters.value.flatMap((current, i) => (i !== index ? [current] : sorter ? [sorter] : []))
  )
}

function removeSorter(index: number): boolean {
  replaceSorter(index, null)
  return true
}

function reorderSorters(order: number[]) {
  content.value = withSorters(
    content.value,
    order.map((index) => sorters.value[index]!)
  )
}

function addSorter() {
  const [column] = unsortedColumns.value
  if (column) {
    content.value = withSorters(content.value, [
      ...sorters.value,
      { column: column.id, direction: 'asc' }
    ])
  }
}

const customLimitValid = computed(() => limit.value !== null)

const columnsError = ref<TranslatedString | null>(null)
watch(
  () => content.value.columns.length,
  () => (columnsError.value = null)
)

function goNext() {
  if (content.value.columns.length === 0) {
    columnsError.value = _t('Please select at least one column.')
    return
  }
  if (!customLimitValid.value) {
    return
  }
  emit('goNext')
}
</script>

<template>
  <CmkHeading type="h1">{{ _t('Data configuration') }}</CmkHeading>

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton
      :label="_t('Previous step')"
      :icon="{ name: 'continue', side: 'left', rotate: 180 }"
      variant="secondary"
      :action="() => emit('goPrev')"
    />
    <ActionButton
      :label="_t('Next step: Visualization')"
      :icon="{ name: 'continue', side: 'right' }"
      variant="secondary"
      :action="goNext"
    />
  </ActionBar>

  <ContentSpacer />

  <CmkCatalogPanel :title="_t('View properties')" variant="padded">
    <TableForm>
      <TableFormRow>
        <FieldDescription>{{ _t('View') }}</FieldDescription>
        <FieldComponent>{{ viewTitle }}</FieldComponent>
      </TableFormRow>
      <TableFormRow>
        <FieldDescription>{{ _t('Row limit') }}</FieldDescription>
        <FieldComponent class="db-stage-contents__row-limit">
          <CmkDropdown
            :model-value="limitChoice"
            :label="_t('Row limit')"
            :options="{
              type: 'fixed',
              suggestions: [
                { name: 'default', title: untranslated('1000') },
                { name: 'max', title: untranslated(String(MAX_ROW_LIMIT)) },
                { name: 'custom', title: _t('Custom') }
              ]
            }"
            @update:model-value="(value) => (limitChoice = (value ?? 'default') as RowLimitChoice)"
          />
          <CmkInput
            v-if="limitChoice === 'custom'"
            v-model="customLimit"
            type="number"
            :aria-label="_t('Custom row limit')"
            :validators="[
              (value) =>
                isValidRowLimit(value)
                  ? []
                  : [
                      _t('Enter a whole number from 1 to %{max}.', {
                        max: String(MAX_ROW_LIMIT)
                      })
                    ]
            ]"
          />
        </FieldComponent>
      </TableFormRow>
    </TableForm>
  </CmkCatalogPanel>

  <CmkCatalogPanel :title="_t('Columns')" variant="padded">
    <TableForm>
      <TableFormRow>
        <FieldDescription>{{ _t('Columns') }}<CmkLabelRequired space="before" /></FieldDescription>
        <FieldComponent>
          <CmkInlineValidation :validation="columnsError ? [columnsError] : []" />
          <CmkMultiselectList
            v-model="columns"
            :items="columnItems"
            :label="_t('Columns')"
            :empty-text="_t('No matching columns')"
          />
        </FieldComponent>
      </TableFormRow>
      <TableFormRow>
        <FieldDescription :help="_t('How the Check age and State age columns show a date.')">{{
          _t('Date format')
        }}</FieldDescription>
        <FieldComponent>
          <CmkDropdown
            :model-value="content.date_format"
            :label="_t('Date format')"
            :options="dateFormatChoices()"
            @update:model-value="
              (value) =>
                value !== null &&
                (content = { ...content, date_format: value as DisplayOptions['dateFormat'] })
            "
          />
        </FieldComponent>
      </TableFormRow>
      <TableFormRow>
        <FieldDescription
          :help="_t('Whether the Check age and State age columns show the time, the age or both.')"
          >{{ _t('Timestamp format') }}</FieldDescription
        >
        <FieldComponent>
          <CmkDropdown
            :model-value="content.timestamp_format"
            :label="_t('Timestamp format')"
            :options="timestampFormatChoices()"
            @update:model-value="
              (value) =>
                value !== null &&
                (content = {
                  ...content,
                  timestamp_format: value as DisplayOptions['timestampFormat']
                })
            "
          />
        </FieldComponent>
      </TableFormRow>
    </TableForm>
  </CmkCatalogPanel>

  <CmkCatalogPanel :title="_t('Sorting')" variant="padded">
    <TableForm>
      <TableFormRow>
        <FieldDescription>{{ _t('Sorting') }}</FieldDescription>
        <FieldComponent>
          <CmkList
            :items-props="{ sorter: sorters }"
            :try-delete="removeSorter"
            :drag-callbacks="{ onReorder: reorderSorters }"
          >
            <template #item-props="{ index, sorter }">
              <div class="db-stage-contents__sorter">
                <CmkDropdown
                  :model-value="sorter.column"
                  :label="_t('Sort column')"
                  :options="{ type: 'fixed', suggestions: sorterColumnChoices(sorter) }"
                  @update:model-value="
                    (value) => value !== null && replaceSorter(index, { ...sorter, column: value })
                  "
                />
                <CmkDropdown
                  :model-value="sorter.direction"
                  :label="_t('Sort direction')"
                  :options="{
                    type: 'fixed',
                    suggestions: [
                      { name: 'asc', title: _t('Ascending') },
                      { name: 'desc', title: _t('Descending') }
                    ]
                  }"
                  @update:model-value="
                    (value) =>
                      replaceSorter(index, {
                        ...sorter,
                        direction: value === 'desc' ? 'desc' : 'asc'
                      })
                  "
                />
              </div>
            </template>
          </CmkList>
          <CmkButton variant="optional" :disabled="unsortedColumns.length === 0" @click="addSorter">
            {{ _t('Add sorter') }}
          </CmkButton>
        </FieldComponent>
      </TableFormRow>
    </TableForm>
  </CmkCatalogPanel>
</template>

<style scoped>
.db-stage-contents__row-limit {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--dimension-4);
}

.db-stage-contents__sorter {
  display: flex;
  align-items: center;
  gap: var(--spacing-half);
}
</style>
