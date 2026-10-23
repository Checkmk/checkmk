const fs = require("fs");

/**
 * Extracts all rendered diagnostics from a list of Rust compiler diagnostics
 * and joins them into a newline-delimited string.
 *
 * @param diagnostics An array of Rust compiler output diagnostics
 * @returns A string containing all rendered diagnostics separated by newlines
 */
function diagnosticsToHumanReadable(diagnostics) {
  // Filter for compiler-message type items and extract their rendered diagnostic
  const renderedDiagnostics = diagnostics
    .filter(
      (message) => message.rendered
    )
    .map((message) => message.rendered);

  // Join all rendered diagnostics with newlines
  return renderedDiagnostics.join("\n");
}

/**
 * Converts Rust diagnostics to a SARIF patch file format that matches
 * the Rust implementation.
 *
 * @param diagnostics An array of Rust compiler output diagnostics
 * @returns A SARIF-compatible JSON object
 */
function diagnosticsToSarif(diagnostics) {
  // Track rule IDs with a map to assign indices
  const ruleMap = new Map();
  const rules = [];
  const results = [];

  diagnostics
    .forEach((diagnostic) => {
      // Skip diagnostics without spans
      if (!diagnostic.spans || diagnostic.spans.length === 0) {
        return;
      }

      diagnostic.spans.forEach((span) => {
        // Get or create the rule entry
        const diagnosticCode = diagnostic.code ? diagnostic.code.code : "";
        if (!ruleMap.has(diagnosticCode)) {
          // Build global message for rule description
          const globalMessage = buildGlobalMessage(diagnostic);

          // Look for help URI in child diagnostics
          const helpUri = findHelpUri(diagnostic);

          const rule = {
            id: diagnosticCode,
            fullDescription: {
              text: globalMessage,
            },
          };

          if (helpUri) {
            rule.helpUri = helpUri;
          }

          const ruleIndex = rules.length;
          ruleMap.set(diagnosticCode, ruleIndex);
          rules.push(rule);
        }

        const ruleIndex = ruleMap.get(diagnosticCode);

        // Map diagnostic level to SARIF level
        const level = mapDiagnosticLevel(diagnostic.level);

        // Create result
        const result = {
          ruleId: diagnosticCode,
          ruleIndex: ruleIndex,
          level: level,
          message: {
            text: diagnostic.message,
          },
          locations: [createLocationFromSpan(span)],
          relatedLocations: getRelatedLocations(diagnostic),
        };

        results.push(result);
      });
    });

  // Construct the full SARIF document
  return {
    $schema:
      "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0.json",
    version: "2.1.0",
    runs: [
      {
        tool: {
          driver: {
            name: "clippy",
            informationUri: "https://rust-lang.github.io/rust-clippy/",
            rules: rules,
          },
        },
        results: results,
      },
    ],
  };
}

/**
 * @typedef {Object} Replacement
 * @property {string} file_name - file name where
 * @property {number} byte_start - byte offset where this replacement starts
 * @property {number} byte_end - byte offset where this replacement ends
 * @property {string} suggested_replacement - content to replace the byte offset with
 */
/**
 * Apply diagnostics to the relevant files, in the same order as the rustfix crate.
 * Assumes the file paths referenced in diagnostics are relative to the bindir.
 * Will write the new file contents to disk.
 *
 * Please note that only the machine-applicable suggestions are applied.
 * Suggestions that may or many not be correct are ignored.
 * For more information about suggestion applicability, see the rustc documentation about suggestions:
 * - Ref: https://rustc-dev-guide.rust-lang.org/diagnostics.html?highlight=Applicabilit#suggestions
 *
 * @param diagnostics
 * @return void
 */
function applyDiagnosticsAsPatches(diagnostics) {

  // Gather all the files that need fixing, with all the fix spans
  /**
   *
   * @type {Object.<string, Replacement[]>}
   */
  let filesToFixSpans = {};

  /**
   * @param {Replacement} span
   */
  const record_span_for_file = (span) => {
    if (filesToFixSpans[span.file_name] === undefined) {
      filesToFixSpans[span.file_name] = [];
    }
    filesToFixSpans[span.file_name].push(span);
  }

  const gatherFixSpans = (diagnostic) => {
    (diagnostic.spans ?? []).forEach((span) => {
        if (span.suggested_replacement !== null && span.suggestion_applicability === "MachineApplicable") {
          record_span_for_file(span)
        }
      });

    (diagnostic.children ?? []).forEach(gatherFixSpans);
  };
  diagnostics.forEach(gatherFixSpans);

  // Apply the fixes to the file and write them to disk
  Object.entries(filesToFixSpans).forEach(applyReplacementsToFile)
}

/**
 * Apply the fixes to the files in the filesystem.
 *
 * @param {string} path_relative_to_ws_root
 * @param {Replacement[]} unsorted_replacements
 */
function applyReplacementsToFile([path_to_fix, unsorted_replacements]) {

  /**
   * @type Buffer
   */
  const fileContents = fs.readFileSync(path_to_fix); // No encoding because we want a buffer that we can replace.
  const replacements = sortReplacements(unsorted_replacements, fileContents);

  let fixedContents = Buffer.from("");
  let prev_end = 0;
  for (const span of replacements) {
    const replacementBuffer =
        Buffer.isBuffer(span.suggested_replacement)
            ? replacement
            : Buffer.from(span.suggested_replacement);

    fixedContents = Buffer.concat([
        fixedContents,
        fileContents.slice(prev_end, span.byte_start),
        replacementBuffer,
    ]);
    prev_end = span.byte_end;
  }
  fixedContents = Buffer.concat([
      fixedContents,
      fileContents.slice(prev_end),
  ])

  // Write file contents to disk
  try {
    fs.writeFileSync(path_to_fix, fixedContents);
  } catch (err) {
    console.error(`failed to write back changes to ${path_to_fix}`)
  }
}

