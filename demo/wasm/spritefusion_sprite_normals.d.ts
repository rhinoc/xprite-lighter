/* tslint:disable */
/* eslint-disable */

export class NormalMapResult {
    private constructor();
    free(): void;
    [Symbol.dispose](): void;
    readonly color_png: Uint8Array;
    readonly metadata: string;
    readonly normal_png: Uint8Array;
}

/**
 * Generate PNG normal maps from PNG, GIF, or APNG bytes. Pass "{}" for default options.
 * Call `free()` on the result after copying its arrays and metadata.
 *
 * # Errors
 * Throws for invalid options, malformed images, and resource limits.
 */
export function generate_normal_map(bytes: Uint8Array, options_json: string): NormalMapResult;

export type InitInput = RequestInfo | URL | Response | BufferSource | WebAssembly.Module;

export interface InitOutput {
    readonly memory: WebAssembly.Memory;
    readonly __wbg_normalmapresult_free: (a: number, b: number) => void;
    readonly generate_normal_map: (a: number, b: number, c: number, d: number) => [number, number, number];
    readonly normalmapresult_color_png: (a: number) => [number, number];
    readonly normalmapresult_metadata: (a: number) => [number, number];
    readonly normalmapresult_normal_png: (a: number) => [number, number];
    readonly __wbindgen_externrefs: WebAssembly.Table;
    readonly __wbindgen_malloc: (a: number, b: number) => number;
    readonly __wbindgen_realloc: (a: number, b: number, c: number, d: number) => number;
    readonly __externref_table_dealloc: (a: number) => void;
    readonly __wbindgen_free: (a: number, b: number, c: number) => void;
    readonly __wbindgen_start: () => void;
}

export type SyncInitInput = BufferSource | WebAssembly.Module;

/**
 * Instantiates the given `module`, which can either be bytes or
 * a precompiled `WebAssembly.Module`.
 *
 * @param {{ module: SyncInitInput }} module - Passing `SyncInitInput` directly is deprecated.
 *
 * @returns {InitOutput}
 */
export function initSync(module: { module: SyncInitInput } | SyncInitInput): InitOutput;

/**
 * If `module_or_path` is {RequestInfo} or {URL}, makes a request and
 * for everything else, calls `WebAssembly.instantiate` directly.
 *
 * @param {{ module_or_path: InitInput | Promise<InitInput> }} module_or_path - Passing `InitInput` directly is deprecated.
 *
 * @returns {Promise<InitOutput>}
 */
export default function __wbg_init (module_or_path?: { module_or_path: InitInput | Promise<InitInput> } | InitInput | Promise<InitInput>): Promise<InitOutput>;
