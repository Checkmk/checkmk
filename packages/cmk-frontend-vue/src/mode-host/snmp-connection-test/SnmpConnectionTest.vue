<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type ModeHostFormKeys, type ModeHostSite } from 'cmk-shared-typing/typescript/mode_host'
import { computed, onMounted, ref } from 'vue'

import usei18n from '@/lib/i18n'
import useId from '@/lib/useId'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkButton from '@/components/CmkButton'
import CmkIcon from '@/components/CmkIcon'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

defineOptions({
  inheritAttrs: false
})

const { _t } = usei18n()

const snmpPortId = useId()
const snmpTimeoutId = useId()
const snmpRetriesId = useId()

interface Props {
  formElement: HTMLFormElement
  changeTagSnmpDs: HTMLInputElement
  tagSnmpDs: HTMLSelectElement
  tagSnmpDsDefault: HTMLDivElement
  hostnameInputElement: HTMLInputElement
  ipv4InputElement: HTMLInputElement
  ipv4InputButtonElement: HTMLInputElement
  ipv6InputElement: HTMLInputElement
  ipv6InputButtonElement: HTMLInputElement
  siteSelectElement: HTMLSelectElement
  siteInputElement: HTMLInputElement
  siteDefaultElement: HTMLDivElement
  ipAddressFamilySelectElement: HTMLSelectElement
  ipAddressFamilyInputElement: HTMLInputElement
  sites: Array<ModeHostSite>
  formKeys: ModeHostFormKeys
}

const props = defineProps<Props>()

const showTest = ref(false)

const hostname = ref(props.hostnameInputElement.value || '')
const ipV4 = ref(props.ipv4InputElement.value || '')
const ipV6 = ref(props.ipv6InputElement.value || '')
const selectedSiteIdHash = ref(props.siteSelectElement.value)
const siteId = ref(
  props.sites.find((site) => site.id_hash === selectedSiteIdHash.value)?.site_id ?? ''
)

const targetElement = ref<HTMLElement>(
  props.changeTagSnmpDs.checked
    ? (props.tagSnmpDs.parentNode as HTMLElement)
    : props.tagSnmpDsDefault
)

function getSnmpTagValue(): string {
  if (props.changeTagSnmpDs.checked) {
    return props.tagSnmpDs.value
  }
  const text = props.tagSnmpDsDefault.textContent ?? ''
  if (text.includes('No SNMP')) {
    return 'no-snmp'
  }
  if (text.includes('SNMPv1')) {
    return 'snmp-v1'
  }
  if (text.includes('SNMP')) {
    return 'snmp-v2'
  }
  return 'no-snmp'
}

function updateVisibility() {
  const tagValue = getSnmpTagValue()
  showTest.value = tagValue === 'snmp-v1' || tagValue === 'snmp-v2'
}

function updateTargetElement() {
  targetElement.value = props.changeTagSnmpDs.checked
    ? (props.tagSnmpDs.parentNode as HTMLElement)
    : props.tagSnmpDsDefault
}

onMounted(() => {
  updateVisibility()
  updateTargetElement()

  props.formElement.addEventListener('change', (e: Event) => {
    switch (e.target) {
      case props.formElement: {
        updateVisibility()
        updateTargetElement()
        break
      }
      case props.changeTagSnmpDs:
      case props.tagSnmpDs: {
        updateVisibility()
        updateTargetElement()
        isSuccess.value = false
        isError.value = false

        selectedSiteIdHash.value = props.siteSelectElement.value
        siteId.value =
          props.sites.find((site) => site.id_hash === selectedSiteIdHash.value)?.site_id ?? ''
        break
      }
      case props.siteInputElement: {
        if (props.siteInputElement.checked) {
          selectedSiteIdHash.value = props.siteSelectElement.value
          siteId.value =
            props.sites.find((site) => site.id_hash === selectedSiteIdHash.value)?.site_id ?? ''
        } else {
          siteId.value = props.siteDefaultElement.textContent?.split(' - ')[0] ?? ''
        }
        break
      }
      case props.ipv4InputButtonElement:
      case props.ipv6InputButtonElement: {
        isSuccess.value = false
        isError.value = false
        break
      }
    }
  })

  function watchInput(input: HTMLInputElement, targetRef: { value: string }) {
    input.addEventListener('input', () => {
      targetRef.value = input.value
      isSuccess.value = false
      isError.value = false
    })
  }

  watchInput(props.hostnameInputElement, hostname)
  watchInput(props.ipv4InputElement, ipV4)
  watchInput(props.ipv6InputElement, ipV6)
})

const snmpPort = ref(161)
const snmpTimeout = ref(5)
const snmpRetries = ref(1)
const showSettings = ref(false)

const isLoading = ref(false)
const isSuccess = ref(false)
const isError = ref(false)
const errorDetails = ref('')

const tooltipText = computed(() => {
  if (isLoading.value) {
    return _t('SNMP connection test running')
  }
  if (isSuccess.value) {
    return _t('SNMP connection successful')
  }
  if (isError.value) {
    return _t('SNMP connection failed')
  }
  if (!hostname.value) {
    return _t('Please enter a hostname to test SNMP connection')
  }
  return _t('Test SNMP connection')
})

