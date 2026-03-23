<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton'
import CmkIcon from '@/components/CmkIcon'
import CmkIconButton from '@/components/CmkIconButton.vue'
import CmkPaste from '@/components/CmkPaste.vue'

defineProps<{ screenshotMode: boolean }>()

const value1 = ref('')
const value2 = ref('')
const value3 = ref('')
const value4 = ref('')
const value5 = ref('')
</script>

<template>
  <div class="ucl-cmk-paste-dev__container">
    <section>
      <h4>Text button (default)</h4>
      <p>A secondary button as the trigger, input follows.</p>
      <CmkPaste>
        <template #trigger>
          <CmkButton variant="secondary">
            <CmkIcon name="clipboard" variant="inline" size="small" />
            Paste
          </CmkButton>
        </template>
        <template #input>
          <input v-model="value1" placeholder="Paste here…" class="ucl-cmk-paste-dev__input" />
        </template>
      </CmkPaste>
    </section>

    <section>
      <h4>Icon button</h4>
      <p>A bare icon button as the trigger.</p>
      <CmkPaste>
        <template #trigger>
          <CmkIconButton name="clipboard" size="medium" title="Paste from clipboard" />
        </template>
        <template #input>
          <input v-model="value2" placeholder="Paste here…" class="ucl-cmk-paste-dev__input" />
        </template>
      </CmkPaste>
    </section>

    <section>
      <h4>Button + textarea</h4>
      <p>Pastes multi-line content into a textarea.</p>
      <CmkPaste>
        <template #trigger>
          <CmkButton variant="secondary">Paste</CmkButton>
        </template>
        <template #input>
          <textarea
            v-model="value3"
            placeholder="Paste here…"
            class="ucl-cmk-paste-dev__input ucl-cmk-paste-dev__textarea"
          />
        </template>
      </CmkPaste>
    </section>

    <section>
      <h4>Input before trigger (<code>input-first</code>)</h4>
      <p>The input is rendered before the trigger button.</p>
      <CmkPaste input-first>
        <template #trigger>
          <CmkButton variant="secondary">Paste</CmkButton>
        </template>
        <template #input>
          <input v-model="value4" placeholder="Paste here…" class="ucl-cmk-paste-dev__input" />
        </template>
      </CmkPaste>
    </section>

    <section>
      <h4>Password field + icon button, input first</h4>
      <p>Paste a secret directly into a password field.</p>
      <CmkPaste input-first>
        <template #trigger>
          <CmkIconButton name="clipboard" size="medium" title="Paste from clipboard" />
        </template>
        <template #input>
          <input
            v-model="value5"
            type="password"
            placeholder="Paste secret here…"
            class="ucl-cmk-paste-dev__input"
          />
        </template>
      </CmkPaste>
    </section>
  </div>
</template>

<style scoped>
.ucl-cmk-paste-dev__container {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
  padding: var(--dimension-5);

  h4 {
    margin: 0 0 var(--dimension-2);
  }

  p {
    margin: 0 0 var(--dimension-3);
    color: var(--font-color-dimmed);
    font-size: var(--font-size-normal);
  }

  code {
    font-family: monospace;
    font-size: var(--font-size-normal);
  }
}

.ucl-cmk-paste-dev__input {
  padding: var(--dimension-3);
  width: 260px;
  border: var(--border-width-1, 1px) solid var(--ux-color-gray-40);
  border-radius: var(--border-radius);
  background: var(--default-form-element-bg-color);
  color: var(--font-color);
  font-size: var(--font-size-normal);
}

.ucl-cmk-paste-dev__textarea {
  width: 260px;
  height: 80px;
  resize: vertical;
}
</style>
