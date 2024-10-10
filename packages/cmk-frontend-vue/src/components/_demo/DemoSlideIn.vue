<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import SlideIn from '@/components/slidein/SlideIn.vue'
import type { Catalog } from '@/form/components/vue_formspec_components'

import CmkButton from '@/components/CmkButton.vue'
import FormCatalog from '@/form/components/forms/FormCatalog.vue'
import { ref } from 'vue'

const data = ref<Record<string, Record<string, unknown>>>({
  some_topic_id: { element_ident: 'string content' }
})

const open = ref<boolean>(false)

const catalog = ref<Catalog>({
  type: 'catalog',
  title: 'title',
  help: 'some_help',
  validators: [],
  topics: [
    {
      ident: 'some_topic_id',
      dictionary: {
        type: 'dictionary',
        title: 'dict title',
        validators: [],
        help: 'dict help',
        elements: [
          {
            ident: 'element_ident',
            required: false,
            default_value: '',
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
      }
    }
  ]
})
</script>

<template>
  <CmkButton type="tertiary" @click="open = !open">trigger button text</CmkButton>
  <SlideIn :open="open" :header="{ title: 'some title', closeButton: true }" @close="open = false">
    <div style="margin-bottom: 1em">
      <CmkButton variant="submit">save</CmkButton>
      <CmkButton variant="cancel" @click="open = false">cancel</CmkButton>
    </div>
    <div class="content">
      <FormCatalog v-model:data="data" :spec="catalog" :backend-validation="[]" />
    </div>
  </SlideIn>
  <pre>{{ data }}</pre>
</template>

<style scoped>
.content {
  min-width: 600px;
}
</style>
