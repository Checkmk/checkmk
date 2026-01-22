<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkLabel from '@/components/CmkLabel.vue'

import type { ComponentConfig, ConfiguredValues } from '../../types.ts'
import CheckboxComponent from './CheckboxComponent.vue'
import CheckboxGroupComponent from './CheckboxGroupComponent.vue'
import DropdownComponent from './DropdownComponent.vue'
import DualListComponent from './DualListComponent.vue'
import DynamicDropdownComponent from './DynamicDropdownComponent.vue'
import HiddenComponent from './HiddenComponent.vue'
import LabelQueryBuilder from './LabelGroups/LabelQueryBuilder.vue'
import type { QueryItem } from './LabelGroups/types.ts'
import { convertFromFilterStructure, convertToFilterStructure } from './LabelGroups/utils.ts'
import RadioButtonComponent from './RadioButtonComponent.vue'
import SliderComponent from './SliderComponent.vue'
import TagMatchComponent from './TagMatchComponent/TagMatchComponent.vue'
import {
  type TagMatchItem,
  dictToTagMatchItems,
  tagMatchItemsToDict
} from './TagMatchComponent/utils.ts'
import TextInputComponent from './TextInputComponent.vue'
import { type ComponentEmits } from './types.ts'

const { _t } = usei18n()

interface Props {
  component: ComponentConfig
  configuredFilterValues: ConfiguredValues | null
}

const props = defineProps<Props>()
const emit = defineEmits<ComponentEmits>()

const handleUpdate = (
  componentId: string,
  values: Record<string, string>,
  mode: 'merge' | 'overwrite' = 'merge'
): void => {
  emit('update-component-values', componentId, values, mode)
}

const onLabelComponentUpdate = (query: QueryItem[]): void => {
  if (props.component.component_type === 'label_group') {
    const converted = convertToFilterStructure(query, props.component.id)
    handleUpdate(props.component.id, converted, 'overwrite')
    return
  }
  throw new Error('Component is not of type label_group')
}

const onTagComponentUpdate = (values: TagMatchItem[]): void => {
  if (props.component.component_type === 'tag_filter') {
    handleUpdate('tag_filter', tagMatchItemsToDict(values, props.component.variable_prefix))
    return
  }
  throw new Error(`Component is not of type tag_filter: ${props.component.component_type}`)
}
</script>

<template>
  <div class="filter-component">
    <!-- Horizontal Group / Avoid Circular dependency -->
    <div v-if="component.component_type === 'horizontal_group'" class="horizontal-group">
      <div
        v-for="(childComponent, index) in component.components"
        :key="`${childComponent.component_type}-${index}`"
        class="horizontal-group-item"
      >
        <FilterInputComponent
          :component="childComponent"
          :configured-filter-values="configuredFilterValues"
          @update-component-values="handleUpdate"
        />
      </div>
    </div>

    <!-- Radio Button Component -->
    <RadioButtonComponent
      v-else-if="component.component_type === 'radio_button'"
      :component="component"
      :configured-values="configuredFilterValues"
      @update-component-values="handleUpdate"
    />

    <!-- Text Input Component -->
    <TextInputComponent
      v-else-if="component.component_type === 'text_input'"
      :component="component"
      :configured-values="configuredFilterValues"
      @update-component-values="handleUpdate"
    />

    <!-- Checkbox Component -->
    <CheckboxComponent
      v-else-if="component.component_type === 'checkbox'"
      :component="component"
      :configured-values="configuredFilterValues"
      @update-component-values="handleUpdate"
    />

    <!-- Checkbox Group Component -->
    <CheckboxGroupComponent
      v-else-if="component.component_type === 'checkbox_group'"
      :component="component"
      :configured-values="configuredFilterValues"
      @update-component-values="handleUpdate"
    />

    <!-- Static Text Component -->
    <div v-else-if="component.component_type === 'static_text'">
      <CmkLabel>
        {{ component.text }}
      </CmkLabel>
    </div>

    <!-- Hidden Component -->
    <HiddenComponent
      v-else-if="component.component_type === 'hidden'"
      :component="component"
      :configured-values="configuredFilterValues"
      @update-component-values="handleUpdate"
    />

    <!-- Dropdown Component -->
    <DropdownComponent
      v-else-if="component.component_type === 'dropdown'"
      :component="component"
      :configured-values="configuredFilterValues"
      @update-component-values="handleUpdate"
    />

    <!-- Dynamic Dropdown Component -->
    <DynamicDropdownComponent
      v-else-if="component.component_type === 'dynamic_dropdown'"
      :component="component"
      :configured-values="configuredFilterValues"
      @update-component-values="handleUpdate"
    />

    <!-- Label Query Builder Component -->
    <LabelQueryBuilder
      v-else-if="component.component_type === 'label_group'"
      :component="component"
      :model-value="convertFromFilterStructure(configuredFilterValues || {}, component.id)"
      @update:model-value="onLabelComponentUpdate"
    />

    <!-- Tag Match Component -->
    <TagMatchComponent
      v-else-if="component.component_type === 'tag_filter'"
      :component="component"
      :component-values="
        dictToTagMatchItems(configuredFilterValues || {}, component.variable_prefix)
      "
      @update:component-values="onTagComponentUpdate"
    />

    <!-- Slider Component -->
    <SliderComponent
      v-else-if="component.component_type === 'slider'"
      :component="component"
      :configured-values="configuredFilterValues"
      @update-component-values="handleUpdate"
    />

    <!-- Dual List Component -->
    <DualListComponent
      v-else-if="component.component_type === 'dual_list'"
      :component="component"
      :configured-values="configuredFilterValues"
      @update-component-values="handleUpdate"
    />

    <!-- Unknown Component Type -->
    <div v-else class="unknown-component">
      {{ _t('Placeholder for unknown component type:') }}
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-component {
  flex: 1;
  width: 100%;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.horizontal-group {
  display: flex;
  align-items: flex-end;
  flex-wrap: wrap;
  width: 100%;
  gap: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.horizontal-group-item {
  flex: 1;
  min-width: 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.unknown-component {
  color: red;
  font-style: italic;
  padding: var(--dimension-4);
  border: var(--dimension-1) solid var(--font-color);
}
</style>
