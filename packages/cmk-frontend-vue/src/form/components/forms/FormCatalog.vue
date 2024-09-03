<script setup lang="ts">
import type { Catalog, Topic } from '@/form/components/vue_formspec_components'
import { ref } from 'vue'
import type { ValidationMessages } from '@/form/components/utils/validation'
import { immediateWatch } from '@/form/components/utils/watch'
import FormCatalogDictionary from './FormCatalogDictionary.vue'

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

function toggleTopic(topic: Topic) {
  hiddenTopics.value[topic.key] = !hiddenTopics.value[topic.key]
}

function setAllTopics(isOpen: boolean) {
  for (const topic of props.spec.topics) {
    hiddenTopics.value[topic.key] = !isOpen
  }
}

function getClass(key: string) {
  return {
    open: !hiddenTopics.value[key],
    closed: hiddenTopics.value[key]
  }
}
</script>

<template>
  <input type="button" value="Open all" @click="setAllTopics(true)" />
  <input type="button" value="Collapse all" @click="setAllTopics(false)" />
  <table
    v-for="topic in props.spec.topics"
    :key="topic.key"
    class="nform"
    :class="getClass(topic.key)"
  >
    <thead>
      <tr class="heading" @click="toggleTopic(topic)">
        <td colspan="2">
          <img class="vue nform treeangle" :class="getClass(topic.key)" />
          {{ topic.dictionary.title }}
        </td>
      </tr>
    </thead>
    <tbody :class="getClass(topic.key)">
      <tr>
        <td colspan="2" />
      </tr>
      <FormCatalogDictionary
        v-model="data[topic.key]!"
        :entries="topic.dictionary.elements"
        :backend-validation="backendValidation"
      />
      <!-- TODO: backendValidation can not be passed as is? it needs to be filtered by topic.key, right? -->
      <tr class="bottom">
        <td colspan="2"></td>
      </tr>
    </tbody>
  </table>
</template>
