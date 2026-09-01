<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkColorPicker from 'cmk-ui-library/components/CmkColorPicker.vue'
import CmkGhostWidth from 'cmk-ui-library/components/CmkGhostWidth.vue'
import CmkToggleButtonGroup, {
  type ToggleButtonOption
} from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useId from 'cmk-ui-library/lib/useId'
import { computed, nextTick, ref } from 'vue'

import { type Domain, type FormulaDraft, type GraphItem, type ItemId, isFormula } from '../../types'
import { type RefVisibility, useCalculationEditor } from '../composables/useCalculationEditor'
import type { FunctionName, OperatorSymbol } from '../formula'
import FormulaEditor from './FormulaEditor.vue'
import ItemIdLabel from './ItemIdLabel.vue'
import ItemListPanel from './ItemListPanel.vue'
import type { SectionAlert } from './ItemListSection.vue'
import OperatorBar from './OperatorBar.vue'
import TransformationEditor from './TransformationEditor.vue'

const { _t } = usei18n()

const { items, nextId, nextColor } = defineProps<{
  items: readonly GraphItem[]
  /** Id the next added item will get. */
  nextId: ItemId
  /** Default color for the next added item. */
  nextColor: string
}>()

const emit = defineEmits<{
  add: [draft: FormulaDraft, refVisibility: RefVisibility]
  update: [id: ItemId, draft: FormulaDraft, refVisibility: RefVisibility]
  delete: [id: ItemId]
}>()

const DOMAIN: Domain = 'rrd'

const operatorsLabelId = useId()
const titleId = useId()

const {
  mode,
  editingId,
  title,
  color,
  hideSourceMetrics,
  formula,
  transformation,
  successAlert,
  itemBlockReason,
  switchMode,
  startEdit,
  insertRef,
  commit,
  dismissAlert
} = useCalculationEditor(
  () => items,
  DOMAIN,
  () => nextId,
  () => nextColor
)

const displayId = computed(() => editingId.value ?? nextId)

const { text: formulaText, errors: formulaErrors, appendOperator, wrapFunction } = formula
const {
  selectedId,
  percentile,
  errors: transformationErrors,
  metricOptions,
  percentileOptions
} = transformation

const modeOptions: ToggleButtonOption[] = [
  { label: _t('Operations'), value: 'operations' },
  { label: _t('Transformation'), value: 'transformation' }
]

const calculateLabelVariants = [_t('Calculate & add'), _t('Calculate & update')]
const calculateLabel = computed(() =>
  editingId.value === null ? _t('Calculate & add') : _t('Calculate & update')
)

function onModeChange(value: string): void {
  if (value === 'operations' || value === 'transformation') {
    switchMode(value)
  }
}

const alert = computed<SectionAlert | null>(() => {
  const current = successAlert.value
  if (current === null) {
    return null
  }
  return {
    id: current.id,
    nonce: current.nonce,
    text: current.kind === 'added' ? _t('Calculation added') : _t('Calculation updated')
  }
})

const formulaEditorRef = ref<InstanceType<typeof FormulaEditor> | null>(null)

function focus(): void {
  formulaEditorRef.value?.focus()
}
defineExpose({ focus })

function onCalculate(): void {
  const result = commit()
  if ('errors' in result) {
    return
  }
  if (result.kind === 'add') {
    emit('add', result.draft, result.refVisibility)
  } else {
    emit('update', result.id, result.draft, result.refVisibility)
  }
}

function onInsertOperator(symbol: OperatorSymbol): void {
  appendOperator(symbol)
  focus()
}

function onWrapFunction(name: FunctionName): void {
  wrapFunction(name)
  focus()
}

function onInsertId(id: ItemId): void {
  insertRef(id)
  if (mode.value === 'operations') {
    focus()
  }
}

function onEdit(id: ItemId): void {
  const item = items.find((candidate) => candidate.id === id)
  if (item === undefined || !isFormula(item)) {
    return
  }
  startEdit(item)
  if (mode.value === 'operations') {
    void nextTick(focus)
  }
}

function itemActionLabel(id: ItemId): TranslatedString {
  return mode.value === 'operations'
    ? _t('Insert %{id} into the formula', { id })
    : _t('Select %{id} for the transformation', { id })
}
</script>

