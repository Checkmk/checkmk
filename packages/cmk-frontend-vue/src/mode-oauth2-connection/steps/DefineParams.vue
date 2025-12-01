<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import {
  type MsGraphApi,
  type Oauth2Urls
} from 'cmk-shared-typing/typescript/mode_oauth2_connection'
import { v4 as uuid } from 'uuid'
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown/CmkDropdown.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import type { Suggestions } from '@/components/CmkSuggestions'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

const { _t } = usei18n()

const props = defineProps<CmkWizardStepProps & { urls: Oauth2Urls }>()

const suggestions: Suggestions = {
  type: 'fixed',
  suggestions: [
    {
      name: 'global_',
      title: _t('Global')
    },
    {
      name: 'china',
      title: _t('China')
    }
  ]
}

const model = defineModel<MsGraphApi>({ required: true })

const title = ref<string>(model.value.title ?? '')
const authority = ref<'global_' | 'china'>(model.value.authority ?? 'global_')
const tenantId = ref<string>(model.value.tenant_id ?? '')
const clientId = ref<string>(model.value.client_id ?? '')
const clientSecret = ref<string>(model.value.client_secret ?? '')

async function validate(): Promise<boolean> {
  if (!title.value || !tenantId.value || !clientId.value || !clientSecret.value) {
    return false
  }

  model.value = {
    type: 'ms_graph_api',
    id: uuid(),
    title: title.value,
    authority: authority.value,
    tenant_id: tenantId.value,
    client_id: clientId.value,
    client_secret: clientSecret.value,
    redirect_uri: location.origin + location.pathname.replace('wato.py', '') + props.urls.redirect
  }

  return true
}
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Define OAuth2 parameter') }}</CmkHeading>
    </template>

    <template #content>
      <div class="mode-oauth2-connection-define-params__form-row">
        <CmkLabel class="mode-oauth2-connection-define-params__label" for="description">{{
          _t('Description:')
        }}</CmkLabel>
        <CmkInput id="title" v-model="title" type="text" field-size="MEDIUM" />
      </div>
      <div class="mode-oauth2-connection-define-params__form-row">
        <CmkLabel class="mode-oauth2-connection-define-params__label" for="authority">{{
          _t('Authority:')
        }}</CmkLabel>
        <CmkDropdown
          id="client_secret"
          :options="suggestions"
          :selected-option="authority"
          :label="_t('Authority')"
        />
      </div>
      <div class="mode-oauth2-connection-define-params__form-row">
        <CmkLabel class="mode-oauth2-connection-define-params__label" for="tenant_id">{{
          _t('Tenant ID:')
        }}</CmkLabel>
        <CmkInput id="tenant_id" v-model="tenantId" type="text" field-size="MEDIUM" />
      </div>
      <div class="mode-oauth2-connection-define-params__form-row">
        <CmkLabel class="mode-oauth2-connection-define-params__label" for="client_id">{{
          _t('Client ID:')
        }}</CmkLabel>
        <CmkInput id="client_id" v-model="clientId" type="text" field-size="MEDIUM" />
      </div>
      <div class="mode-oauth2-connection-define-params__form-row">
        <CmkLabel class="mode-oauth2-connection-define-params__label" for="client_secret">{{
          _t('Client secret:')
        }}</CmkLabel>
        <CmkInput id="client_secret" v-model="clientSecret" type="password" field-size="MEDIUM" />
      </div>
    </template>

    <template #actions>
      <CmkWizardButton
        type="next"
        :override-label="_t('Start authorization')"
        :validation-cb="validate"
      />
    </template>
  </CmkWizardStep>
</template>

<style scoped>
.mode-oauth2-connection-define-params__form-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-6);
}

.mode-oauth2-connection-define-params__label {
  display: inline-block;
  width: 120px;
}
</style>
