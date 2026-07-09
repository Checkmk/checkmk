<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkCode from '@/components/CmkCode.vue'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

const { _t } = usei18n()

defineProps<CmkWizardStepProps>()

const installScript = `# Enable the Windows features required for WSL2 (no reboot yet)
Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform, Microsoft-Windows-Subsystem-Linux -NoRestart -All

# Fetch the download URL of the latest official WSL package from GitHub
$msiUrl = (Invoke-RestMethod "https://api.github.com/repos/microsoft/WSL/releases/latest").assets.browser_download_url | Where-Object { $_ -match '\\.x64\\.msi$' }
$installerPath = "$env:TEMP\\wsl-latest.msi"

# Download the installer
$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest -Uri $msiUrl -OutFile $installerPath

# Verify the installer is signed by Microsoft before running it
$sig = Get-AuthenticodeSignature -FilePath $installerPath
if ($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch 'O=Microsoft') {
    Remove-Item $installerPath
    throw "Security check failed: invalid or non-Microsoft signature. Aborting."
}

# Install WSL2 machine-wide, silently
Start-Process msiexec.exe -Wait -ArgumentList "/i $installerPath /qn /norestart"

# Restart the computer to finish the installation
Restart-Computer -Force`
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2">{{ _t('Install WSL2') }}</CmkHeading>
    </template>

    <template #content>
      <CmkParagraph>
        {{
          _t(
            'The Relay on Windows runs inside WSL2 (Windows Subsystem for Linux 2). ' +
              'Run the script below in an elevated PowerShell to set it up. It enables the ' +
              'required Windows features, downloads the latest official WSL package from ' +
              "Microsoft's GitHub repository, verifies that it is signed by Microsoft, and " +
              'then installs it.'
          )
        }}
      </CmkParagraph>
      <CmkCode :code_txt="installScript" data-testid="install-wsl2-command"></CmkCode>
      <CmkAlertBox variant="warning">
        {{
          _t(
            'This script requires administrator privileges and will restart the computer ' +
              'automatically, without further confirmation, once the installation completes. ' +
              'Save your work before running it.'
          )
        }}
      </CmkAlertBox>
    </template>

    <template #actions>
      <CmkWizardButton type="next" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