<template>
  <div class="graphing-rrd-tab">
    <div class="graphing-rrd-tab__toggle">
      <CmkToggleButtonGroup
        :model-value="mode"
        :options="modeOptions"
        spacing="none"
        @update:model-value="onModeChange"
      />
    </div>

    <div class="graphing-rrd-tab__form">
      <div class="graphing-rrd-tab__title-field">
        <CmkHeading :id="titleId" type="h4">
          {{ _t('Formula color and title') }}
        </CmkHeading>
        <div class="graphing-rrd-tab__color-title-row">
          <CmkColorPicker v-model="color" :aria-label="_t('Formula color')">
            <ItemIdLabel :id="displayId" />
          </CmkColorPicker>
          <CmkInput
            v-model="title"
            :aria-labelledby="titleId"
            field-size="fill"
            :placeholder="_t('Default title')"
          />
        </div>
      </div>
      <FormulaEditor
        v-if="mode === 'operations'"
        ref="formulaEditorRef"
        v-model="formulaText"
        class="graphing-rrd-tab__editor"
        :errors="formulaErrors"
        @submit="onCalculate"
      />
      <TransformationEditor
        v-else
        v-model:selected-id="selectedId"
        v-model:percentile="percentile"
        class="graphing-rrd-tab__editor"
        :metric-options="metricOptions"
        :percentile-options="percentileOptions"
        :errors="transformationErrors"
      />
      <CmkButton variant="optional" class="graphing-rrd-tab__calculate" @click="onCalculate">
        <CmkGhostWidth :variants="calculateLabelVariants">
          <span class="graphing-rrd-tab__calculate-label">{{ calculateLabel }}</span>
        </CmkGhostWidth>
      </CmkButton>
      <CmkCheckbox
        v-model="hideSourceMetrics"
        class="graphing-rrd-tab__hide-checkbox"
        allow-indeterminate
        :label="_t('Hide source metrics from graph')"
      />
    </div>

    <CmkHeading type="h3" class="graphing-rrd-tab__blocks-heading">
      {{ _t('Query building blocks') }}
    </CmkHeading>
    <div class="graphing-rrd-tab__panel">
      <div
        v-if="mode === 'operations'"
        class="graphing-rrd-tab__operators"
        role="group"
        :aria-labelledby="operatorsLabelId"
      >
        <CmkHeading :id="operatorsLabelId" type="h4">
          {{ _t('Operators') }}
        </CmkHeading>
        <OperatorBar @insert="onInsertOperator" @wrap="onWrapFunction" />
      </div>
      <div class="graphing-rrd-tab__list">
        <ItemListPanel
          :items="items"
          :domain="DOMAIN"
          :action-label="itemActionLabel"
          :item-block-reason="itemBlockReason"
          :alert="alert"
          @insert-id="onInsertId"
          @edit="onEdit"
          @delete="emit('delete', $event)"
          @dismiss-alert="dismissAlert"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.graphing-rrd-tab {
  display: flex;
  flex-direction: column;

  --graphing-rrd-tab-separator: var(--color-mid-grey-10);
}

body[data-theme='modern-dark'] .graphing-rrd-tab {
  --graphing-rrd-tab-separator: var(--color-mid-grey-90);
}

.graphing-rrd-tab__toggle {
  margin-bottom: var(--dimension-7);
}

.graphing-rrd-tab__form {
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-areas:
    'title .'
    'editor calculate'
    'hide hide';
  gap: var(--dimension-4);
  align-items: end;
  margin-bottom: var(--dimension-10);
}

.graphing-rrd-tab__title-field {
  grid-area: title;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.graphing-rrd-tab__color-title-row {
  display: flex;
  gap: var(--dimension-3);
  align-items: stretch;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.graphing-rrd-tab__color-title-row :deep(.cmk-input__wrapper) {
  flex: 1 1 auto;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.graphing-rrd-tab__color-title-row :deep(.cmk-input) {
  box-sizing: border-box;
  height: var(--dimension-10);
}

.graphing-rrd-tab__editor {
  grid-area: editor;
}

.graphing-rrd-tab__calculate {
  grid-area: calculate;
}

.graphing-rrd-tab__calculate-label {
  text-align: center;
}

.graphing-rrd-tab__hide-checkbox {
  grid-area: hide;
}

.graphing-rrd-tab__blocks-heading {
  margin: 0 0 var(--dimension-6);
}

.graphing-rrd-tab__panel {
  display: flex;
  flex-direction: column;
  background: var(--ux-theme-3);
}

.graphing-rrd-tab__operators {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  padding: var(--dimension-5);
  border-bottom: 1px solid var(--graphing-rrd-tab-separator);
}

.graphing-rrd-tab__list {
  padding: var(--dimension-5);
}
</style>
