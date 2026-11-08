import { type PixelBuffer, type Point, type Rgba } from "./base.js";
export interface NormalMapLightOptions {
    position: Point;
    height: number;
    brightness: number;
    ambient: number;
    maskStrength: number;
    color: Rgba;
    invertY: boolean;
    /**
     * Divide out a directional light already painted into the sprite before shading.
     * `angle` is the image-plane azimuth in degrees (0 = right, 90 = up), as returned by
     * `estimatePaintedLight`; `influence` 0–100 blends from no correction to full division.
     */
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
/** Lambert point lighting in linear color; normal channels are raw vector data. */
export declare function renderPreparedNormalMapLighting(source: PreparedNormalMapLighting, options: NormalMapLightOptions): PixelBuffer;
/** Return the sprite with a painted directional light divided out, as flat-lit albedo. */
export declare function removePaintedLight(source: PreparedNormalMapLighting, delight: NonNullable<NormalMapLightOptions["delight"]>, invertY?: boolean): PixelBuffer;
export declare function renderNormalMapLighting(albedo: PixelBuffer, normals: PixelBuffer | null, options: NormalMapLightOptions, lightMask?: PixelBuffer | null): PixelBuffer;
//# sourceMappingURL=normal-map-lighting.d.ts.map