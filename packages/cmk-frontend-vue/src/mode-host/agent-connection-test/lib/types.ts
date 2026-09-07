/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

/** One command block: a caption, the command, and a warning shown above it. */
export interface CommandBlock {
  /** Omitted for a single unlabelled command. */
  title?: TranslatedString
  command: string
  warning?: TranslatedString
}

/** One selectable set of commands: a shell, or a package format. */
export interface CommandChoice {
  id: string
  label: string
  intro?: TranslatedString
  blocks: CommandBlock[]
}

export interface DocLink {
  title: TranslatedString
  url: string
  icon?: SimpleIcons
}

/**
 * How a flavour is installed. The variant is decided once, when the flavour is
 * built from the payload, so the step component does not have to guess it from
 * a set of optional fields.
 */
export type InstallSpec =
  | { kind: 'commands'; intro: TranslatedString; blocks: CommandBlock[] }
  | { kind: 'shell-variants'; intro: TranslatedString; variants: CommandChoice[] }
  | { kind: 'package-choice'; choices: CommandChoice[] }
  | { kind: 'unbaked-fallback'; intro: TranslatedString; blocks: CommandBlock[] }
  | { kind: 'external-doc'; msg: TranslatedString; link: DocLink }

export interface RegisterSpec {
  /** The sentence directly above the command. */
  msg: TranslatedString
  commands:
    | { kind: 'single'; block: CommandBlock }
    | { kind: 'shell-variants'; variants: CommandChoice[] }
  /** Which troubleshooting hint applies; absent means none. */
  troubleshooting?: 'registration-user'
}

export type StatusSpec =
  | { kind: 'single'; command: string }
  | { kind: 'shell-variants'; variants: CommandChoice[] }

/** One way of getting monitoring data out of a system. */
export interface AgentFlavour {
  id: string
  title: TranslatedString
  /** Absent means this flavour has no "Download and install" step. */
  install?: InstallSpec | undefined
  /** Absent means this flavour has no "Register agent" step. */
  register?: RegisterSpec
  /** Absent means no "Test connection" step, even in push mode. */
  status?: StatusSpec
}
