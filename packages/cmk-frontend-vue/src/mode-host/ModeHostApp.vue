<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type ModeHostFormKeys, type ModeHostI18N } from 'cmk-shared-typing/typescript/mode_host'
import PingHost from '@/mode-host/PingHost.vue'
import { onMounted, ref, type Ref } from 'vue'

const props = defineProps<{
  i18n: ModeHostI18N
  form_keys: ModeHostFormKeys
}>()

const formElement: Ref<HTMLFormElement | null> = ref(null)
const hostnameInputElement: Ref<HTMLInputElement | null> = ref(null)
const siteSelectElement: Ref<HTMLSelectElement | null> = ref(null)
const ipv4InputElement: Ref<HTMLInputElement | null> = ref(null)
const ipv4InputButtonElement: Ref<HTMLInputElement | null> = ref(null)
const ipv6InputElement: Ref<HTMLInputElement | null> = ref(null)
const ipv6InputButtonElement: Ref<HTMLInputElement | null> = ref(null)
const ipAddressFamilySelectElement: Ref<HTMLSelectElement | null> = ref(null)
const ipAddressFamilyInputElement: Ref<HTMLInputElement | null> = ref(null)

onMounted(() => {
  formElement.value = getElementBySelector(`form[id="form_${props.form_keys.form}"]`)
  hostnameInputElement.value = document.querySelector(
    `input.text[name="${props.form_keys.host_name}"]`
  )
  ipv4InputElement.value = getElementBySelector(
    `input.text[name="${props.form_keys.ipv4_address}"]`
  )
  ipv6InputElement.value = getElementBySelector(
    `input.text[name="${props.form_keys.ipv6_address}"]`
  )
  siteSelectElement.value = getElementBySelector(`select[name="${props.form_keys.site}"]`)
  ipAddressFamilySelectElement.value = getElementBySelector(
    `select[name="${props.form_keys.ip_address_family}"]`
  )
  ipAddressFamilyInputElement.value = getElementBySelector(
    `input[id="${props.form_keys.cb_change}_${props.form_keys.ip_address_family}"]`
  )
  ipv4InputButtonElement.value = getElementBySelector(
    `input[id="${props.form_keys.cb_change}_${props.form_keys.ipv4_address}"]`
  )
  ipv6InputButtonElement.value = getElementBySelector(
    `input[id="${props.form_keys.cb_change}_${props.form_keys.ipv6_address}"]`
  )
})

function getElementBySelector<T>(selector: string): T {
  const element = document.querySelector(selector) as T | null
  if (!element) {
    throw new Error(`Element with selector "${selector}" not found`)
  }
  return element
}
</script>

<template>
  <PingHost
    v-if="
      formElement &&
      hostnameInputElement &&
      siteSelectElement &&
      ipv4InputElement &&
      ipv6InputElement &&
      ipAddressFamilySelectElement &&
      ipAddressFamilyInputElement &&
      ipv4InputButtonElement &&
      ipv6InputButtonElement
    "
    :i18n="i18n"
    :form-element="formElement"
    :ip-address-family-select-element="ipAddressFamilySelectElement"
    :ip-address-family-input-element="ipAddressFamilyInputElement"
    :hostname-input-element="hostnameInputElement"
    :ipv4-input-element="ipv4InputElement"
    :ipv4-input-button-element="ipv4InputButtonElement"
    :ipv6-input-element="ipv6InputElement"
    :ipv6-input-button-element="ipv6InputButtonElement"
    :site-select-element="siteSelectElement"
  ></PingHost>
</template>

<style scoped></style>
