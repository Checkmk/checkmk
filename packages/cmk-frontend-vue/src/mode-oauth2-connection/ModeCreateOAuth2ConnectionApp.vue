<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import {
  type MsGraphApi,
  type Oauth2ConnectionConfig
} from 'cmk-shared-typing/typescript/mode_oauth2_connection'
import { ref } from 'vue'

import CmkWizard from '@/components/CmkWizard'

import AuthorizeApplication from './steps/AuthorizeApplication.vue'
import DefineParams from './steps/DefineParams.vue'

const props = defineProps<Oauth2ConnectionConfig>()

const connectionObject = ref<MsGraphApi>(props.connection ?? ({} as MsGraphApi))

const currentStep = ref<number>(1)
</script>

<template>
  <div class="mode-oauth2-connection-mode-create-o-auth2connection-app">
    <CmkWizard v-model="currentStep" mode="guided">
      <DefineParams
        v-model="connectionObject"
        :urls="urls"
        :index="1"
        :is-completed="() => currentStep > 1"
      />
      <AuthorizeApplication
        v-model="connectionObject"
        :urls="urls"
        :index="2"
        :is-completed="() => currentStep > 2"
      />
    </CmkWizard>
  </div>
</template>

<style scoped>
.mode-oauth2-connection-mode-create-o-auth2connection-app {
  max-width: 628px;
}
</style>
