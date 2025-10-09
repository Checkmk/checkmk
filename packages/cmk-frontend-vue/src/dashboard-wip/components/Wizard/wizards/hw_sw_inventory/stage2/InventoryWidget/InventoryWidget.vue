<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onBeforeMount, ref } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import CmkCollapsible from '@/components/CmkCollapsible.vue'
import CmkCollapsibleTitle from '@/components/CmkCollapsibleTitle.vue'
import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkIndent from '@/components/CmkIndent.vue'
import type { Suggestion } from '@/components/suggestions'

import { dashboardAPI } from '../../../../../../utils.ts'
import ContentSpacer from '../../../../components/ContentSpacer.vue'
import FieldComponent from '../../../../components/TableForm/FieldComponent.vue'
import FieldDescription from '../../../../components/TableForm/FieldDescription.vue'
import TableForm from '../../../../components/TableForm/TableForm.vue'
import TableFormRow from '../../../../components/TableForm/TableFormRow.vue'
import WidgetVisualization from '../../../../components/WidgetVisualization/WidgetVisualization.vue'
import { type UseInventory } from './useInventory'

const { _t } = usei18n()

const handler = defineModel<UseInventory>('handler', { required: true })

defineExpose({ validate })

function validate(): boolean {
  return handler.value.validate()
}

const displayVisualizationSettings = ref<boolean>(true)
const displayHwSwPropertySelection = ref<boolean>(true)

const inventoryPaths = ref<Suggestion[]>([])

onBeforeMount(async () => {
  inventoryPaths.value = (await dashboardAPI.listAvailableInventory()).map((item) => ({
    name: item.id,
    title: untranslated(item.title)
  }))
})
</script>

<template>
  <CmkCollapsibleTitle
    :title="_t('Widget visualization')"
    :open="displayVisualizationSettings"
    class="collapsible"
    @toggle-open="displayVisualizationSettings = !displayVisualizationSettings"
  />
  <CmkCollapsible :open="displayVisualizationSettings">
    <WidgetVisualization
      v-model:show-title="handler.showTitle.value"
      v-model:show-title-background="handler.showTitleBackground.value"
      v-model:show-widget-background="handler.showWidgetBackground.value"
      v-model:title="handler.title.value"
      v-model:title-url="handler.titleUrl.value"
      v-model:title-url-enabled="handler.titleUrlEnabled.value"
      v-model:title-url-validation-errors="handler.titleUrlValidationErrors.value"
    />
  </CmkCollapsible>

  <ContentSpacer />

  <CmkCollapsibleTitle
    :title="_t('Metric selection')"
    :open="displayHwSwPropertySelection"
    class="collapsible"
    @toggle-open="displayHwSwPropertySelection = !displayHwSwPropertySelection"
  />
  <CmkCollapsible :open="displayHwSwPropertySelection">
    <CmkIndent>
      <TableForm>
        <TableFormRow>
          <FieldDescription>
            {{ _t('HW/SW inventory property') }}
          </FieldDescription>
          <FieldComponent>
            <div class="db-inventory-widget__field-component-item">
              <CmkDropdown
                v-model:selected-option="handler.inventoryPath.value"
                :input-hint="_t('Select inventory path')"
                :label="_t('Inventory path')"
                :options="{
                  type: 'fixed',
                  suggestions: inventoryPaths
                }"
              />
            </div>
          </FieldComponent>
        </TableFormRow>
      </TableForm>
    </CmkIndent>
  </CmkCollapsible>
</template>

<style scoped>
.db-inventory-widget__field-component-item {
  display: block;
  padding-bottom: var(--spacing-half);
}
</style>
