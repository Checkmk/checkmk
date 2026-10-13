/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Formula } from './formula'

/** What an editor's commit produces: the AST, or the messages explaining why it cannot. */
export type CommitResult = { ast: Formula } | { errors: string[] }

/** Where the calculation form shows: in a slide-in, or in place of the designer tabs. */
export type CalculationPlacement = 'slideout' | 'inline'