function collectSnmpCommunityFields(): URLSearchParams {
  const prefix = props.formKeys.snmp_community
  const params = new URLSearchParams()

  // Collect all input/select elements whose name starts with the snmp_community prefix
  const container = document.querySelector(`div[id="attr_entry_${prefix}"]`)
  if (!container) {
    return params
  }

  container
    .querySelectorAll<HTMLInputElement | HTMLSelectElement>('input, select')
    .forEach((el) => {
      if (el.name && el.name.startsWith(prefix)) {
        params.append(el.name, el.value)
      }
    })

  return params
}

type AutomationResponse = {
  output: string
  status_code: number
}

type AjaxResponse = {
  result_code: number
  result?: AutomationResponse
}

async function startTest(): Promise<void> {
  isLoading.value = true
  isSuccess.value = false
  isError.value = false
  errorDetails.value = ''
  showSettings.value = false

  try {
    const snmpVersion = getSnmpTagValue()
    const credentialFields = collectSnmpCommunityFields()

    const postDataRaw = new URLSearchParams({
      host_name: hostname.value || '',
      ipaddress:
        (props.ipAddressFamilySelectElement.value ?? 'ip-v4-only') === 'ip-v6-only'
          ? ipV6.value || ''
          : ipV4.value || ipV6.value || '',
      address_family: props.ipAddressFamilySelectElement.value ?? 'ip-v4-only',
      snmp_version: snmpVersion,
      port: String(snmpPort.value),
      timeout: String(snmpTimeout.value),
      retries: String(snmpRetries.value),
      site_id: siteId.value
    })

    // Append all SNMP credential form fields
    credentialFields.forEach((value, key) => {
      postDataRaw.append(key, value)
    })

    const res = await fetch('wato_ajax_diag_snmp.py', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: postDataRaw.toString()
    })

    if (!res.ok) {
      throw new Error(`Error: ${res.status}`)
    }

    const data: AjaxResponse = await res.json()

    if (data.result?.status_code === 0) {
      isSuccess.value = true
    } else {
      isError.value = true
      errorDetails.value = data.result?.output ?? ''
    }
  } catch (err) {
    isError.value = true
    errorDetails.value = String(err)
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <Teleport v-if="showTest" :to="targetElement" defer>
    <span v-if="!isLoading && !isSuccess && !isError" class="mh-snmp-connection-test__controls">
      <CmkButton
        type="button"
        :title="tooltipText"
        class="mh-snmp-connection-test__button"
        :disabled="!hostname"
        @click="startTest"
      >
        <CmkIcon
          name="connection-tests"
          size="small"
          :title="tooltipText"
          class="mh-snmp-connection-test__icon"
        />
        {{ _t('Test SNMP connection') }}
      </CmkButton>

      <button
        type="button"
        class="mh-snmp-connection-test__settings-toggle"
        :title="_t('Test settings')"
        @click="showSettings = !showSettings"
      >
        <CmkIcon name="configuration" size="small" :title="_t('Test settings')" />
      </button>

      <span
        v-if="showSettings"
        class="mh-snmp-connection-test__settings-fields"
        :class="{ 'mh-snmp-connection-test__settings-fields--disabled': !hostname }"
      >
        <CmkLabel :for="snmpPortId">{{ _t('Port') }}<CmkSpace size="small" /></CmkLabel>
        <CmkInput
          :id="snmpPortId"
          v-model="snmpPort"
          :disabled="!hostname"
          type="number"
          min="1"
          max="65535"
        />
        <CmkSpace size="small" />
        <CmkLabel :for="snmpTimeoutId">{{ _t('Timeout') }}<CmkSpace size="small" /></CmkLabel>
        <CmkInput
          :id="snmpTimeoutId"
          v-model="snmpTimeout"
          :disabled="!hostname"
          type="number"
          min="1"
        />
        <CmkSpace size="small" />
        <CmkLabel :for="snmpRetriesId">{{ _t('Retries') }}<CmkSpace size="small" /></CmkLabel>
        <CmkInput
          :id="snmpRetriesId"
          v-model="snmpRetries"
          :disabled="!hostname"
          type="number"
          min="0"
        />
      </span>
    </span>

    <CmkAlertBox
      v-if="isLoading"
      variant="loading"
      size="small"
      class="mh-snmp-connection-test__loading"
    >
      {{ _t('Testing SNMP connection ...') }}
    </CmkAlertBox>

    <CmkAlertBox
      v-if="isSuccess"
      variant="success"
      size="small"
      class="mh-snmp-connection-test__success"
    >
      {{ _t('Successfully connected via SNMP.') }}
      <span class="mh-snmp-connection-test__success-actions">
        <a href="#" @click.prevent="startTest">{{ _t('Re-test SNMP connection') }}</a>

        <button
          type="button"
          class="mh-snmp-connection-test__settings-toggle"
          :title="_t('Test settings')"
          @click="showSettings = !showSettings"
        >
          <CmkIcon name="configuration" size="small" :title="_t('Test settings')" />
        </button>

        <span v-if="showSettings" class="mh-snmp-connection-test__settings-fields">
          <CmkLabel :for="snmpPortId">{{ _t('Port') }}<CmkSpace size="small" /></CmkLabel>
          <CmkInput :id="snmpPortId" v-model="snmpPort" type="number" min="1" max="65535" />
          <CmkSpace size="small" />
          <CmkLabel :for="snmpTimeoutId">{{ _t('Timeout') }}<CmkSpace size="small" /></CmkLabel>
          <CmkInput :id="snmpTimeoutId" v-model="snmpTimeout" type="number" min="1" />
          <CmkSpace size="small" />
          <CmkLabel :for="snmpRetriesId">{{ _t('Retries') }}<CmkSpace size="small" /></CmkLabel>
          <CmkInput :id="snmpRetriesId" v-model="snmpRetries" type="number" min="0" />
        </span>
      </span>
    </CmkAlertBox>

    <CmkAlertBox
      v-if="isError"
      variant="warning"
      size="small"
      class="mh-snmp-connection-test__warning"
    >
      <template #heading>{{ _t('SNMP connection failed') }}</template>
      <div class="mh-snmp-connection-test__warning-text">
        <CmkParagraph v-if="errorDetails"> {{ _t('Error: ') }} {{ errorDetails }} </CmkParagraph>
        <CmkParagraph>
          {{
            _t(
              'Could not connect to the host via SNMP. Check that the SNMP credentials are correct and that the host is reachable via SNMP.'
            )
          }}
        </CmkParagraph>
        <span class="mh-snmp-connection-test__warning-actions">
          <CmkButton
            type="button"
            :title="_t('Re-test SNMP connection')"
            class="mh-snmp-connection-test__button mh-snmp-connection-test__button--alert"
            @click="startTest"
          >
            {{ _t('Re-test SNMP connection') }}
          </CmkButton>

          <button
            type="button"
            class="mh-snmp-connection-test__settings-toggle"
            :title="_t('Test settings')"
            @click="showSettings = !showSettings"
          >
            <CmkIcon name="configuration" size="small" :title="_t('Test settings')" />
          </button>

          <span v-if="showSettings" class="mh-snmp-connection-test__settings-fields">
            <CmkLabel :for="snmpPortId">{{ _t('Port') }}<CmkSpace size="small" /></CmkLabel>
            <CmkInput :id="snmpPortId" v-model="snmpPort" type="number" min="1" max="65535" />
            <CmkSpace size="small" />
            <CmkLabel :for="snmpTimeoutId">{{ _t('Timeout') }}<CmkSpace size="small" /></CmkLabel>
            <CmkInput :id="snmpTimeoutId" v-model="snmpTimeout" type="number" min="1" />
            <CmkSpace size="small" />
            <CmkLabel :for="snmpRetriesId">{{ _t('Retries') }}<CmkSpace size="small" /></CmkLabel>
            <CmkInput :id="snmpRetriesId" v-model="snmpRetries" type="number" min="0" />
          </span>
        </span>
      </div>
    </CmkAlertBox>
  </Teleport>
</template>

<style scoped>
button {
  border: none;
  margin: 0;
  padding: 0;

  .mh-snmp-connection-test__icon {
    margin-right: var(--spacing-half);
  }
}

.mh-snmp-connection-test__controls {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  margin-left: var(--spacing-half);
}

.mh-snmp-connection-test__button {
  height: 21px;

  &.mh-snmp-connection-test__button--alert {
    margin-left: 0;
    margin-right: var(--spacing-half);
  }
}

.mh-snmp-connection-test__settings-toggle {
  background: none;
  cursor: pointer;
  margin-left: var(--spacing-half);
  opacity: 0.6;

  &:hover {
    opacity: 1;
  }
}

.mh-snmp-connection-test__settings-fields {
  display: inline-flex;
  align-items: center;
  margin-left: var(--spacing-half);

  &.mh-snmp-connection-test__settings-fields--disabled {
    opacity: 0.5;
  }
}

.mh-snmp-connection-test__loading {
  display: inline-flex;
  color: var(--font-color);
  margin: 0 0 0 var(--dimension-4);
}

.mh-snmp-connection-test__success {
  display: inline-flex;
  color: var(--font-color);
  margin: 0 0 0 var(--dimension-4);

  .mh-snmp-connection-test__success-actions {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    margin-left: var(--spacing-half);
  }
}

.mh-snmp-connection-test__warning {
  display: inline-flex;
  color: var(--font-color);
  margin: 0 0 0 var(--dimension-4);
  padding: var(--dimension-4) var(--dimension-5);

  .mh-snmp-connection-test__warning-text {
    white-space: pre-line;
    display: inline-flex;
    flex-direction: column;
  }

  .mh-snmp-connection-test__warning-actions {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    margin: var(--spacing-half) 0 0;
  }
}
</style>
