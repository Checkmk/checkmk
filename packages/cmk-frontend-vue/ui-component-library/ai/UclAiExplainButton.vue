<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { useMswWorker } from '@ucl/_ucl/composables/useMswWorker'
import { nextTick, reactive, ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import AiExplainButtonApp from '@/ai/AiExplainButtonApp.vue'

import { aiServiceHandlers, mockConfig } from './mocks/ai-service-handlers'
import { type FixtureId, fixtures } from './mocks/mock-answers'

defineProps<{ screenshotMode: boolean }>()

const { mockLoaded } = useMswWorker(aiServiceHandlers)

const aiButtonProps = {
  button_text: 'Explain with AI',
  user_id: 'demo-user',
  site_name: 'demo-site',
  template: {
    id: 'explain-this-issue' as const,
    title: 'Explain with AI',
    legal: {
      footer_text_template:
        'This feature uses gemini-3.5-flash by Gemini Enterprise Agent Platform. The generated output can contain errors or inaccuracies and must be carefully reviewed by a human for factual correctness. Documentation and Privacy Policy',
      disclaimer_title: 'About this feature',
      disclaimer_body_template: 'This is a demo mock. No real AI service is contacted.'
    },
    context_data: {
      host_name: 'prod-web-01',
      host_state: 'Up' as const,
      service_name: 'CPU load',
      service_state: 'Critical' as const,
      is_stale: false
    }
  }
}

// Local reactive copy so the controls update the shared module-level mockConfig
// synchronously on every change.
const controls = reactive({
  fixtureId: mockConfig.fixtureId as FixtureId,
  rateLimit: mockConfig.rateLimit,
  error: mockConfig.error
})

function syncControls() {
  mockConfig.fixtureId = controls.fixtureId
  mockConfig.rateLimit = controls.rateLimit
  mockConfig.error = controls.error
}

// Bumped on every trigger to remount AiExplainButtonApp; that clears its cached
// aiTemplate so each click runs the current mockConfig fresh. Note:
// AiExplainButtonApp attaches a document-level 'cmk-ai-explain-button' listener
// in setup without removing it on unmount, so repeated triggers accumulate
// listeners in this demo. Harmless here (mock only); the production component
// mounts once per page.
const remountKey = ref(0)

// The controls' reactive state is written into the shared mockConfig at trigger
// time (syncControls runs at the start of triggerExplain), which is the only
// point the MSW handlers read it, so no per-control change handlers are needed.

async function triggerExplain() {
  syncControls()
  remountKey.value++
  await nextTick()
  const fixtureContextData = fixtures[controls.fixtureId].context_data ?? {}
  document.dispatchEvent(
    new CustomEvent('cmk-ai-explain-button', {
      detail: { ...aiButtonProps.template.context_data, ...fixtureContextData }
    })
  )
}

const fixtureOptions = Object.entries(fixtures).map(([id, f]) => ({
  id: id as FixtureId,
  label: f.label
}))
</script>

<template>
  <div class="ucl-ai-explain-button">
    <h2>Explain with AI — mock dev page</h2>
    <p>
      Renders the production <code>AiExplainButtonApp</code>. Network calls to
      <code>ai-service/api/v1/*</code> are intercepted by MSW.
    </p>

    <div v-if="mockLoaded" class="ucl-ai-explain-button__controls">
      <label>
        Fixture:
        <select v-model="controls.fixtureId">
          <option v-for="opt in fixtureOptions" :key="opt.id" :value="opt.id">
            {{ opt.label }}
          </option>
        </select>
      </label>

      <CmkCheckbox v-model="controls.rateLimit" label="Force 429 (rate limit)" />
      <CmkCheckbox v-model="controls.error" label="Force error mid-stream" />

      <button type="button" @click="triggerExplain">Trigger explain</button>

      <AiExplainButtonApp :key="remountKey" v-bind="aiButtonProps" />
    </div>
    <p v-else><i>Loading HTTP mocking (MSW)…</i></p>
  </div>
</template>

<style scoped>
.ucl-ai-explain-button {
  padding: var(--dimension-4);
}

.ucl-ai-explain-button__controls {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  margin-top: var(--dimension-4);
  padding: var(--dimension-4);
  max-width: 480px;
  border: 1px solid var(--ux-theme-5);
}
</style>