/**
 * Maps Rust diagnostic levels to SARIF result levels
 *
 * @param level The Rust diagnostic level
 * @returns The corresponding SARIF level
 */
function mapDiagnosticLevel(level) {
  switch (level) {
    case "help":
    case "note":
      return "note";
    case "warning":
      return "warning";
    case "error":
      return "error";
    default:
      return "none";
  }
}

/**
 * Creates a SARIF location from a diagnostic span
 *
 * @param span The diagnostic span
 * @returns A SARIF location object
 */
function createLocationFromSpan(span) {
  return {
    physicalLocation: {
      artifactLocation: {
        uri: span.file_name,
      },
      region: {
        byteOffset: span.byte_start,
        byteLength: span.byte_end - span.byte_start,
        startLine: span.line_start,
        startColumn: span.column_start,
        endLine: span.line_end,
        endColumn: span.column_end,
      },
    },
    message: span.label ? { text: span.label } : undefined,
  };
}

/**
 * Recursively builds a global message from diagnostic and children
 *
 * @param diagnostic The diagnostic object
 * @returns A string containing the global message
 */
function buildGlobalMessage(diagnostic) {
  let message = "";

  // If no spans, add the message (it's a global message)
  if (!diagnostic.spans || diagnostic.spans.length === 0) {
    message += diagnostic.message + "\n";
  }

  // Process children recursively
  if (diagnostic.children && diagnostic.children.length > 0) {
    for (const child of diagnostic.children) {
      message += buildGlobalMessage(child);
    }
  }

  return message;
}

/**
 * Extracts help URI from a diagnostic's children
 *
 * @param diagnostic The diagnostic object
 * @returns The help URI if found, otherwise undefined
 */
function findHelpUri(diagnostic) {
  if (!diagnostic.children) {
    return undefined;
  }

  for (const child of diagnostic.children) {
    if (child.level === "help") {
      // Match URI pattern using regex similar to Rust implementation
      const match = /^for further information visit (\S+)/.exec(child.message);
      if (match && match[1]) {
        return match[1];
      }
    }
  }

  return undefined;
}

/**
 * Collects related locations from a diagnostic's children
 *
 * @param diagnostic The diagnostic object
 * @returns An array of related locations
 */
function getRelatedLocations(diagnostic) {
  if (!diagnostic.children) {
    return [];
  }

  const relatedLocations = [];

  for (const child of diagnostic.children) {
    if (!child.spans || child.spans.length === 0) {
      continue;
    }

    for (const childSpan of child.spans) {
      let message = child.message;

      // Append suggested replacement to message if available
      if (childSpan.suggested_replacement) {
        message += ` "${childSpan.suggested_replacement}"`;
      }

      const location = createLocationFromSpan(childSpan);
      location.message = { text: message };

      relatedLocations.push(location);
    }
  }

  return relatedLocations;
}

/**
 * Sort fixes according to the logic in rustfix
 *   Ref: https://github.com/rust-lang/cargo/blob/master/crates/rustfix/src/replace.rs#L143-L150
 *
 * @param {Replacement[]} spans
 * @param {Buffer} fileContents
 * @return {Replacement[]}
 */
function sortReplacements(spans, fileContents) {
  /**
   * @type {Replacement[]}
   */
  const replacements = [];

  for (const span of spans) {
    const start = span.byte_start;
    const end = span.byte_end;

    console.assert(start <= end, `span ends before it starts: ${JSON.stringify(span)}`);
    console.assert(end <= fileContents.length, `span ends after file end: ${JSON.stringify(span)}`)

    /**
     * Re-implementation of Rust's partition point:
     * https://doc.rust-lang.org/std/primitive.slice.html#method.partition_point
     * @template ELEM
     * @param {ELEM[]} elems
     * @param {(ELEM) => bool} predicate
     * @return {number}
     */
    function partitionPoint(elems, predicate) {
      let idx = elems.findLastIndex(predicate);
      return idx + 1;
    }

    let insertionPoint = partitionPoint(replacements, (replacement) => {
      return (replacement.byte_start < start ||
          (replacement.byte_start === start && replacement.byte_end < end)
      )
    });

    // If we did not find a proper insertion point, insert at the end of the replacement queue.
    if (insertionPoint === -1) {
      insertionPoint = replacements.length;
    }

    // Reject if the change starts before the previous one ends.
    const previousReplacementIdx = insertionPoint - 1;
    if (previousReplacementIdx >= 0) {
      const previousReplacement = replacements[previousReplacementIdx];
      if (start < previousReplacement.byte_end) {
        continue
      }
    }

    // Reject if the change ends after the next one starts,
    // or if this is an insert and there's already an insert there.
    if (0 <= insertionPoint && insertionPoint < replacements.length) {
      const nextReplacement = replacements[insertionPoint];
      const areTheSameRange = start === nextReplacement.byte_start && end === nextReplacement.byte_end;
      if (end > nextReplacement.byte_start || areTheSameRange) {
        continue
      }
    }

    replacements.splice(insertionPoint, 0, span);
  }

  return replacements;
}

module.exports = {
  diagnosticsToHumanReadable,
  diagnosticsToSarif,
  applyDiagnosticsAsPatches,
};
