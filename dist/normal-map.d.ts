/**
 * Adapted from Pixel Art Lighter v3.5.22 by Red Hat Sprite, MIT.
 * Copyright (c) 2026 Red Hat Sprite. Full notice: LICENSES/pixel-art-lighter-MIT.txt.
 * https://www.moonfell-rpg.com/Pixel-Art-Lighter-v3.5.22.html
 */
import { type PixelBuffer } from "./base";
export declare enum NormalMapPreset {
    Architecture = "architecture",
    Character = "character",
    Object = "object",
    Terrain = "terrain"
}
export interface NormalMapOptions {
    preset: NormalMapPreset;
    shapeStrength: number;
    normalStrength: number;
    smoothing: number;
    facets: number;
    mergeOutlines: boolean;
    invertY: boolean;
    paintedLightAngle: number;
    paintedLightInfluence: number;
}
export declare const NORMAL_MAP_LIMITS: Readonly<{
    shapeStrength: 200;
    normalStrength: 300;
    smoothing: 6;
    facets: 100;
    paintedLightAngle: number;
    paintedLightInfluence: 100;
}>;
export declare function defaultNormalMapOptions(preset?: NormalMapPreset): NormalMapOptions;
export declare function normalizeNormalMapOptions(input: Partial<NormalMapOptions>): NormalMapOptions;
/** Cache source segmentation, silhouette distance and geometry between parameter edits. */
export declare function createNormalMapGenerator(albedo: PixelBuffer, shading?: PixelBuffer): {
    setShading(source: PixelBuffer | null): void;
    suggestPaintedLightAngle(): number | null;
    generate(input?: Partial<NormalMapOptions>): PixelBuffer;
};
export declare function generateNormalMap(albedo: PixelBuffer, input?: Partial<NormalMapOptions>): PixelBuffer;
//# sourceMappingURL=normal-map.d.ts.map