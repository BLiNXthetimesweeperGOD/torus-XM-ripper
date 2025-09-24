import struct
from typing import List, Optional, Tuple

class XMNote:
    """
    One channel event in a row.
    - note: 1..96 (C-0=1 .. B-7=96), 97 = Key Off, 0 = empty
    - instrument: 1..128, 0 = empty
    - volume: 0..64 (or 0x10..0x50 FT2 volume column), 0 = empty
    - effect_type: 0..31, 0 = none
    - effect_param: 0..255, 0 = none
    """
    __slots__ = ("note", "instrument", "volume", "effect_type", "effect_param")

    def __init__(self, note=0, instrument=0, volume=0, effect_type=0, effect_param=0):
        self.note = note
        self.instrument = instrument
        self.volume = volume
        self.effect_type = effect_type
        self.effect_param = effect_param


class XMEnvelopePoint:
    """
    Envelope point: x in 0..65535 (frame), y in 0..64 (value)
    """
    __slots__ = ("x", "y")

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y


class XMSample:
    """
    PCM sample source. Provide signed PCM data:
    - If is_16bit=False: list of int8 values in [-128, 127]
    - If is_16bit=True: list of int16 values in [-32768, 32767]
    Looping uses (loop_type, loop_start, loop_length).
    """
    __slots__ = ("name", "pcm", "volume", "fine_tune", "panning",
                 "relative_note", "is_16bit", "loop_type", "loop_start", "loop_length")

    def __init__(
        self,
        name: str = "",
        pcm: List[int] = None,
        is_16bit: bool = False,
        volume: int = 64,
        fine_tune: int = 0,  # -16..+15
        panning: int = 128,  # 0..255
        relative_note: int = 0,  # semitone offset
        loop_type: int = 0,  # 0=none, 1=forward, 2=ping-pong
        loop_start: int = 0,
        loop_length: int = 0,
    ):
        self.name = name
        self.pcm = list(pcm or [])
        self.is_16bit = is_16bit
        self.volume = volume
        self.fine_tune = fine_tune
        self.panning = panning
        self.relative_note = relative_note
        self.loop_type = loop_type
        self.loop_start = loop_start
        self.loop_length = loop_length


class XMInstrument:
    """
    Instrument metadata + samples.
    - name: up to 22 ASCII chars
    - sample_for_note: length-96 list mapping MIDI-ish notes to sample index (0-based)
    - envelopes: volume and panning envelopes (optional)
    - envelope flags: on/sustain/loop via type bits (1=on, 2=sustain, 4=loop)
    """
    __slots__ = ("name", "samples", "sample_for_note",
                 "volume_points", "panning_points",
                 "num_volume_points", "num_panning_points",
                 "volume_sustain", "volume_loop_start", "volume_loop_end",
                 "panning_sustain", "panning_loop_start", "panning_loop_end",
                 "volume_type", "panning_type",
                 "vibrato_type", "vibrato_sweep", "vibrato_depth", "vibrato_rate",
                 "volume_fadeout")

    def __init__(self, name: str = ""):
        self.name = name
        self.samples: List[XMSample] = []

        # 96-note sample map
        self.sample_for_note: List[int] = [0] * 96

        # Envelopes
        self.volume_points: List[XMEnvelopePoint] = []
        self.panning_points: List[XMEnvelopePoint] = []
        self.num_volume_points = 0
        self.num_panning_points = 0
        self.volume_sustain = 0
        self.volume_loop_start = 0
        self.volume_loop_end = 0
        self.panning_sustain = 0
        self.panning_loop_start = 0
        self.panning_loop_end = 0
        self.volume_type = 0  # bits: 1 on, 2 sustain, 4 loop
        self.panning_type = 0  # bits: 1 on, 2 sustain, 4 loop

        # Vibrato
        self.vibrato_type = 0
        self.vibrato_sweep = 0
        self.vibrato_depth = 0
        self.vibrato_rate = 0

        # Fadeout
        self.volume_fadeout = 0  # u2


