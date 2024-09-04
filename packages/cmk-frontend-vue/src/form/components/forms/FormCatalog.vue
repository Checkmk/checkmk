<script setup lang="ts">
import type { Catalog, Topic } from '@/form/components/vue_formspec_components'
import { ref } from 'vue'
import { immediateWatch } from '@/form/components/utils/watch'
import FormCatalogDictionary from './FormCatalogDictionary.vue'
import {
  groupDictionaryValidations,
  type ValidationMessages
} from '@/form/components/utils/validation'

const props = defineProps<{
  spec: Catalog
  backendValidation: ValidationMessages
}>()

const data = defineModel<Record<string, Record<string, unknown>>>('data', { required: true })

const hiddenTopics = ref<Record<string, boolean>>({})

immediateWatch(
  () => props.spec.topics,
  () => {
    hiddenTopics.value = {}
  }
)

const elementValidation = ref<Record<string, ValidationMessages>>({})
immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    const [, _elementValidation] = groupDictionaryValidations(props.spec.topics, newValidation)
    elementValidation.value = _elementValidation
  }
)

function toggleTopic(topic: Topic) {
  hiddenTopics.value[topic.ident] = !hiddenTopics.value[topic.ident]
}

function setAllTopics(isOpen: boolean) {
  for (const topic of props.spec.topics) {
    hiddenTopics.value[topic.ident] = !isOpen
  }
}

function getClass(ident: string) {
  return {
    open: !hiddenTopics.value[ident],
    closed: hiddenTopics.value[ident]
  }
}
</script>

<template>
  <input type="button" value="Open all" @click="setAllTopics(true)" />
  <input type="button" value="Collapse all" @click="setAllTopics(false)" />
  <table
    v-for="topic in props.spec.topics"
    :key="topic.ident"
    class="nform"
    :class="getClass(topic.ident)"
  >
    <thead>
      <tr class="heading" @click="toggleTopic(topic)">
        <td colspan="2">
          <img class="vue nform treeangle" :class="getClass(topic.ident)" />
          {{ topic.dictionary.title }}
        </td>
      </tr>
    </thead>
    <tbody :class="getClass(topic.ident)">
      <tr>
        <td colspan="2" />
      </tr>
      <FormCatalogDictionary
        v-model="data[topic.ident]!"
        :entries="topic.dictionary.elements"
        :backend-validation="elementValidation[topic.ident]!"
      />
      <tr class="bottom">
        <td colspan="2"></td>
      </tr>
    </tbody>
  </table>
</template>
