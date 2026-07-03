/// <reference types="vite/client" />

declare module '*.wasm?url&no-inline' {
  const url: string
  export default url
}

declare module '*.js?url&no-inline' {
  const url: string
  export default url
}
