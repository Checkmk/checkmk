<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import SimpleButton from './SimpleButton.vue'

export type ToggleButtonOption = {
  label: string
  value: string
}

export interface ToggleButtonGroupProps {
  options: ToggleButtonOption[]
  value?: string | null
}

const props = withDefaults(defineProps<ToggleButtonGroupProps>(), {
  value: null
})

defineEmits(['change'])

const isSelected = (value: string) => value === props.value
</script>

<template>
  <div class="toggle_buttons_container">
    <SimpleButton
      v-for="option in options"
      :key="option.value"
      class="toggle_option"
      :class="{ selected: isSelected(option.value) }"
      :label="option.label"
      :aria-label="`Toggle ${option.label}`"
      @click="$emit('change', option.value)"
    />
  </div>
</template>

<style scoped>
.toggle_buttons_container {
  width: max-content;
  padding: 5px;
  border-radius: 5px;
  border: 2px solid var(--default-border-color);
  background-color: transparent;
}

.toggle_option {
  min-width: 150px;
  border: none;
  background-color: transparent;
  padding: 3px;
}

.selected {
  background-color: var(--default-select-background-color);
}
</style>
