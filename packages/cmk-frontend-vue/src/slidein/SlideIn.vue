<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
  DialogTrigger
} from 'radix-vue'
import { Label } from '@/quick-setup/components/ui/label'
import type { SlideInProps } from '@/slidein/slidein_types'
import Button from '@/quick-setup/components/IconButton.vue'
import FormCatalog from '@/form/components/forms/FormCatalog.vue'
import { computed, ref } from 'vue'
const data = defineModel<Record<string, Record<string, unknown>>>('data', { required: true })

defineProps<SlideInProps>()
const backendValidation = ref([])

const valueAsJSON = computed(() => {
  return JSON.stringify(data.value)
})
const save = async () => {
  console.log('Save')
}
</script>

<template>
  <DialogRoot>
    <DialogTrigger class="slide-in__trigger">{{ trigger_text }}</DialogTrigger>
    <DialogPortal>
      <DialogOverlay />
      <DialogContent class="slide-in__content">
        <DialogTitle class="slide-in__title">
          <Label variant="title">{{ catalog.title }}</Label>
          <DialogClose class="slide-in__close">
            <div class="slide-in__icon-close" />
          </DialogClose>
        </DialogTitle>
        <Button
          :label="save_button_label"
          variant="custom"
          icon-name="save"
          class="slide-in__save"
          @click="save"
        />
        <DialogClose class="slide-in__close">
          <Button :label="cancel_button_label" variant="custom" icon-name="cancel" />
        </DialogClose>
        <DialogDescription>{{ description }}</DialogDescription>
        <FormCatalog v-model:data="data" :spec="catalog" :backend-validation="backendValidation" />
        <input v-model="valueAsJSON" :name="id" type="hidden" />
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

<style scoped>
.slide-in__content {
  max-width: 80%;
  padding: 20px;
  position: fixed;
  top: 0;
  right: 0;
  height: 100%;
  border-left: 4px solid var(--default-border-color-green);
  background: var(--default-background-color);

  &[data-state='open'] {
    animation: slide-in__content-show 0.2s ease-in-out;
  }

  &[data-state='closed'] {
    animation: slide-in__content-hide 0.2s ease-in-out;
  }
}

@keyframes slide-in__content-show {
  from {
    opacity: 0;
    transform: translate(50%, 0%);
  }
  to {
    opacity: 1;
    transform: translate(0%, 0%);
  }
}

@keyframes slide-in__content-hide {
  from {
    opacity: 1;
    transform: translate(0%, 0%);
  }
  to {
    opacity: 0;
    transform: translate(50%, 0%);
  }
}

.slide-in__title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  label {
    margin-right: 10px;
  }
}

.slide-in__trigger {
  background: none;
  border: none;
  text-decoration: underline var(--success);
  padding: 0;
  margin: 0;
  font-weight: normal;
}

.slide-in__close {
  background: none;
  border: none;
  margin: 0;
  padding: 0;
}

.slide-in__save {
  border: 1px solid var(--default-submit-button-border-color);
}

div.slide-in__icon-close {
  width: 10px;
  height: 10px;
  background-size: 10px;
  background-image: var(--icon-close);
}

button {
  margin: 0 10px 0 0;
}
</style>
