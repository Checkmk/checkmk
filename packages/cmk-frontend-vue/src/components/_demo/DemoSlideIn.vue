<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import SlideIn from '@/components/slidein/SlideIn.vue'
import type { Catalog } from '@/form/components/vue_formspec_components'

import Button from '@/components/IconButton.vue'
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
  <button class="slide-in__trigger" @click="open = !open">trigger button text</button>
  <SlideIn :open="open" :header="{ title: 'some title', closeButton: true }" @close="open = false">
    <div style="margin-bottom: 1em">
      <Button label="save text" variant="custom" icon-name="save" class="slide-in__save" />
      <Button label="cancel text" variant="custom" icon-name="cancel" @click="open = false" />
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
.slide-in__trigger {
  border: none;
  text-decoration: underline var(--success);
  padding: 0;
  margin: 0;
  font-weight: normal;
}

.slide-in__save {
  border: 1px solid var(--default-submit-button-border-color);
  /* TODO: this should be a variant/prop of the button CMK-19365 */
}
</style>
