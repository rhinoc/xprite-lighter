"""Write native full-frame RGBA cels, with named layers and per-frame timing."""
import struct
import zlib


def chunk(kind, payload):
    return struct.pack("<IH", 6 + len(payload), kind) + payload


def write_ase(path, layers, frames, durations=None):
    width, height = frames[0][0].size
    body = bytearray()
    if durations is None: durations = [125] * len(frames)
    for i, images in enumerate(frames):
        duration=durations[i]
        chunks = []
        if i == 0:
            for title, visible in layers:
                name = title.encode("utf-8")
                flags = 2 + int(visible)  # every layer editable
                layer = struct.pack("<6HB3xH", flags, 0, 0, 0, 0, 0, 255, len(name)) + name
                chunks.append(chunk(0x2004, layer))
        if len(images) != len(layers):
            raise ValueError("frame layer count differs")
        for layer_index, image in enumerate(images):
            if image.size != (width, height) or image.mode != "RGBA":
                raise ValueError("this writer expects full-canvas RGBA cels")
            header = struct.pack("<HhhBHh5xHH", layer_index, 0, 0, 255, 2, 0, width, height)
            chunks.append(chunk(0x2005, header + zlib.compress(image.tobytes(), 9)))
        contents = b"".join(chunks)
        body.extend(struct.pack("<IHHH2xI", 16 + len(contents), 0xF1FA, len(chunks), duration, len(chunks)))
        body.extend(contents)
    header = bytearray(128)
    struct.pack_into("<I5HIH", header, 0, 128 + len(body), 0xA5E0, len(frames), width, height, 32, 1, durations[0])
    struct.pack_into("<BBhhHH", header, 34, 1, 1, 0, 0, 16, 16)
    path.write_bytes(header + body)


