/** Pixel data shared by the generators. Kept free of editor types. */
export type Rgba = readonly [number, number, number, number];
export interface Point {
    x: number;
    y: number;
}
/** Straight-alpha RGBA pixels, row by row. */
export interface PixelBuffer {
    width: number;
    height: number;
    data: Uint8ClampedArray;
}
export declare const UINT8_MAX = 255;
/** Keep accidental allocations bounded while allowing ordinary 4K imports. */
export declare const MAX_IMAGE_DIMENSION = 32768;
export declare const MAX_IMAGE_PIXELS = 64000000;
/** Constrains a number to an inclusive interval. */
export declare function clamp(value: number, minimum: number, maximum: number): number;
export declare function assertDimension(value: number, label: string): number;
export declare function assertPixelBuffer(image: PixelBuffer, label?: string): void;
//# sourceMappingURL=base.d.ts.map