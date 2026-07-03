export type ConfigMeta = {
  modelFilename: string
  bufferSize: number
  sampleRate: number
}

function calcMean(v: number[]): number {
  return v.reduce((a, b) => a + b, 0) / v.length
}

function calcMin(v: number[]): number {
  return Math.min(...v)
}

function calcMax(v: number[]): number {
  return Math.max(...v)
}

function calcPercentile(v: number[], p: number): number {
  const sorted = [...v].sort((a, b) => a - b)
  return sorted[Math.floor(p * (sorted.length - 1))]
}

export function logConfigHeader(
  config: ConfigMeta,
  label: string,
  numIter: number,
  numReps: number
): string {
  const bsMs = (config.bufferSize * 1000) / config.sampleRate
  return [
    '',
    '----------------------------------------------------------------------------------------------------------------------------------------',
    `Model: ${config.modelFilename} | Run: ${label} | Host Sample Rate: ${config.sampleRate} Hz | Host Buffer Size: ${config.bufferSize} = ${bsMs.toFixed(4)} ms`,
    '----------------------------------------------------------------------------------------------------------------------------------------',
    '',
    `Benchmark: ${numReps} repetitions x ${numIter} iterations`,
    '',
  ].join('\n')
}

export function logSingleRep(
  config: ConfigMeta,
  label: string,
  repIdx: number,
  numReps: number,
  times: number[]
): string {
  const lines: string[] = []
  for (let i = 0; i < times.length; i++) {
    lines.push(
      `ProcessBlock/${config.modelFilename}/${label}/${config.bufferSize}/iteration:${i}/repetition:${repIdx + 1}\t\t\t${times[i].toFixed(4)} ms`
    )
  }
  lines.push(
    `  Repetition ${repIdx + 1}/${numReps}: mean=${calcMean(times).toFixed(4)} ms`
  )
  lines.push('')
  return lines.join('\n')
}

export function logAggregate(
  config: ConfigMeta,
  label: string,
  allTimes: number[]
): string {
  return [
    '',
    `Aggregate (${allTimes.length} total iterations):`,
    `  ProcessBlock/${config.modelFilename}/${label}: mean=${calcMean(allTimes).toFixed(4)} ms, min=${calcMin(allTimes).toFixed(4)} ms, max=${calcMax(allTimes).toFixed(4)} ms, p99.9=${calcPercentile(allTimes, 0.999).toFixed(4)} ms`,
    '',
    '----------------------------------------------------------------------------------------------------------------------------------------',
  ].join('\n')
}
