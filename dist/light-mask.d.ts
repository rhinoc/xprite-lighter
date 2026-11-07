/**
 * Adapted from Pixel Art Lighter v3.5.22 by Red Hat Sprite, MIT.
 * Copyright (c) 2026 Red Hat Sprite. Full notice: LICENSES/pixel-art-lighter-MIT.txt.
 * https://www.moonfell-rpg.com/Pixel-Art-Lighter-v3.5.22.html
 */
import { type PixelBuffer } from "./base";
export declare const DEFAULT_LIGHT_MASK_LAYER_NAME = "Light Mask";
export interface LightMaskOptions {
    strength: number;
    floor: number;
    ceiling: number;
    cavity: number;
}
export declare const LIGHT_MASK_LIMITS: Readonly<{
    strength: 100;
    floor: 255;
    ceiling: 255;
    cavity: 100;
}>;
export declare function defaultLightMaskOptions(): LightMaskOptions;
export declare function createLightMaskGenerator(albedo: PixelBuffer): {
    generate(input?: Partial<LightMaskOptions>): PixelBuffer;
};
//# sourceMappingURL=light-mask.d.ts.map