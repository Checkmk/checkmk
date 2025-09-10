<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkLabel from '@/components/CmkLabel.vue'

import { convertFromFilterStructure } from '../FilterInputItem/components/LabelGroups/utils.ts'
import { dictToTagMatchItems } from '../FilterInputItem/components/TagMatchComponent/utils.ts'
import type { ComponentConfig, ConfiguredValues } from '../types.ts'
import LabelQueryBuilder from './LabelQueryBuilderDisplay/LabelQueryBuilder.vue'
import TagMatchComponent from './TagMatchComponent.vue'

const { _t } = usei18n()

interface Props {
  component: ComponentConfig
  configuredFilterValues: ConfiguredValues
}

const props = defineProps<Props>()
</script>

<template>
  <div class="filter-component">
    <div v-if="component.component_type === 'horizontal_group'" class="horizontal-group">
      <div
        v-for="(childComponent, index) in component.components"
        :key="index"
        class="horizontal-group-item"
      >
        <FilterDisplayComponentRenderer
          :component="childComponent"
          :configured-filter-values="configuredFilterValues"
        />
      </div>
    </div>
    <div v-else-if="component.component_type === 'text_input'">
      <CmkLabel>
        {{ (component.label ? `${component.label} ` : '') + configuredFilterValues[component.id] }}
      </CmkLabel>
    </div>
    <div v-else-if="component.component_type === 'static_text'">
      <CmkLabel>
        {{ component.text }}
      </CmkLabel>
    </div>
    <div v-else-if="component.component_type === 'dropdown'">
      <CmkLabel>
        {{
          (component.label ? `${component.label} :` : '') +
          component.choices[configuredFilterValues[component.id]!]
        }}
      </CmkLabel>
    </div>
    <div v-else-if="component.component_type === 'dynamic_dropdown'">
      <CmkLabel>
        {{ configuredFilterValues[component.id]! }}
      </CmkLabel>
    </div>
    <div v-else-if="component.component_type === 'radio_button'">
      <CmkLabel>
        {{ component.choices[configuredFilterValues[component.id]!] }}
      </CmkLabel>
    </div>
    <div v-else-if="component.component_type === 'checkbox'">
      <CmkLabel v-if="configuredFilterValues[component.id] === 'on'">
        {{ component.label }}
      </CmkLabel>
    </div>
    <div v-else-if="component.component_type === 'checkbox_group'">
      <CmkLabel v-if="component.label"> {{ component.label }}: </CmkLabel>
      <div class="checkbox-group-container">
        <div v-for="[choiceId, choiceLabel] in Object.entries(component.choices)" :key="choiceId">
          <span v-if="configuredFilterValues[choiceId] === 'on'">
            <CmkLabel>{{ choiceLabel }}</CmkLabel>
          </span>
        </div>
        <div
          v-if="
            component.label &&
            !Object.keys(component.choices).some(
              (choiceId) => configuredFilterValues[choiceId] === 'on'
            )
          "
          class="checkbox-no-selection"
        >
          {{ _t('No items selected') }}
        </div>
      </div>
    </div>
    <div v-else-if="component.component_type === 'slider'">
      <CmkLabel>
        {{ configuredFilterValues[component.id] }}
      </CmkLabel>
    </div>
    <LabelQueryBuilder
      v-else-if="component.component_type === 'label_group'"
      :component="component"
      :model-value="convertFromFilterStructure(props.configuredFilterValues || {}, component.id)"
    />
    <TagMatchComponent
      v-else-if="component.component_type === 'tag_filter'"
      :component="component"
      :model-value="
        dictToTagMatchItems(props.configuredFilterValues || {}, component.variable_prefix)
      "
    />
    <!-- Unknown Component Type -->
    <div v-else class="unknown-component">
      {{ _t('Placeholder for unknown component type:') }} {{ component.component_type }}
    </div>
  </div>
</template>

<style scoped>
.filter-component {
  flex: 1;
  width: 100%;
}

.horizontal-group {
  display: flex;
  flex-wrap: wrap;
  width: 100%;
  gap: var(--dimension-4);
}

.horizontal-group-item {
  flex: 1;
  min-width: 0;
}

.checkbox-group-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.checkbox-no-selection {
  padding: var(--dimension-3) var(--dimension-4);
  color: #666;
  font-style: italic;
  font-size: var(--font-size-large);
}
</style>
