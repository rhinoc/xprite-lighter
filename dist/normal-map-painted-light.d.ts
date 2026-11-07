import { type PixelBuffer } from "./base";
/** Signed luminance relative to the surrounding foreground, independent of the light angle. */
export declare function paintedLightSignal(width: number, height: number, foreground: Uint8Array, foregroundArea: number, luminance: Float32Array, shading?: PixelBuffer): Float32Array;
//# sourceMappingURL=normal-map-painted-light.d.ts.map