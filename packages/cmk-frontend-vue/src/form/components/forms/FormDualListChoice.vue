<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref } from 'vue'
import { useValidation, type ValidationMessages } from '../utils/validation'
import { computed, onMounted, ref, useTemplateRef } from 'vue'
import CmkIcon from '@/components/CmkIcon.vue'
import FormValidation from '@/form/components/FormValidation.vue'
import type {
  DualListChoice,
  MultipleChoiceElement
} from 'cmk-shared-typing/typescript/vue_formspec_components'

import { useId } from '@/form/utils'
import { fetchData } from '../utils/autocompleter'

const props = defineProps<{
  spec: DualListChoice
  backendValidation: ValidationMessages
}>()

export interface DualListChoiceElement {
  name: string
  title: string
}

const data = defineModel<DualListChoiceElement[]>('data', { required: true })
const [validation, value] = useValidation<DualListChoiceElement[]>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const localElements = ref<DualListChoiceElement[]>(props.spec.elements)
const loading: Ref<boolean> = ref(false) // Loading flag

onMounted(async () => {
  if (!props.spec.autocompleter) {
    return
  }
  loading.value = true
  await fetchData<{ choices: [string, string][] }>('', props.spec.autocompleter.data).then(
    (result) => {
      localElements.value = result['choices'].map(([id, title]) => ({
        name: id,
        title: title.length > 60 ? `${title.substring(0, 57)}...` : title
      }))
      loading.value = false
    }
  )
})

const searchInactive = ref('')
const searchActive = ref('')

const searchInactiveInput = useTemplateRef<HTMLInputElement>('search-inactive-input')
const searchActiveInput = useTemplateRef<HTMLInputElement>('search-active-input')

const items = computed(() => {
  const active: MultipleChoiceElement[] = []
  const inactive: MultipleChoiceElement[] = []
  const matchesSearch = (element: MultipleChoiceElement, search: string) => {
    return !search || element.title.toLowerCase().includes(search.toLowerCase())
  }
  localElements.value.forEach((element) => {
    if (value.value.map((element) => element.name).includes(element.name)) {
      if (matchesSearch(element, searchActive.value)) {
        active.push(element)
      }
    } else {
      if (matchesSearch(element, searchInactive.value)) {
        inactive.push(element)
      }
    }
  })
  return { active: active, inactive: inactive }
})

const availableSelected = ref<string[]>([])
const activeSelected = ref<string[]>([])

function addSelected() {
  const newEntries: DualListChoiceElement[] = []
  availableSelected.value.forEach((entry) => {
    if (!value.value.map((element) => element.name).includes(entry)) {
      const element = localElements.value.find((element) => element.name === entry)
      if (element) {
        newEntries.push(element)
      }
    }
  })
  if (newEntries.length === 0) {
    return
  }
  value.value = [...value.value, ...newEntries]
  cleanSelection()
}

function removeSelected() {
  const removedEntries: string[] = []
  activeSelected.value.forEach((entry) => {
    const index = value.value.map((element) => element.name).indexOf(entry)
    if (index !== -1) {
      const element = localElements.value.find((element) => element.name === entry)
      if (element) {
        removedEntries.push(entry)
      }
    }
  })
  if (removedEntries.length === 0) {
    return
  }
  value.value = value.value.filter((entry) => !removedEntries.includes(entry.name))
  cleanSelection()
}

function toggleAll(allActive: boolean) {
  if (allActive) {
    value.value = [...value.value, ...items.value.inactive.map((element) => element)]
  } else {
    value.value = value.value.filter(
      (entry) => !items.value.active.map((element) => element.name).includes(entry.name)
    )
  }
  cleanSelection()
}

const selectStyle = computed(() => {
  let maxLength = 1
  localElements.value.forEach((element) => {
    if (element.title.length > maxLength) {
      maxLength = element.title.length
    }
  })

  return {
    height:
      localElements.value.length < 10
        ? '200px'
        : `${Math.min(localElements.value.length * 15, 400)}px`,
    width: `${Math.max(20, Math.min(100, maxLength * 0.7))}em`,
    marginTop: '3px',
    maxWidth: '440px'
  }
})

const cleanSelection = () => {
  availableSelected.value = []
  activeSelected.value = []
}

const componentId = useId()

const handleDoubleClickToAddItem = (element: DualListChoiceElement) => {
  if (!value.value.map((element) => element.name).includes(element.name)) {
    value.value = [...value.value, element]
  }
  cleanSelection()
}

const handleDoubleClickToRemoveItem = (element: DualListChoiceElement) => {
  const index = value.value.map((element) => element.name).indexOf(element.name)
  if (index !== -1) {
    value.value = value.value.filter((_, i) => i !== index)
  }
  cleanSelection()
}
</script>

