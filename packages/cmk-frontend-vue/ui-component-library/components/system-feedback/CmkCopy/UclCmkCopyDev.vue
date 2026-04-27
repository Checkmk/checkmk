<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from '@/components/CmkButton.vue'
import CmkChip from '@/components/CmkChip.vue'
import CmkCopy from '@/components/CmkCopy.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkIconButton from '@/components/CmkIconButton.vue'

defineProps<{ screenshotMode: boolean }>()

const exampleText = 'cmk --check myhost'
const exampleSecret = 'abc123-secret-token'
const examplePath = '/etc/check_mk/main.mk'
</script>

<template>
  <div class="ucl-cmk-copy-dev__container">
    <section>
      <h4>Icon button (default usage)</h4>
      <p>The same trigger used in <code>CmkCode</code>.</p>
      <div class="ucl-cmk-copy-dev__row">
        <code>{{ exampleText }}</code>
        <CmkCopy :text="exampleText">
          <CmkIconButton name="copied" size="medium" class="ucl-cmk-copy-dev__icon-button" />
        </CmkCopy>
      </div>
    </section>

    <section>
      <h4>Text button</h4>
      <p>A secondary button as the trigger.</p>
      <div class="ucl-cmk-copy-dev__row">
        <code>{{ exampleSecret }}</code>
        <CmkCopy :text="exampleSecret">
          <CmkButton variant="secondary">
            <CmkIcon name="copied" variant="inline" size="small" />
            Copy
          </CmkButton>
        </CmkCopy>
      </div>
    </section>

    <section>
      <h4>Chip</h4>
      <p>Clicking the chip itself copies the path.</p>
      <div class="ucl-cmk-copy-dev__row">
        <CmkCopy :text="examplePath">
          <CmkChip color="info" variant="outline" :as-div="true">{{ examplePath }}</CmkChip>
        </CmkCopy>
      </div>
    </section>
  </div>
</template>

<style scoped>
.ucl-cmk-copy-dev__container {
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

.ucl-cmk-copy-dev__row {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.ucl-cmk-copy-dev__icon-button {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--dimension-4);
  border-radius: var(--border-radius);
  border: var(--border-width-1, 1px) solid var(--color-corporate-green-50);
  background: var(--color-corporate-green-50);
  cursor: pointer;
}
</style>
