/**
 * Adapted from Pixel Art Lighter v3.5.22 by Red Hat Sprite, MIT.
 * Copyright (c) 2026 Red Hat Sprite. Full notice: LICENSES/pixel-art-lighter-MIT.txt.
 * https://www.moonfell-rpg.com/Pixel-Art-Lighter-v3.5.22.html
 */
import { type PixelBuffer } from "./base.js";
export declare const CONSTANT_LUMINANCE = 0.75;
export declare const LUMINANCE_EPSILON = 0.00001;
export declare enum LightingMapRegionMode {
    ExactRgb = "exact-rgb",
    Perceptual = "perceptual"
}
export declare function lightingMapLuminance(data: Uint8ClampedArray, at: number): number;
/** Partition foreground pixels into four-connected regions. */
export declare function segmentLightingMapSource(albedo: PixelBuffer, mode?: LightingMapRegionMode): {
    w: number;
    h: number;
    N: number;
    a: Uint8ClampedArray<ArrayBuffer>;
    fg: Uint8Array<ArrayBuffer>;
    lum: Float32Array<ArrayBuffer>;
    labels: Int32Array<ArrayBuffer>;
    lo: number;
    hi: number;
    adjacent: (i: number) => number[];
    queue: Int32Array<ArrayBuffer>;
    clusters: {
        pixels: number[];
        value: number;
    }[];
    foregroundArea: number;
};
//# sourceMappingURL=lighting-map-source.d.ts.map