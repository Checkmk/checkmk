<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { onMounted, ref } from 'vue'

import type { CmkAsyncContentProps } from './types'

const { _t } = usei18n()

const props = defineProps<CmkAsyncContentProps>()

type State =
  | { status: 'loading' }
  | { status: 'loaded'; data: unknown }
  | { status: 'error'; error: unknown }

// Content with nothing to wait for is there from the first render, so it never
// passes through a spinner on its way in.
const state = ref<State>(props.load ? { status: 'loading' } : { status: 'loaded', data: undefined })

async function load(): Promise<void> {
  if (!props.load) {
    return
  }
  state.value = { status: 'loading' }
  try {
    state.value = { status: 'loaded', data: await props.load() }
  } catch (error) {
    state.value = { status: 'error', error }
  }
}

// The body loads itself, so a container is left with nothing to do but place it:
// the load lasts exactly as long as the body is mounted, and a container that
// drops it (a closing panel, a tab shown for the first time) gets a fresh one.
onMounted(load)
</script>

<template>
  <component :is="skeleton" v-if="state.status === 'loading' && skeleton" />
  <div v-else-if="state.status === 'loading'" class="cmk-async-content__loading">
    <CmkLoading />
  </div>
  <div v-else-if="state.status === 'error'" class="cmk-async-content__error">
    <CmkParagraph>
      {{ _t('Could not load this content.') }}
    </CmkParagraph>
    <CmkButton variant="secondary" size="small" @click="load">
      {{ _t('Retry') }}
    </CmkButton>
  </div>
  <component :is="component" v-else :data="state.data" v-bind="props.props" />
</template>

<style scoped>
.cmk-async-content__loading {
  display: flex;
  justify-content: center;
  padding: var(--spacing);
}

.cmk-async-content__error {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--spacing);
}
</style>
