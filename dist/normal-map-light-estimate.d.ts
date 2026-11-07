import { type PixelBuffer } from "./base.js";
/** Estimate an image-plane azimuth from contour shading. Null leaves the draft angle alone. */
export interface PaintedLightEstimate {
    angle: number;
    /** correlation fit in [0,1]; scale influence by this to fade weak signals */
    fit: number;
}
export declare function estimatePaintedLightAngle(source: PixelBuffer, shading?: PixelBuffer): number | null;
export declare function estimatePaintedLight(source: PixelBuffer, shading?: PixelBuffer): PaintedLightEstimate | null;
//# sourceMappingURL=normal-map-light-estimate.d.ts.map