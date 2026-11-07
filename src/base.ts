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

export const UINT8_MAX = 255;
/** Keep accidental allocations bounded while allowing ordinary 4K imports. */
export const MAX_IMAGE_DIMENSION = 32_768;
export const MAX_IMAGE_PIXELS = 64_000_000;
const CHANNELS = 4;

/** Constrains a number to an inclusive interval. */
export function clamp(value: number, minimum: number, maximum: number): number {
  return Math.max(minimum, Math.min(maximum, value));
}

export function assertDimension(value: number, label: string): number {
  if (!Number.isSafeInteger(value) || value < 1 || value > MAX_IMAGE_DIMENSION) {
    throw new RangeError(`${label} must be an integer from 1 to ${MAX_IMAGE_DIMENSION}`);
  }
  return value;
}

export function assertPixelBuffer(image: PixelBuffer, label = "image"): void {
  if (!image || typeof image !== "object") {
    throw new TypeError(`${label} must be a PixelBuffer`);
  }
  assertDimension(image.width, `${label}.width`);
  assertDimension(image.height, `${label}.height`);
  const pixels = image.width * image.height;
  if (!Number.isSafeInteger(pixels) || pixels > MAX_IMAGE_PIXELS) {
    throw new RangeError(`${label} is too large; at most ${MAX_IMAGE_PIXELS} pixels are supported`);
  }
  if (!(image.data instanceof Uint8ClampedArray)) {
    throw new TypeError(`${label}.data must be a Uint8ClampedArray`);
  }
  const expectedLength = pixels * CHANNELS;
  if (image.data.length !== expectedLength) {
    throw new RangeError(`${label}.data must contain exactly ${expectedLength} bytes`);
  }
}
