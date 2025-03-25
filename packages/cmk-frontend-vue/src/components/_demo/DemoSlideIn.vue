<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import SlideIn from '@/components/SlideIn.vue'
import type { Catalog, Dictionary } from 'cmk-shared-typing/typescript/vue_formspec_components'

import CmkButton from '@/components/CmkButton.vue'
import CmkButtonSubmit from '@/components/CmkButtonSubmit.vue'
import CmkButtonCancel from '@/components/CmkButtonCancel.vue'
import FormCatalog from '@/form/components/forms/form_catalog/FormCatalog.vue'
import { ref } from 'vue'

defineProps<{ screenshotMode: boolean }>()

const data = ref<Record<string, Record<string, unknown>>>({
  some_topic_id: { element_name: 'string content' }
})

const scrollOpen = ref<boolean>(false)
const open = ref<boolean>(false)

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
          name: 'element_name',
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
                  title: 'string title',
                  help: 'some string help',
                  validators: []
                }
              }
            ],
            layout: 'one_column',
            groups: []
          } as Dictionary
        }
      ]
    }
  ],
  i18n_base: { required: 'required' }
})
</script>

<template>
  <h2>With embedded Form</h2>
  <CmkButton @click="open = !open">trigger button text</CmkButton>
  <SlideIn :open="open" :header="{ title: 'some title', closeButton: true }" @close="open = false">
    <div style="margin-bottom: 1em">
      <CmkButtonSubmit>save</CmkButtonSubmit>
      <CmkButtonCancel @click="open = false">cancel</CmkButtonCancel>
    </div>
    <div class="content">
      <FormCatalog v-model:data="data" :spec="catalog" :backend-validation="[]" />
    </div>
  </SlideIn>
  <pre>{{ data }}</pre>
  <h2>With very long content</h2>
  <CmkButton @click="scrollOpen = !scrollOpen">open another slidein</CmkButton>
  <SlideIn
    :open="scrollOpen"
    :header="{ title: 'some title', closeButton: true }"
    @close="scrollOpen = false"
  >
    <div v-for="i in 100" :key="i">{{ i }} <br /></div>
  </SlideIn>
</template>

<style scoped>
.content {
  min-width: 600px;
}
</style>
