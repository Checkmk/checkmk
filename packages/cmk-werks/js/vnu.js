'use strict'

const { execFile } = require('child_process')
const vnu = require('vnu-jar')

execFile(
  'java',
  ['-jar', `"${vnu}"`].concat(process.argv.slice(2)),
  { shell: true },
  (error, stdout) => {
    if (error) {
      console.error(`exec error: ${error}`)
      return
    }
    console.log(stdout)
  }
)
