import { type PixelBuffer, type Point, type Rgba } from "./base.js";
export interface NormalMapLightOptions {
    position: Point;
    height: number;
    brightness: number;
    ambient: number;
    maskStrength: number;
    color: Rgba;
    invertY: boolean;
    /** Remove a previously painted directional light before shading. */
    delight?: {
        angle: number;
        influence: number;
    };
}
export declare const NORMAL_LIGHT_LIMITS: Readonly<{
    height: 600;
    brightness: 500;
    ambient: 100;
    maskStrength: 100;
}>;
export declare function defaultNormalMapLightOptions(width: number, height: number): NormalMapLightOptions;
export interface PreparedNormalMapLighting {
    readonly width: number;
    readonly height: number;
    readonly colors: Float32Array;
    readonly directions: Float32Array;
    readonly alpha: Uint8Array;
    readonly mask: Float32Array | null;
}
/** Decode invariant color and vector data once for repeated light positions. */
export declare function prepareNormalMapLighting(albedo: PixelBuffer, normals: PixelBuffer | null, lightMask?: PixelBuffer | null): PreparedNormalMapLighting;
export declare function renderPreparedNormalMapLighting(source: PreparedNormalMapLighting, options: NormalMapLightOptions): PixelBuffer;
export declare function renderNormalMapLighting(albedo: PixelBuffer, normals: PixelBuffer | null, options: NormalMapLightOptions, lightMask?: PixelBuffer | null): PixelBuffer;
//# sourceMappingURL=normal-map-lighting.d.ts.map