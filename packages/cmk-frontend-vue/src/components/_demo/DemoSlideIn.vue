<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'
import FormEdit from '@/form/components/FormEdit.vue'
import SlideIn from '@/components/SlideIn.vue'
import CmkButton from '@/components/CmkButton.vue'
import CmkButtonSubmit from '@/components/CmkButtonSubmit.vue'
import CmkButtonCancel from '@/components/CmkButtonCancel.vue'
import type {
  Catalog,
  Dictionary,
  DictionaryElement,
  String,
  Topic,
  TopicElement
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkCollapsible from '@/components/CmkCollapsible.vue'
import CmkCollapsibleTitle from '@/components/CmkCollapsibleTitle.vue'

defineProps<{ screenshotMode: boolean }>()

const data = ref<Record<string, Record<string, unknown>>>({
  some_topic_id: { some_topic_element: { element_name: 'string content' } }
})

const slideOut1 = ref<boolean>(false)
const slideOut2 = ref<boolean>(false)
const slideOut3 = ref<boolean>(false)

const collapsible = ref<boolean>(false)

const catalog = ref<Catalog>({
  type: 'catalog',
  title: 'title',
  help: 'some_help',
  validators: [],
  elements: [
    {
      name: 'some_topic_id',
      title: 'some_topic_title',
      elements: [
        {
          name: 'some_topic_element',
          required: true,
          default_value: {},
          type: 'topic_element',
          parameter_form: {
            type: 'dictionary',
            title: 'dict title',
            validators: [],
            help: 'dict help',
            i18n_base: { required: 'required' },
            no_elements_text: 'no_text',
            additional_static_elements: {},
            elements: [
              {
                name: 'element_name',
                render_only: false,
                required: false,
                default_value: '',
                group: null,
                parameter_form: {
                  type: 'string',
                  label: 'string label',
                  input_hint: 'string input hint',
                  title: 'string title',
                  help: 'some string help',
                  field_size: 'MEDIUM',
                  i18n_base: { required: 'required' },
                  autocompleter: null,
                  validators: []
                } as String
              } as DictionaryElement
            ],
            groups: []
          } as Dictionary
        } as TopicElement
      ]
    } as Topic
  ],
  i18n_base: { required: 'required' }
})
</script>

<template>
  <h2>With embedded Form</h2>
  <CmkButton @click="slideOut1 = !slideOut1">open</CmkButton>
  <SlideIn
    :open="slideOut1"
    :header="{ title: 'some title', closeButton: true }"
    @close="slideOut1 = false"
  >
    <div style="margin-bottom: 1em">
      <CmkButtonSubmit>save</CmkButtonSubmit>
      <CmkButtonCancel @click="slideOut1 = false">cancel</CmkButtonCancel>
    </div>
    <div class="content">
      <FormEdit v-model:data="data" :spec="catalog" :backend-validation="[]" />
    </div>
  </SlideIn>
  <pre>{{ data }}</pre>
  <h2>With very long content</h2>
  <CmkButton @click="slideOut2 = !slideOut2">open</CmkButton>
  <SlideIn
    :open="slideOut2"
    :header="{ title: 'some title', closeButton: true }"
    @close="slideOut2 = false"
  >
    <div v-for="i in 100" :key="i">{{ i }} <br /></div>
  </SlideIn>
  <h2>With very wide content</h2>
  <CmkButton @click="slideOut3 = !slideOut3">open</CmkButton>
  <SlideIn
    :open="slideOut3"
    :header="{ title: 'some title', closeButton: true }"
    @close="slideOut3 = false"
  >
    <CmkCollapsibleTitle
      :title="'Show wide content'"
      :open="collapsible"
      @toggle-open="collapsible = !collapsible"
    />
    <CmkCollapsible :open="collapsible">
      <span v-for="i in 100" :key="i">{{ i }}</span></CmkCollapsible
    >
  </SlideIn>
</template>

<style scoped>
.content {
  min-width: 600px;
}
</style>
