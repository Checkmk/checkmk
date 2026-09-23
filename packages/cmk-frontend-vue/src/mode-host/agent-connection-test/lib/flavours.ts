/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  AgentInstallCmds,
  AgentRegistrationCmds,
  AgentStatusCmds,
  UnbakedFallback
} from 'cmk-shared-typing/typescript/agent_slideout'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { AgentFlavour, CommandBlock, InstallSpec } from './types'

/**
 * The backend payload this module turns into flavours. It still names one flat
 * command field per operating system; the shape below is what the components
 * consume, so a future payload of ready-made flavours would replace only this
 * module.
 */
export interface KubernetesPayload {
  helmCommand: string
  /** The values.yaml the Helm command reads. */
  values: string
  docUrl: string
}

export interface AgentSlideoutPayload {
  installCmds: AgentInstallCmds
  registrationCmds: AgentRegistrationCmds
  statusCmds: AgentStatusCmds
  legacyAgentUrl: string | undefined
  unbakedFallback: UnbakedFallback | null
  /** Null when the host cannot receive pushed data, so Kubernetes is not offered. */
  kubernetes: KubernetesPayload | null
}

export function buildFlavours(payload: AgentSlideoutPayload): AgentFlavour[] {
  const { _t } = usei18n()

  const legacyInstallTitle = _t('Install the legacy Checkmk agent')
  const rootExtractionWarning = _t(
    'This command extracts files directly into the root directory (/). Make sure you are executing this command on the correct host.'
  )
  const downloadTitle = _t('Download the agent')
  const installTitle = _t('Install the agent')

  /**
   * Falls back to the legacy-agent documentation when the site has no agent to
   * hand out. Without that link there is nothing to show, so the flavour gets
   * no install step at all rather than an empty one.
   */
  function installOrDoc(
    spec: InstallSpec | null,
    legacyMsg: TranslatedString
  ): InstallSpec | undefined {
    if (spec !== null) {
      return spec
    }
    if (payload.legacyAgentUrl) {
      return {
        kind: 'external-doc',
        msg: legacyMsg,
        link: { title: legacyInstallTitle, url: payload.legacyAgentUrl, icon: 'learning-guide' }
      }
    }
    return undefined
  }

  const windows: AgentFlavour = {
    id: 'windows',
    title: _t('Windows'),
    install: {
      kind: 'shell-variants',
      intro: _t(
        'Run these commands on your Windows host to download and install the Checkmk agent. Please make sure to run these commands with sufficient permissions (e.g. "Run as Administrator")'
      ),
      variants: [
        {
          id: 'powershell',
          label: 'PowerShell',
          blocks: [
            {
              title: downloadTitle,
              command: payload.installCmds.windows_download_powershell ?? ''
            },
            { title: installTitle, command: payload.installCmds.windows_powershell ?? '' }
          ]
        },
        {
          id: 'cmd',
          label: 'Command Prompt',
          blocks: [
            { title: downloadTitle, command: payload.installCmds.windows_download },
            { title: installTitle, command: payload.installCmds.windows }
          ]
        }
      ]
    },
    register: {
      msg: _t(
        'After you have installed the agent, run this command on your Windows host to register the Checkmk agent controller. Please make sure to run this command with sufficient permissions (e.g. "Run as Administrator").'
      ),
      commands: {
        kind: 'shell-variants',
        variants: [
          {
            id: 'powershell',
            label: 'PowerShell',
            blocks: [{ command: payload.registrationCmds.windows_powershell ?? '' }]
          },
          {
            id: 'cmd',
            label: 'Command Prompt',
            blocks: [{ command: payload.registrationCmds.windows }]
          }
        ]
      },
      troubleshooting: 'registration-user'
    },
    status: {
      kind: 'shell-variants',
      variants: [
        {
          id: 'powershell',
          label: 'PowerShell',
          blocks: [{ command: payload.statusCmds.windows_powershell ?? payload.statusCmds.windows }]
        },
        { id: 'cmd', label: 'Command Prompt', blocks: [{ command: payload.statusCmds.windows }] }
      ]
    }
  }

  const packageIntro = _t(
    'Run this command on your Linux host to download and install the Checkmk agent.'
  )
  const packageChoices = [
    payload.installCmds.linux_deb
      ? {
          id: 'deb',
          label: 'DEB',
          intro: packageIntro,
          blocks: [{ command: payload.installCmds.linux_deb }]
        }
      : null,
    payload.installCmds.linux_rpm
      ? {
          id: 'rpm',
          label: 'RPM',
          intro: packageIntro,
          blocks: [{ command: payload.installCmds.linux_rpm }]
        }
      : null,
    payload.installCmds.linux_tgz_download
      ? {
          id: 'tgz',
          label: 'TGZ',
          intro: _t(
            'Run these commands on your Linux host to download and install the Checkmk agent.'
          ),
          blocks: [
            { title: downloadTitle, command: payload.installCmds.linux_tgz_download },
            {
              title: installTitle,
              command: payload.installCmds.linux_tgz_extract ?? '',
              warning: rootExtractionWarning
            }
          ]
        }
      : null
  ].filter((choice) => choice !== null)

  function linuxInstall(): InstallSpec | null {
    if (payload.unbakedFallback !== null) {
      return {
        kind: 'unbaked-fallback',
        intro: untranslated(payload.unbakedFallback.intro),
        blocks: payload.unbakedFallback.commands.map((command) => ({ command }))
      }
    }
    return packageChoices.length > 0 ? { kind: 'package-choice', choices: packageChoices } : null
  }

  const linux: AgentFlavour = {
    id: 'linux',
    title: _t('Linux'),
    install: installOrDoc(
      linuxInstall(),
      _t(
        'If you want to install the Checkmk agent on Linux, please read how to install the legacy agent'
      )
    ),
    register: {
      msg: _t(
        'After you have installed the agent, run this command on your Linux host to register the Checkmk agent controller.'
      ),
      commands: { kind: 'single', block: { command: payload.registrationCmds.linux } },
      troubleshooting: 'registration-user'
    },
    status: { kind: 'single', command: payload.statusCmds.linux }
  }

  const solaris: AgentFlavour = {
    id: 'solaris',
    title: _t('Solaris'),
    install: installOrDoc(
      payload.installCmds.solaris
        ? {
            kind: 'commands',
            intro: _t('Run this command on your Solaris host to download the Checkmk agent.'),
            blocks: [{ command: payload.installCmds.solaris }]
          }
        : null,
      _t(
        'If you want to install the Checkmk agent on Solaris, please read how to install the legacy agent'
      )
    ),
    register: {
      msg: _t(
        'After you have installed the agent, run this command on your Solaris host to register the Checkmk agent.'
      ),
      commands: { kind: 'single', block: { command: payload.registrationCmds.solaris } },
      troubleshooting: 'registration-user'
    },
    status: { kind: 'single', command: payload.statusCmds.solaris }
  }

  const aixBlocks: CommandBlock[] = [
    { title: downloadTitle, command: payload.installCmds.aix_download ?? '' },
    {
      title: installTitle,
      command: payload.installCmds.aix_extract ?? '',
      warning: rootExtractionWarning
    }
  ]

  const aix: AgentFlavour = {
    id: 'aix',
    title: _t('AIX'),
    install: installOrDoc(
      payload.installCmds.aix_download
        ? {
            kind: 'commands',
            intro: _t(
              'Run these commands on your AIX host to download and install the Checkmk agent.'
            ),
            blocks: aixBlocks
          }
        : null,
      _t(
        'If you want to install the Checkmk agent on AIX, please read how to install the legacy agent'
      )
    ),
    register: {
      msg: _t(
        'After you have installed the agent, run this command on your AIX host to register the Checkmk agent controller.'
      ),
      commands: { kind: 'single', block: { command: payload.registrationCmds.aix } },
      troubleshooting: 'registration-user'
    },
    status: { kind: 'single', command: payload.statusCmds.aix }
  }

  function kubernetesFlavour(kubernetes: KubernetesPayload): AgentFlavour {
    return {
      id: 'kubernetes',
      title: _t('Kubernetes'),
      register: {
        intro: _t(
          'Agent registration will establish trust between the Checkmk monitoring in-cluster components and the Agent Receiver on the Checkmk server.'
        ),
        msg: _t(
          'Save the configuration as values.yaml and adjust it as needed. On the selected Checkmk site, open Setup > Certificate overview and download the certificate with purpose "Signing the site certificate", then replace the site CA certificate path in this command.'
        ),
        config: {
          doc: {
            title: _t('Read the Kubernetes monitoring guide for all configuration options.'),
            url: kubernetes.docUrl,
            icon: 'learning-guide'
          },
          code: { title: _t('Minimal values.yaml'), text: kubernetes.values }
        },
        commands: { kind: 'single', block: { command: kubernetes.helmCommand } },
        troubleshooting: 'kubernetes-secret'
      }
    }
  }

  return [
    windows,
    linux,
    solaris,
    aix,
    ...(payload.kubernetes ? [kubernetesFlavour(payload.kubernetes)] : [])
  ]
}
