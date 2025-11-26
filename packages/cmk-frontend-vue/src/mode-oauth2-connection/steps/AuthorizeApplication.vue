<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { MsGraphApi, Oauth2Urls } from 'cmk-shared-typing/typescript/mode_oauth2_connection'
import { ref } from 'vue'

import usei18n from '@/lib/i18n'
import { randomId } from '@/lib/randomId'
import { immediateWatch } from '@/lib/watch.ts'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import { getWizardContext } from '@/components/CmkWizard/utils.ts'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import { Oauth2ConnectionApi } from '../lib/service/oauth2-connection-api'
import { waitForRedirect } from '../lib/waitForRedirect'

const { _t } = usei18n()

const api = new Oauth2ConnectionApi()

const props = defineProps<CmkWizardStepProps & { urls: Oauth2Urls }>()

const context = getWizardContext()

const loading = ref(true)
const loadingTitle = ref(_t('Verifying the authorization...'))
const errorTitle = ref(_t('Authorization failed.'))
const authSucceeded = ref(false)
const refId = randomId()

const model = defineModel<MsGraphApi>({ required: true })

async function authorize(): Promise<string | null> {
  return new Promise((resolve) => {
    if (model.value.type) {
      const baseUrl = props.urls[model.value.type][model.value.authority ?? 'global_'].base_url
      if (baseUrl) {
        const url = new URL(
          `${baseUrl.replace('###tenant_id###', model.value.tenant_id as string)}/authorize`
        )

        url.searchParams.append('client_id', model.value.client_id as string)
        url.searchParams.append(
          'redirect_uri',
          location.origin + location.pathname.replace('wato.py', '') + props.urls.redirect
        )
        url.searchParams.append('response_type', 'code')
        url.searchParams.append('response_mode', 'query')
        url.searchParams.append('scope', '.default')
        url.searchParams.append('state', refId)

        const authWindow = open(url, '_blank')
        if (authWindow) {
          // TODO: think about how to handle the timeout properly
          waitForRedirect<string | null>(authWindow, resolve, verifyAuthorization)
        }
      }
    } else {
      resolve(null)
    }
  })
}

function verifyAuthorization(
  authWindow: WindowProxy,
  resolve: (value: string | null | PromiseLike<string | null>) => void
) {
  const params = new URL(authWindow.location.href).searchParams

  if (params.get('state') === refId) {
    const code = params.get('code')
    if (code) {
      resolve(code)
    } else {
      loading.value = false
      resolve(null)
    }
  } else {
    loading.value = false
    resolve(null)
  }

  authWindow.close()
}

async function requestAndSaveAccessToken(): Promise<boolean> {
  loadingTitle.value = _t('Requesting access token')
  try {
    const res = await api.requestAndSaveAccessToken({
      type: model.value.type,
      id: model.value.id,
      redirect_uri: model.value.redirect_uri,
      tenant_id: model.value.tenant_id as string,
      description: model.value.description as string,
      authority: model.value.authority as string,
      code: model.value.code as string,
      client_id: model.value.client_id as string,
      client_secret: model.value.client_secret as string
    })
    if (res.status !== 'success') {
      errorTitle.value = _t(`${res.message}`)
      return false
    }
    return true
  } catch (e) {
    errorTitle.value = _t(`Failed to request and save access token: ${e}`)
  }
  return false
}

immediateWatch(
  () => context.isSelected(props.index),
  async (isSelected) => {
    if (isSelected) {
      authSucceeded.value = false
      loading.value = true
      const code = await authorize()
      if (code) {
        model.value.code = code
        authSucceeded.value = await requestAndSaveAccessToken()
        loading.value = false
      } else {
        loading.value = false
        errorTitle.value = _t('Authorization was not completed. Please try again.')
      }
    }
  }
)
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Authorize application') }}</CmkHeading>
    </template>

    <template #content>
      <CmkParagraph>
        {{
          _t(
            'A new tab will be opened. Please follow the instructions to authorize the application'
          )
        }}
      </CmkParagraph>
      <span v-if="loading">
        <CmkIcon name="load-graph" />
        {{ loadingTitle }}
      </span>

      <template v-else-if="authSucceeded">
        <CmkAlertBox variant="success">
          {{ _t('OAuth2 connection created successfully!') }}
        </CmkAlertBox>
      </template>
      <CmkAlertBox v-else variant="error">
        {{ errorTitle }}
      </CmkAlertBox>
    </template>

    <template #actions>
      <CmkWizardButton type="finish" :override-label="_t('Finish')" :disabled="!authSucceeded" />
      <CmkWizardButton
        type="previous"
        :override-label="_t('Go back to restart authorization process')"
      />
    </template>
  </CmkWizardStep>
</template>
