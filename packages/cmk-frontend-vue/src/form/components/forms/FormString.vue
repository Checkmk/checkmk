<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as FormSpec from '@/form/components/vue_formspec_components'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import FormValidation from '@/form/components/FormValidation.vue'
import { useId } from '@/form/utils'
import {
  ComboboxAnchor,
  ComboboxCancel,
  ComboboxContent,
  ComboboxInput,
  ComboboxRoot,
  ComboboxItem,
  ComboboxTrigger,
  ComboboxViewport
} from 'radix-vue'

import { computed, type ComputedRef } from 'vue'
import { setupAutocompleter } from '@/form/components/utils/autocompleter'

const props = defineProps<{
  spec: FormSpec.String
  backendValidation: ValidationMessages
}>()

const data = defineModel<string>('data', { required: true })
const [validation, value] = useValidation<string>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const getSize = (spec: FormSpec.StringFieldSize | undefined): number => {
  return {
    SMALL: 7,
    MEDIUM: 35,
    LARGE: 100
  }[spec || 'MEDIUM']
}

const componentId = useId()
const comboboxContentSize = computed(() => {
  return { SMALL: '100px', MEDIUM: '272px', LARGE: '722px' }[props.spec.field_size || 'MEDIUM']
})

// Autocompleter functions
type AutocompleterResponse = Record<'choices', [string, string][]>
const [autocompleterInput, autocompleterOutput] = setupAutocompleter<AutocompleterResponse>(
  props.spec.autocompleter || null
)

const options: ComputedRef<string[]> = computed(() => {
  if (autocompleterOutput.value === undefined) {
    return []
  }
  return autocompleterOutput
    .value!.choices.map((element: [string, string]) => element[0])
    .filter((element: string) => element.length > 0)
    .splice(0, 15)
})

function updateChoices(event: InputEvent) {
  autocompleterInput.value = (event.target! as HTMLInputElement).value as string
}

function resetInput() {
  value.value = ''
  autocompleterInput.value = ''
}
</script>

<template>
  <input
    v-if="!spec.autocompleter"
    :id="componentId"
    v-model="value"
    :placeholder="spec.input_hint || ''"
    type="text"
    :size="getSize(spec.field_size)"
  />
  <!-- @vue-ignore -->
  <ComboboxRoot v-if="spec.autocompleter" v-model="value" class="ComboboxRoot">
    <ComboboxAnchor class="ComboboxAnchor">
      <ComboboxInput
        class="ComboboxInput"
        :placeholder="spec.input_hint"
        :size="getSize(spec.field_size)"
        @input="updateChoices"
      />
      <ComboboxCancel class="cancel"><label @click="resetInput">×</label></ComboboxCancel>
      <ComboboxTrigger class="trigger">
        <img />
      </ComboboxTrigger>
    </ComboboxAnchor>

    <ComboboxContent class="ComboboxContent" :style="{ width: comboboxContentSize }">
      <ComboboxViewport class="ComboboxViewport">
        <!-- @vue-ignore -->
        <ComboboxItem v-for="option in options" :key="option" :value="option" class="ComboboxItem">
          <span>
            {{ option }}
          </span>
        </ComboboxItem>
      </ComboboxViewport>
    </ComboboxContent>
  </ComboboxRoot>
  <FormValidation :validation="validation"></FormValidation>
</template>

<style scoped>
.trigger img {
  width: 24px;
  height: 9px;
  opacity: 0.3;
  content: var(--icon-select-arrow);
}

button.trigger {
  margin: unset;
  padding: unset;
  position: relative;
  background: none;
  border: none;
  height: 12px;
  width: 12px;
  left: -40px;
}

button.cancel {
  margin: unset;
  padding: unset;
  position: relative;
  background: none;
  border: none;
  height: 12px;
  width: 12px;
  left: -40px;
  top: -4px;
}

.ComboboxRoot {
  position: relative;
}

.ComboboxAnchor {
  display: inline-flex;
  align-items: center;
  justify-content: left;
}

.ComboboxContent {
  z-index: 10;
  position: absolute;
  overflow: hidden;
  background-color: var(--default-select-background-color);
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  margin-top: -7px;
}

.ComboboxItem {
  display: flex;
  align-items: center;
  position: relative;
}

.ComboboxItem[data-highlighted] span {
  outline: none;
  color: var(--default-select-hover-color);
}
</style>
