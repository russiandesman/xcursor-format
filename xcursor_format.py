from dataclasses import dataclass, astuple
import struct

class XCursorBase:
    @classmethod
    def raw_unpack(cls, data: bytes, offset: int, fmt: str):
        required_size = struct.calcsize(fmt)
        available_size = len(data) - offset
        if available_size < required_size:
            raise ValueError(f"Processing {cls.__name__}; required {required_size} bytes, only {available_size} available")
        fields = struct.unpack_from(fmt, data, offset)
        return fields, offset + required_size

    @classmethod
    def unpack(cls, data: bytes, offset: int, fmt: str | None = None):
        if fmt is None:
            fmt = cls.FMT
        fields, new_offset = cls.raw_unpack(data, offset, fmt)
        return cls(*fields), new_offset

    def serialize(self):
        return struct.pack(self.FMT, *astuple(self))


@dataclass
class XCursorHdr(XCursorBase):
    EXPECTED_MAGIC = 0x72756358  # "Xcur"
    FMT = "<IIII"
    magic: int
    size: int
    version: int
    toc_count: int

    @classmethod
    def unpack(cls, data: bytes, offset: int):
        instance, new_offset = super().unpack(data, offset)
        if instance.magic != cls.EXPECTED_MAGIC:
            raise ValueError(f"Invalid magic number: {instance.magic:#x}, expected {cls.EXPECTED_MAGIC:#x}")
        return instance, new_offset

    def __repr__(self):
        return f"[magic={self.magic:#x}, sz={self.size}, ver={self.version:#x}, toc_sz={self.toc_count}]"


@dataclass
class XCursorTocEntry(XCursorBase):
    FMT = "<III"
    type: int
    subtype: int
    position: int

    def __repr__(self):
        return f"[type={self.type:#x}, sub={self.subtype:#x}, filepos={self.position}]"


@dataclass
class XCursorChunkHdr(XCursorBase):
    COMMENT = 0xfffd0001
    IMAGE = 0xfffd0002
    FMT = "<IIII"
    chunk_len: int
    type: int
    subtype: int
    version: int

    def __repr__(self):
        return f"[len={self.chunk_len}, type={self.type:#x}, sub={self.subtype:#x}, ver={self.version:#x}]"


@dataclass
class XCursorChunkComment(XCursorBase):
    FMT = "<I"
    str_len: int
    string: str

    @classmethod
    def unpack(cls, data: bytes, offset: int):
        instance, new_offset = super().unpack(data, offset)
        string_bytes, new_offset = cls.raw_unpack(data, new_offset, f"{instance.str_len}s")
        instance.string = string_bytes.decode('utf-8')
        return instance, new_offset

    def __repr__(self):
        return f"[len={self.str_len}, s='{self.string}']"

    def serialize(self):
        return struct.pack(self.FMT + f"{self.str_len}s", self.str_len, self.string.encode('utf-8'))


@dataclass
class XCursorChunkImage(XCursorBase):
    FMT = "<IIIII" # followed by "157I" for 157 pixels image 
    width: int
    height: int
    xhot: int
    yhot: int
    delay: int
    pixels: tuple[int, ...] = ()

    @classmethod
    def unpack(cls, data: bytes, offset: int):
        instance, new_offset = super().unpack(data, offset)
        instance.pixels, new_offset = cls.raw_unpack(data, new_offset, f"{instance.width * instance.height}I")
        return instance, new_offset

    def __repr__(self):
        return f"[{self.width}x{self.height} with {self.xhot}x{self.yhot}, delay={self.delay}, {len(self.pixels)} pixels]"

    def serialize(self):
        return struct.pack(self.FMT + f"{self.width * self.height}I", *(astuple(self)[:-1] + self.pixels))


@dataclass
class XCursorChunk:
    header: XCursorChunkHdr
    body: XCursorChunkComment | XCursorChunkImage

    @classmethod
    def unpack(cls, data: bytes, offset: int):
        header, body_offset = XCursorChunkHdr.unpack(data, offset)
        if header.type == XCursorChunkHdr.COMMENT:
            body, _ = XCursorChunkComment.unpack(data, body_offset)
        elif header.type == XCursorChunkHdr.IMAGE:
            body, _ = XCursorChunkImage.unpack(data, body_offset)
        else:
            raise ValueError(f"Unknown chunk type: {header.type:#x}")

        return cls(header, body)

    def __repr__(self):
        return f"[{self.header}, {self.body}]"

    def serialize(self):
        return self.header.serialize() + self.body.serialize()


class XCursor:
    def __init__(self, data: bytes):
        self.toc = []
        self.chunks = []
        self.hdr, offset = XCursorHdr.unpack(data, 0)
        for i in range(self.hdr.toc_count):
            toc_item, offset = XCursorTocEntry.unpack(data, offset)
            self.toc.append(toc_item)
            chunk = XCursorChunk.unpack(data, toc_item.position)
            self.chunks.append(chunk)

    def serialize(self):
        result = self.hdr.serialize()
        for toc_item in self.toc:
            result += toc_item.serialize()
        for chunk in self.chunks:
            result += chunk.serialize()
        return result

    @property
    def images(self):
        for chunk in self.chunks:
            if isinstance(chunk.body, XCursorChunkImage):
                yield chunk

    @property
    def largest_image(self):
        return max(self.images, key=lambda chunk: chunk.body.width)

    def flip(self):
        def flip_horizontal(pixels: tuple[int, ...], width: int):
            for i in range(0, len(pixels), width):
                yield from reversed(pixels[i:i+width])
        for chunk in self.images:
            chunk.body.pixels = tuple(flip_horizontal(chunk.body.pixels, chunk.body.width))
            chunk.body.xhot = chunk.body.width - 1 - chunk.body.xhot