<template>
  <div class="container" role="group" :aria-label="props.spec.title">
    <div v-if="loading" class="form-duallist-choice__loading">
      <CmkIcon name="load-graph" variant="inline" size="xlarge" />
      <span>{{ props.spec.i18n.autocompleter_loading }}</span>
    </div>
    <table class="vue multiple_choice">
      <thead>
        <tr class="table-header">
          <td class="head">
            <div class="selected-info">
              <div class="title">{{ props.spec.i18n.available_options }}</div>
              <div>
                {{ availableSelected.length }}/{{ items.inactive.length }}
                {{ props.spec.i18n.selected }}
              </div>
            </div>
            <div class="search-input-wrapper" :class="!!searchInactive ? 'active' : ''">
              <input
                ref="search-inactive-input"
                class="search"
                :aria-label="props.spec.i18n.search_available_options"
                @input="
                  (e: Event) => {
                    searchInactive = (e.target as HTMLInputElement).value
                    cleanSelection()
                  }
                "
              />
              <span class="icon" @click="searchInactiveInput?.focus()">
                <img />
              </span>
            </div>
          </td>
          <td class="buttons"></td>
          <td class="head">
            <div class="selected-info">
              <div class="title">{{ props.spec.i18n.selected_options }}</div>
              <div>
                {{ activeSelected.length }}/{{ items.active.length }}
                {{ props.spec.i18n.selected }}
              </div>
            </div>
            <div class="search-input-wrapper" :class="!!searchActive ? 'active' : ''">
              <input
                ref="search-active-input"
                class="search"
                :aria-label="props.spec.i18n.search_selected_options"
                @input="
                  (e: Event) => {
                    searchActive = (e.target as HTMLInputElement).value
                    cleanSelection()
                  }
                "
              />
              <span class="icon" @click="searchActiveInput?.focus()">
                <img />
              </span>
            </div>
          </td>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>
            <div v-if="items.inactive.length > 0">
              <select
                :id="`${componentId}_available`"
                v-model="availableSelected"
                :aria-label="props.spec.i18n.available_options"
                multiple
                :style="selectStyle"
              >
                <option
                  v-for="element in items.inactive"
                  :key="JSON.stringify(element.name)"
                  :value="element.name"
                  @dblclick="() => handleDoubleClickToAddItem(element)"
                >
                  {{ element.title }}
                </option>
              </select>
            </div>

            <div v-else :style="selectStyle" class="no-element-in-select">
              {{ props.spec.i18n.no_elements_available }}
            </div>
          </td>
          <td>
            <div class="centered-container">
              <button
                type="button"
                :disabled="availableSelected.length === 0"
                @click.prevent="addSelected"
              >
                {{ props.spec.i18n.add }}
              </button>
              <button type="button" @click.prevent="toggleAll(true)">
                {{ props.spec.i18n.add_all }}
              </button>
              <button type="button" @click.prevent="toggleAll(false)">
                {{ props.spec.i18n.remove_all }}
              </button>
              <button
                type="button"
                :disabled="activeSelected.length === 0"
                value="<"
                @click.prevent="removeSelected"
              >
                {{ props.spec.i18n.remove }}
              </button>
            </div>
          </td>
          <td>
            <div v-if="items.active.length > 0">
              <select
                :id="`${componentId}_active`"
                v-model="activeSelected"
                :aria-label="props.spec.i18n.selected_options"
                multiple
                :style="selectStyle"
              >
                <option
                  v-for="element in items.active"
                  :key="JSON.stringify(element.name)"
                  :value="element.name"
                  @dblclick="() => handleDoubleClickToRemoveItem(element)"
                >
                  {{ element.title }}
                </option>
              </select>
            </div>
            <div v-else :style="selectStyle" class="no-element-in-select">
              {{ props.spec.i18n.no_elements_selected }}
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <FormValidation :validation="validation"></FormValidation>
</template>

<style scoped>
.form-duallist-choice__loading {
  display: flex;
  align-items: center;
  padding-top: 12px;
}
.container {
  margin-right: 10px;
}
.centered-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;

  border-radius: 10px;
  margin: 0 10px;
  margin-bottom: calc(50% - 50px);

  button {
    margin: 5px;
    padding: 10px;
    width: 100%;
  }
}

.table-header {
  .head {
    color: var(--font-color);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    width: 100%;
    gap: 5px;

    .selected-info {
      display: flex;
      justify-content: space-between;
      align-items: center;
      .title {
        font-weight: bold;
      }
    }

    .search-input-wrapper {
      position: relative;
      display: flex;
      margin: 0;
      padding: 0;

      &.active {
        border: solid 1px var(--success);
        border-radius: 4px;
        margin: -1px;
      }
      .search {
        margin: 5px 0;
        width: 100%;
        margin: 0;
        padding-right: 28px;
      }

      .icon {
        position: absolute;
        top: 0;
        right: 0;

        img {
          content: var(--icon-search);
          cursor: pointer;
          height: 12px;
          width: 12px;
          padding: 4px;
          border-radius: 2px;
        }
      }
    }
  }
}

.head-search {
  display: flex;
  justify-content: space-between;
  align-items: center;

  input.search {
    width: 100%;
    border: 1px solid #303946;
    border-radius: 2px;
  }
}

.no-element-in-select {
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: var(--default-form-element-bg-color);
  height: 100%;
  user-select: none;
  opacity: 0.5;
  border-radius: 3px;
}
</style>
