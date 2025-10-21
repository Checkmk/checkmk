/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { SimpleIcons } from '@/components/CmkIcon'

const { _t } = usei18n()

export interface FirstHostTabStep {
  stepNumber: number
  title: TranslatedString
  description_top: TranslatedString
  description_bottom?: TranslatedString | undefined
  code: string
}

export interface FirstHostTabs {
  id: string
  title: TranslatedString
  icon: SimpleIcons
  steps: FirstHostTabStep[]
}

const step1Title = _t('Trigger download of the Checkmk agent package')
const step2Title = _t('Install the Checkmk agent package')
const step1Note = _t(
  'Note: The above command contains the credentials for a site user with ' +
    "limited permissions. The user's password is rotated regularly."
)
const downloadUrl =
  `${window.location.href.substring(0, window.location.href.indexOf('/check_mk/') + 9)}` +
  '/api/1.0/domain-types/agent/actions/download_by_host/' +
  'invoke?folder_name=%2Fpreconfigured_agent%2F&os_type=[OS_TYPE]&agent_type=generic'

export const tabs: FirstHostTabs[] = [
  {
    id: 'deb',
    title: _t('DEB'),
    icon: 'debian',
    steps: [
      {
        stepNumber: 1,
        title: step1Title,
        description_top: _t('Download the Checkmk agent package for your system.'),
        description_bottom: step1Note,
        code:
          '(\n' +
          'curl -o check-mk-agent.deb \\\n' +
          '--header "Accept: application/octet-stream" \\\n' +
          '--header "Authorization: Bearer agent_download [AGENT_DOWNLOAD_SECRET]" \\\n' +
          `"${downloadUrl.replace('[OS_TYPE]', 'linux_deb')}"\n` +
          ');'
      },
      {
        stepNumber: 2,
        title: step2Title,
        description_top: _t('Run this command to install the Checkmk agent on your workstation.'),
        code: 'sudo dpkg -i check-mk-agent.deb'
      }
    ]
  },
  {
    id: 'rpm',
    title: _t('RPM'),
    icon: 'redhat',
    steps: [
      {
        stepNumber: 1,
        title: step1Title,
        description_top: _t(
          'Run this command to trigger the download of the Checkmk agent onto your ' +
            'workstation that is automatically registered with your Checkmk site.'
        ),
        description_bottom: step1Note,
        code:
          '(\n' +
          'curl -o check-mk-agent.rpm \\\n' +
          '--header "Accept: application/octet-stream" \\\n' +
          '--header "Authorization: Bearer agent_download [AGENT_DOWNLOAD_SECRET]" \\\n' +
          `"${downloadUrl.replace('[OS_TYPE]', 'linux_rpm')}"\n` +
          ');'
      },
      {
        stepNumber: 2,
        title: step2Title,
        description_top: _t('Run this command to install the Checkmk agent on your workstation.'),
        code: 'sudo rpm -U check-mk-agent.rpm'
      }
    ]
  },
  {
    id: 'windows',
    title: _t('Windows'),
    icon: 'windows',
    steps: [
      {
        stepNumber: 1,
        title: step1Title,
        description_top: _t('Download the Checkmk agent package for your system.'),
        description_bottom: step1Note,
        code:
          'Invoke-WebRequest `\n' +
          `-Uri "${downloadUrl.replace('[OS_TYPE]', 'windows_msi')}" \`\n` +
          '-OutFile "check-mk-agent.msi" `\n' +
          '-Method "GET" `\n' +
          '-Headers @{\n' +
          ' "Accept" = "application/octet-stream";\n' +
          ' "Authorization" = "Bearer agent_download [AGENT_DOWNLOAD_SECRET]"\n' +
          '}'
      },
      {
        stepNumber: 2,
        title: step2Title,
        description_top: _t(
          'Run this command in PowerShell as an administrator to trigger the installation' +
            ' of the Checkmk push agent on your workstation.'
        ),
        code: 'Start-Process msiexec.exe -ArgumentList "/i `"$PWD\\check-mk-agent.msi`" /quiet /norestart" -Wait'
      }
    ]
  }
]

export const finalStepText = _t(
  'A couple of minutes after the installation, the agent will start reporting' +
    ' metrics to your site which you can see under Monitor > Overview > All hosts'
)
