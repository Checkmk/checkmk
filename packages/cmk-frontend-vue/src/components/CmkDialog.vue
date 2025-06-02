<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { isWarningDismissed } from '@/lib/userConfig'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkButton, { type ButtonVariants } from '@/components/CmkButton.vue'
import { persistWarningDismissal } from '@/lib/rest-api-client/userConfig'
import usePersistentRef from '@/lib/usePersistentRef'

const props = defineProps<{
  title?: string
  message: string
  buttons?: { title: string; variant: ButtonVariants['variant']; onclick: () => void }[]
  dismissal_button?: { title: string; key: string }
}>()

const dialogHidden = props.dismissal_button
  ? usePersistentRef(props.dismissal_button.key, false, 'session')
  : ref(false)

async function hideContent() {
  if (props.dismissal_button) {
    dialogHidden.value = true
    await persistWarningDismissal(props.dismissal_button.key)
  }
}

onMounted(() => {
  if (props.dismissal_button) {
    dialogHidden.value = isWarningDismissed(props.dismissal_button.key, dialogHidden.value)
  }
})
</script>

<template>
  <div v-if="!dialogHidden" class="cmk-dialog help">
    <div class="info_icon">
      <CmkIcon name="info" />
    </div>
    <div class="cmk-dialog__content">
      <span v-if="props.title" class="cmk-dialog__title">{{ props.title }}<br /></span>
      <span>{{ props.message }}</span>
      <div v-if="(props.buttons?.length ?? 0) > 0 || props.dismissal_button" class="buttons">
        <CmkSpace :direction="'vertical'" />
        <!-- eslint-disable vue/valid-v-for since no unique identifier is present for key -->
        <template v-for="button in props.buttons">
          <CmkButton :variant="button.variant" @click="button.onclick">
            {{ button.title }}
          </CmkButton>
          <CmkSpace />
        </template>
        <!-- eslint-enable vue/valid-v-for -->
        <CmkButton v-if="props.dismissal_button" @click="hideContent">
          {{ props.dismissal_button.title }}
        </CmkButton>
      </div>
    </div>
  </div>
</template>

<style scoped>
div.cmk-dialog {
  display: flex;

  div.cmk-dialog__content {
    background-color: var(--help-text-bg-color);
    color: var(--help-text-font-color);
    border-radius: 0 4px 4px 0;
    flex-grow: 1;
    padding: var(--spacing);

    & > .cmk-dialog__title {
      font-weight: var(--font-weight-bold);
      margin-bottom: var(--spacing);
      display: block;
    }
  }
}
</style>
