<script setup lang="ts">
import type { Catalog, FormSpec, Topic } from '@/form/components/vue_formspec_components'
import FormEdit from '@/form/components/FormEdit.vue'
import { onBeforeMount, ref } from 'vue'
import type { ValidationMessages } from '@/form/components/utils/validation'

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
    topic.dictionary.elements.forEach((element) => {
      const topicData = data.value[topic.key]!
      if (!(element.ident in topicData)) {
        topicData[element.ident] = element.default_value
      }
    })
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

interface TopicEntry {
  title: string
  ident: string
  required: boolean
  form: FormSpec
}

function entriesForTopic(topic: Topic) {
  const entries: TopicEntry[] = []
  topic.dictionary.elements.forEach((element) => {
    entries.push({
      title: element.parameter_form.title,
      ident: element.ident,
      required: element.required,
      form: element.parameter_form
    })
  })
  return entries
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
      <tr v-for="entry in entriesForTopic(topic)" :key="entry.ident">
        <td class="legend">
          <div class="title">
            {{ entry.title }}
            <span
              :class="{
                dots: true,
                required: entry.required
              }"
              >{{ Array(200).join('.') }}</span
            >
          </div>
        </td>
        <td class="content">
          <FormEdit
            v-model:data="(data[topic.key]! as Record<string, object>)[entry.ident]!"
            :backend-validation="backendValidation"
            :spec="entry.form"
          />
        </td>
      </tr>
      <tr class="bottom">
        <td colspan="2"></td>
      </tr>
    </tbody>
  </table>
</template>