class XMPattern:
    def __init__(self, num_rows: int, num_channels: int):
        self.num_rows = num_rows
        self.rows: List[List[XMNote]] = [[XMNote() for _ in range(num_channels)] for _ in range(num_rows)]

class ExtendedModuleWriter:
    """
    XM 1.04 writer:
    - Preheader with signature, module name, tracker name, version 0x01.0x04, header_size
    - Header with song_length, restart_pos, num_channels, num_patterns, num_instruments, flags, tempo, bpm, order table (256 bytes)
    - Pattern headers + packed pattern data
    - Instrument headers + extra headers + sample headers + delta-encoded sample data
    """

    def __init__(
        self,
        name: str = "Untitled",
        tracker_name: str = "FastTracker 2 compatible",
        version_major: int = 0x01,
        version_minor: int = 0x04,
        num_channels: int = 4,
        default_tempo: int = 6,
        default_bpm: int = 125,
        linear_freq_table: bool = True,
    ):
        self.name = name
        self.tracker_name = tracker_name
        self.version_major = version_major
        self.version_minor = version_minor
        self.num_channels = num_channels
        self.default_tempo = default_tempo
        self.default_bpm = default_bpm
        self.linear_freq_table = linear_freq_table

        self.song_length = 1
        self.restart_position = 0
        self.order: List[int] = [0] * 256  # full 256-byte table; song_length controls meaningful entries
        self.patterns: List[XMPattern] = []
        self.instruments: List[XMInstrument] = []

    # ---- Public API ----

    def set_order(self, order: List[int]):
        if len(order) > 256:
            raise ValueError("Order length must be <= 256")
        self.song_length = len(order)
        self.order[:len(order)] = order
        if len(order) < 256:
            for i in range(len(order), 256):
                self.order[i] = 0

    def add_pattern(self, pattern: XMPattern):
        if pattern.num_rows < 1 or pattern.num_rows > 256:
            raise ValueError("Pattern rows must be in 1..256")
        if any(len(row) != self.num_channels for row in pattern.rows):
            raise ValueError("All pattern rows must have num_channels notes")
        self.patterns.append(pattern)

    def add_instrument(self, inst: XMInstrument):
        if len(inst.samples) > 128:
            raise ValueError("Max 128 samples per instrument in XM")
        self.instruments.append(inst)

    def save(self, filename: str):
        with open(filename, "wb") as f:
            f.write(self._pack_preheader_and_header())
            for pat in self.patterns:
                f.write(self._pack_pattern(pat))
            for inst in self.instruments:
                f.write(self._pack_instrument(inst))

    # ---- Internal packing ----

    def _pack_preheader_and_header(self) -> bytes:
        # Preheader
        out = bytearray()
        out += b"Extended Module: "
        out += self._pad_ascii(self.name, 20)
        out += b"\x1A"
        out += self._pad_ascii(self.tracker_name, 20)
        out += struct.pack("<BB", self.version_minor, self.version_major)

        # XM header is traditionally 276 bytes for v1.04
        header_size = 276

        out += struct.pack("<I", header_size)

        # Flags: bit 0 is linear table if set, else Amiga table
        flags = 1 if self.linear_freq_table else 0

        # Header block (16 bytes + 256-byte order table = 272 total)
        out += struct.pack(
            "<HHHHHHHH",
            self.song_length,
            self.restart_position,
            self.num_channels,
            len(self.patterns),
            len(self.instruments),
            flags,
            self.default_tempo,
            self.default_bpm,
        )
        # Order table (always 256 bytes)
        out += bytes(self.order)

        return bytes(out)

    def _pack_pattern(self, pat: XMPattern) -> bytes:
        """Pack pattern data into XM format - fixed version that preserves effects."""
        packed = bytearray()
        
        for r in range(pat.num_rows):
            for ch in range(self.num_channels):
                ev = pat.rows[r][ch]
                
                # Always write all 5 bytes, preserving exact values
                # Don't do conditional checks that might lose effect data
                packed.append(ev.note)
                packed.append(ev.instrument)
                packed.append(ev.volume)
                packed.append(ev.effect_type)
                packed.append(ev.effect_param)

        # Pattern header
        pattern_header_length = 9
        header_main = struct.pack(
            "<BHH",
            0,                # packing_type (always 0)
            pat.num_rows,     # number of rows
            len(packed),      # packed data size
        )
        pattern_header = struct.pack("<I", pattern_header_length) + header_main
        return pattern_header + packed

    def _pack_instrument(self, inst: XMInstrument) -> bytes:
        # Instrument header (excluding the leading header_size u4)
        hdr = bytearray()
        hdr += self._pad_ascii(inst.name, 22)
        hdr += struct.pack("<B", 0)  # type (usually zero)
        hdr += struct.pack("<H", len(inst.samples))

        # Extra header if there are samples
        extra = bytearray()
        if len(inst.samples) > 0:
            # len_sample_header is extended instrument sample header size: 0x000000 (FT2 uses 0x000000?)
            # In practice, we include all fields as per spec:
            # len_sample_header (u4) specifies size from here to end of extra header
            # Our layout below: 4 + 96 + (12*4)*2 + 12 bytes + 12 bytes + 12 bytes + 12 bytes + 2 + 2 = fixed
            # We'll compute dynamically.

            start_extra = len(extra)
            extra += struct.pack("<I", 0)  # placeholder for len_sample_header

            # 96-byte sample map
            extra += bytes(inst.sample_for_note[:96])

            # Envelope points (12 each; x u2, y u2)
            def write_env(points: List[XMEnvelopePoint], count_max=12):
                # write exactly 12 points; unused are zeros
                for i in range(count_max):
                    if i < len(points):
                        extra.extend(struct.pack("<HH", points[i].x, points[i].y))
                    else:
                        extra.extend(struct.pack("<HH", 0, 0))

            write_env(inst.volume_points)
            write_env(inst.panning_points)

            # Counts and positions
            num_vol = min(len(inst.volume_points), 12)
            num_pan = min(len(inst.panning_points), 12)
            extra += struct.pack("<B", num_vol)
            extra += struct.pack("<B", num_pan)
            extra += struct.pack("<B", inst.volume_sustain)
            extra += struct.pack("<B", inst.volume_loop_start)
            extra += struct.pack("<B", inst.volume_loop_end)
            extra += struct.pack("<B", inst.panning_sustain)
            extra += struct.pack("<B", inst.panning_loop_start)
            extra += struct.pack("<B", inst.panning_loop_end)

            # Types (bit flags: 1=on,2=sustain,4=loop)
            extra += struct.pack("<B", inst.volume_type)
            extra += struct.pack("<B", inst.panning_type)

            # Vibrato
            extra += struct.pack("<B", inst.vibrato_type)
            extra += struct.pack("<B", inst.vibrato_sweep)
            extra += struct.pack("<B", inst.vibrato_depth)
            extra += struct.pack("<B", inst.vibrato_rate)

            # Fadeout + reserved
            extra += struct.pack("<H", inst.volume_fadeout)
            extra += struct.pack("<H", 0)  # reserved

            # Now fill len_sample_header
            size = len(extra) - start_extra
            struct.pack_into("<I", extra, start_extra, size)

        # Full instrument block:
        # - header_size (u4) = size of this instrument block header (hdr + extra) + 4
        instrument_header_without_size = bytes(hdr + extra)
        header_size = len(instrument_header_without_size) + 4
        out = bytearray()
        out += struct.pack("<I", header_size)
        out += instrument_header_without_size

        # Sample headers
        for s in inst.samples:
            out += self._pack_sample_header(s)

        # Sample data (delta-coded)
        for s in inst.samples:
            out += self._pack_sample_data(s)

        return bytes(out)

    def _pack_sample_header(self, s: XMSample) -> bytes:
        sample_length = len(s.pcm)
        # loop flags and 16-bit flag reside in "type" bitfield:
        # bits: [reserved0:3][is_16_bit:1][reserved1:2][loop_type:2]
        loop_type_bits = s.loop_type & 0x03
        type_bits = (int(s.is_16bit) << 4) | loop_type_bits

        return struct.pack(
            "<IIIbB B B b B 22s",
            sample_length,
            s.loop_start,
            s.loop_length,
            s.volume,
            s.fine_tune,
            type_bits,
            s.panning,
            s.relative_note,
            0,  # reserved
            self._pad_ascii(s.name, 22),
        )

    def _pack_sample_data(self, s: XMSample) -> bytes:
        # Delta-encode signed PCM stream
        if s.is_16bit:
            # 16-bit signed words, little-endian
            prev = 0
            out = bytearray()
            for val in s.pcm:
                # delta-coded storage uses sample[i] = sample[i] + old; then old = sample[i]
                # For writing, we must store delta = current - prev, then accumulate on read.
                delta = (val - prev)
                # Pack as signed 16-bit little endian
                out += struct.pack("<h", delta)
                prev = val
            return bytes(out)
        else:
            # 8-bit signed bytes
            prev = 0
            out = bytearray()
            for val in s.pcm:
                delta = (val - prev)
                # clamp to int8
                delta = max(-128, min(delta, 127))
                out += struct.pack("<b", delta)
                prev = prev + delta  # Use the clamped delta to update prev
            return bytes(out)

    # ---- Helpers ----

    @staticmethod
    def _pad_ascii(s: str, size: int) -> bytes:
        b = (s or "").encode("ascii", errors="ignore")
        if len(b) > size:
            b = b[:size]
        return b.ljust(size, b"\x00")

