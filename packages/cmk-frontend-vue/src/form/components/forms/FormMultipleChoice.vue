<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useValidation, type ValidationMessages } from '../utils/validation'
import { computed, ref } from 'vue'
import FormValidation from '@/form/components/FormValidation.vue'
import type {
  MultipleChoice,
  MultipleChoiceElement
} from '@/form/components/vue_formspec_components'

const props = defineProps<{
  spec: MultipleChoice
  backendValidation: ValidationMessages
}>()

const data = defineModel<string[]>('data', { required: true })
const [validation, value] = useValidation<string[]>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const items = computed(() => {
  const active: MultipleChoiceElement[] = []
  const inactive: MultipleChoiceElement[] = []
  props.spec.elements.forEach((element) => {
    if (value.value.includes(element.name)) {
      active.push(element)
    } else {
      inactive.push(element)
    }
  })
  return { active: active, inactive: inactive }
})

const availableSelected = ref<string[]>([])
const activeSelected = ref<string[]>([])

function addSelected() {
  availableSelected.value.forEach((entry) => {
    if (!value.value.includes(entry)) {
      value.value.push(entry)
    }
  })
}

function removeSelected() {
  activeSelected.value.forEach((entry) => {
    const index = value.value.indexOf(entry)
    if (index !== -1) {
      value.value.splice(index, 1)
    }
  })
}

function toggleAll(allActive: boolean) {
  if (allActive) {
    value.value = props.spec.elements.map((element) => element.name)
  } else {
    value.value = []
  }
}

const selectStyle = computed(() => {
  let maxLength = 1
  props.spec.elements.forEach((element) => {
    if (element.title.length > maxLength) {
      maxLength = element.title.length
    }
  })

  return {
    height: props.spec.elements.length > 10 ? '200px' : 'auto',
    width: `${Math.max(20, Math.min(100, maxLength * 0.7))}em`
  }
})
</script>

<template>
  <div>
    <table class="vue multiple_choice">
      <tr>
        <td class="head"></td>
        <td class="head"></td>
      </tr>
      <tr>
        <td>
          <select
            :id="`${$componentId}_available`"
            v-model="availableSelected"
            aria-label="available"
            multiple
            :style="selectStyle"
          >
            <option
              v-for="element in items.inactive"
              :key="JSON.stringify(element.name)"
              :value="element.name"
              @dblclick="data.push(element.name)"
            >
              {{ element.title }}
            </option>
          </select>
        </td>
        <td>
          <div class="centered-container">
            <input type="button" value=">" @click="addSelected" />
            <input type="button" value="<" @click="removeSelected" /><br /><br />
            <input v-if="spec.show_toggle_all" type="button" value=">>" @click="toggleAll(true)" />
            <input v-if="spec.show_toggle_all" type="button" value="<<" @click="toggleAll(false)" />
          </div>
        </td>
        <td>
          <select
            :id="`${$componentId}_active`"
            v-model="activeSelected"
            aria-label="active"
            multiple
            :style="selectStyle"
          >
            <option
              v-for="element in items.active"
              :key="JSON.stringify(element.name)"
              :value="element.name"
              @dblclick="value.splice(value.indexOf(element.name), 1)"
            >
              {{ element.title }}
            </option>
          </select>
        </td>
      </tr>
    </table>
  </div>
  <FormValidation :validation="validation"></FormValidation>
</template>

<style scoped>
.centered-container {
  display: flex;
  flex-direction: column;
  align-items: center;
}
</style>
