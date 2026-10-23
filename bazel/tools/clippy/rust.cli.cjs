#!/usr/bin/env node

const fs = require("fs");
const {
  diagnosticsToSarif,
  applyDiagnosticsAsPatches,
  diagnosticsToHumanReadable,
} = require("./rust.diagnostic-formatter.cjs");

/**
 * @typedef {"human-readable" | "patch" | "sarif"} CliCommand
 *
 * @typedef CliOptions
 * @property {CliCommand} command - Command to run.
 * @property {string} inputFile - Path to the input file, relative to where the binary is being run.
 * @property {string | null} outputFile - Path to the input file, relative to where the binary is being run.
 */

/**
 * @param {CliCommand | null} command
 */
function printUsage(command) {
  switch (command) {
    case "human-readable":
      console.error(
          "Usage: node rust.cli.cjs human-readable <rustc-diagnostic-json-file> <output-file>"
      );
      break;
    case "sarif":
      console.error(
          "Usage: node rust.cli.cjs sarif <rustc-diagnostic-json-file> <output-file>"
      );
      break;
    case "patch":
      console.error(
          "Usage: node rust.cli.cjs patch <rustc-diagnostic-json-file>"
      );
      break;
    case null:
      console.error(
          "Usage: node rust.cli.cjs <command> [<arg>...]"
      );
      console.error('  command: "human-readable", "patch", or "sarif"');
      break;
  }
}

/**
 * @return {CliOptions}
 */
function parseOptions() {
  const argv = process.argv;

  if (argv.length < 4) {
    printUsage(null);
    process.exit(1);
  }

  const command = argv[2];

  // Validate command
  if (command !== "human-readable" && command !== "sarif" && command !== "patch") {
    console.error(
        'Error: unrecognized command'
    );
    printUsage(null);
    process.exit(1);
  }

  const inputFile = argv[3];

  if (!inputFile) {
    printUsage(command)
    process.exit(1);
  }

  let outputFile = null;
  if (shouldWriteOutput(command)) {
    if (argv.length < 5) {
      printUsage(command);
      process.exit(1);
    }
    outputFile = argv[4];
  }

  return {
    command,
    inputFile,
    outputFile,
  }
}

/**
 * Main function that processes command line arguments and executes the appropriate function
 */
function main() {
  const {
    command, inputFile, outputFile
  } = parseOptions();

  let diagnostics = [];
  try {
    // Read and parse the input file
    const fileContent = fs.readFileSync(inputFile, "utf8");

    diagnostics = fileContent
      .split("\n")
      .filter((line) => line.trim() !== "")
      .filter((line) => line.startsWith("{"))
      .map((line) => {
        try {
          return JSON.parse(line);
        } catch (err) {
          console.error(`Error parsing JSON line: ${line}`);
          console.error(err);
          throw err;
        }
      })
      .filter((item) => item !== null);
  } catch (err) {
    console.error(`Error gathering diagnostics files: ${err.message}`);
    process.exit(1);
  }

  // Process the diagnostics based on output type
  let outputContent;
  try {
    if (command === "human-readable") {
      outputContent = diagnosticsToHumanReadable(diagnostics);
    } else if (command === "patch") {
      outputContent = applyDiagnosticsAsPatches(diagnostics);
    } else {
      // outputType is 'sarif'
      const sarif = diagnosticsToSarif(diagnostics);
      outputContent = JSON.stringify(sarif, null, 2);
    }
  } catch (err) {
    console.error(`Error processing files: ${err.message}`);
    process.exit(1);
  }

  if (!shouldWriteOutput(command)) {
    console.log(`Command '${command}' requires no output. We're done!`)
    process.exit(0);
  }

  try {
    // Write the output
    fs.writeFileSync(outputFile, outputContent);
    console.log(`Successfully wrote output to ${outputFile}`);
  } catch (err) {
    console.error(`Error writing outputs: ${err.message}`);
    process.exit(1);
  }
}

/**
 * @param {CliCommand} command - The command that was passed to the cli.
 * @return {boolean} - True if the output should be written to disk.
 */
function shouldWriteOutput(command) {
  return command === "human-readable" || command === "sarif";
}

// Execute the main function
main();
