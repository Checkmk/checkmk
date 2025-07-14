<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkIconButton from '@/components/CmkIcon.vue'
import usei18n from '@/lib/i18n'

const { t } = usei18n('cmk-code')

const props = defineProps<{
  title?: string
  code_txt: string
}>()

const showMessage = ref(false)
const errorMessage = ref('')
async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(props.code_txt)
    showMessage.value = true
    setTimeout(() => {
      showMessage.value = false
    }, 3000)
  } catch (err) {
    errorMessage.value = err as string
    console.error('Copy failed', err)
  }
}
</script>

<template>
  <CmkHeading v-if="title" type="h2" class="cmk-code__heading">{{ title }}</CmkHeading>
  <div class="code_wrapper">
    <div class="code_container">
      <pre>
        <code>{{ code_txt.trimStart() }}</code>
      </pre>
    </div>
    <div class="icon_container" @click="copyToClipboard">
      <div class="clone_icon_container">
        <CmkIconButton name="copied" variant="inline" size="medium" class="clone_icon" />
      </div>
      <span v-if="showMessage" class="message">
        <CmkIcon name="checkmark" variant="inline" size="medium" />
        {{ t('cmk-code-copy-success', 'Copied to clipboard') }}
      </span>
      <span v-if="errorMessage" class="message error">
        <CmkIcon name="cross" variant="inline" size="medium" />
        {{ t('cmk-code-copy-error', 'Copy to clipboard failed with error: ') }}{{ errorMessage }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.cmk-code__heading {
  margin-bottom: var(--spacing);
  color: var(--font-color);
}

.code_wrapper {
  display: flex;
  align-items: center;
  margin-bottom: var(--spacing);

  .code_container {
    padding: var(--spacing);
    background: var(--black);
    color: var(--white);
    border-radius: var(--spacing-half);

    pre {
      margin: 0;
      white-space: pre-line;
    }
  }

  .icon_container {
    display: flex;
    align-items: center;
    margin-left: var(--spacing);

    .clone_icon_container {
      padding: var(--spacing-half);
      background-color: var(--color-corporate-green-60);

      .clone_icon {
        margin-right: 0;
      }
    }

    .message {
      margin-left: var(--spacing);
      padding: var(--spacing-half);
      border-radius: var(--spacing-half);
      background-color: var(--color-corporate-green-60);
      color: var(--font-color);
    }
    .message.error {
      background-color: var(--error-msg-bg-color);
    }
  }
}
</style>
