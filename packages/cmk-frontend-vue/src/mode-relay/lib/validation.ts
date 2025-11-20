/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * Regex pattern for valid relay names.
 * Allowed characters are word characters (letters, digits, underscores),
 * dollar signs, spaces, at signs, dots, plus signs, and hyphens.
 * Must start and end with a word character or dollar sign.
 */
const RELAY_NAME_PATTERN = /^[\p{L}\p{N}_$](?:[\p{L}\p{N}_$ @.+-]*[\p{L}\p{N}_$-])?$/u

/**
 * Validates a relay name against the allowed character pattern.
 * @param name The relay name to validate
 * @returns true if the name matches the pattern, false otherwise
 */
export function hasValidRelayNameCharacters(name: string): boolean {
  return RELAY_NAME_PATTERN.test(name)
}
