<script setup lang="ts">
import type { Catalog, Topic } from '@/form/components/vue_formspec_components'
import { onBeforeMount, ref } from 'vue'
import type { ValidationMessages } from '@/form/components/utils/validation'
import FormCatalogDictionary from './FormCatalogDictionary.vue'

const props = defineProps<{
  spec: Catalog
  backendValidation: ValidationMessages
}>()

const data = defineModel<Record<string, Record<string, unknown>>>('data', { required: true })

const openTopics = ref<Record<string, boolean>>({})
onBeforeMount(() => {
  openTopics.value = {}
  props.spec.topics.forEach((topic) => {
    openTopics.value[topic.key] = true
  })
})

function toggleTopic(topic: Topic) {
  openTopics.value[topic.key] = !openTopics.value[topic.key]
}

function setAllTopics(isOpen: boolean) {
  for (const key in openTopics.value) {
    openTopics.value[key] = isOpen
  }
}
</script>

<template>
  <input type="button" value="Open all" @click="setAllTopics(true)" />
  <input type="button" value="Collapse all" @click="setAllTopics(false)" />
  <table
    v-for="topic in props.spec.topics"
    :key="topic.key"
    :class="{
      nform: true,
      open: openTopics[topic.key],
      closed: !openTopics[topic.key]
    }"
  >
    <thead>
      <tr class="heading" @click="toggleTopic(topic)">
        <td colspan="2">
          <img
            :class="{
              vue: true,
              nform: true,
              treeangle: true,
              open: openTopics[topic.key],
              closed: !openTopics[topic.key]
            }"
          />
          {{ topic.dictionary.title }}
        </td>
      </tr>
    </thead>
    <tbody :class="{ open: openTopics[topic.key], closed: !openTopics[topic.key] }">
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