#Example on how to use this
if __name__ == "__main__":
    # Create writer
    xm = ExtendedModuleWriter(
        name="Generic Test Name",
        tracker_name="Example Tracker",
        num_channels=4,
        default_tempo=6,
        default_bpm=125,
        linear_freq_table=True,
    )

    # Order: one pattern
    xm.set_order([0])

    # Pattern: 32 rows, 4 channels
    pat = XMPattern(num_rows=92, num_channels=xm.num_channels)

    # Put a simple C-4 on row 0, channel 0, instrument 1, volume 64
    # XM note numbers: C-4 is note 49 (C-0=1)
    for row in range(pat.num_rows):
        for channel in range(xm.num_channels):
            pat.rows[row][channel] = XMNote(note=0+(channel*12)+row, instrument=1, volume=64, effect_type=0, effect_param=0)
            pat.rows[row][channel] = XMNote(note=0+(channel*12)+row, instrument=1, volume=64, effect_type=12, effect_param=64)
            pat.rows[row][channel] = XMNote(note=0+(channel*12)+row, instrument=1, volume=64, effect_type=12, effect_param=64)
    xm.add_pattern(pat)

    # Instrument with one sample
    inst = XMInstrument(name="Sine")
    # Simple 8-bit sine-like waveform (signed)
    import math
    pcm8 = [int(60 * math.sin(2 * math.pi * t / 64)) for t in range(256)]
    sample = XMSample(
        name="Sine8",
        pcm=pcm8,
        is_16bit=False,
        volume=64,
        fine_tune=0,
        panning=128,
        relative_note=0,
        loop_type=1,       # forward loop
        loop_start=0,
        loop_length=len(pcm8),
    )
    inst.samples.append(sample)

    # Map all notes to sample 0
    inst.sample_for_note = [0] * 96

    # Simple volume envelope: on with 2 points (0->64)
    inst.volume_points = [XMEnvelopePoint(0, 64), XMEnvelopePoint(100, 64)]
    inst.num_volume_points = 2
    inst.volume_type = 1  # on

    xm.add_instrument(inst)

    xm.save("fixed_demo.xm")
