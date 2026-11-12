# =============================================================================
# URTC-GATEWAY - tests/test_image_header_copy.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The copy of the image header module that the update guard uses, held to its own rules: every refusal reason, the signed and the embedded forms and the switch."""
from __future__ import annotations

import random
import struct

import pytest

from urtc_gateway import image_header as ih

HARDWARE = 0x0303CC01
VERSION = (0, 4, 7, 2)
KEY = bytes(range(32))


def embedded_binary(length: int = 1024, version=VERSION) -> bytes:
    raw = bytearray(random.Random(7).randbytes(length))
    raw[ih.EMBED_OFFSET:ih.EMBED_OFFSET + 32] = ih.embedded_slot(HARDWARE, version)
    return bytes(raw)


def test_a_flat_header_round_trips_and_states_the_length_and_the_crc_of_its_payload():
    payload = bytes(range(200))
    image = ih.build_image(payload, HARDWARE, VERSION)
    status, info = ih.verify_image(image)
    assert status == ih.OK and info is not None
    assert (info.hardware_id, info.version, info.payload_length, info.signed, info.embedded) == (HARDWARE, VERSION, 200, False, False)
    assert info.version_text() == "0.4.7.2"
    assert ih.parse_header(image[:32])[0] == ih.OK


@pytest.mark.parametrize("cut, expected", [(31, ih.SHORT), (0, ih.SHORT)])
def test_a_header_shorter_than_32_bytes_is_short(cut, expected):
    assert ih.parse_header(ih.make_header(b"x", HARDWARE, VERSION)[:cut]) == (expected, None)


def test_each_field_of_the_header_that_is_wrong_gives_its_own_reason():
    good = bytearray(ih.make_header(b"payload", HARDWARE, VERSION))

    def broken(offset: int, value: int, fix_crc: bool = True) -> bytes:
        data = bytearray(good)
        data[offset] = value
        if fix_crc:
            import zlib
            data[28:32] = struct.pack(">I", zlib.crc32(bytes(data[:28])) & 0xFFFFFFFF)
        return bytes(data)

    assert ih.parse_header(broken(0, 0x00))[0] == ih.BAD_MAGIC
    assert ih.parse_header(broken(4, 2))[0] == ih.BAD_VERSION
    assert ih.parse_header(broken(5, 33))[0] == ih.BAD_SIZE
    assert ih.parse_header(broken(8, good[8] ^ 1, fix_crc=False))[0] == ih.BAD_HEADER_CRC
    assert ih.parse_header(bytes(good))[0] == ih.OK


def test_a_flat_image_with_the_wrong_length_or_a_changed_payload_is_refused():
    image = ih.build_image(b"0123456789", HARDWARE, VERSION)
    assert ih.verify_image(image + b"!")[0] == ih.BAD_LENGTH
    assert ih.verify_image(image[:-1])[0] == ih.BAD_LENGTH
    changed = bytearray(image)
    changed[-1] ^= 1
    assert ih.verify_image(bytes(changed))[0] == ih.BAD_PAYLOAD_CRC
    assert ih.verify_image(b"short")[0] == ih.SHORT


def test_a_signed_image_carries_a_trailer_that_covers_the_header_and_the_payload():
    payload = b"signed payload"
    image = ih.build_image(payload, HARDWARE, VERSION, key=KEY)
    status, info = ih.verify_image(image)
    assert status == ih.OK and info is not None and info.signed
    header = image[:32]
    assert image[-32:] == ih.sign(KEY, header, payload)
    assert ih.sign(bytes(32), header, payload) != image[-32:]
    assert ih.signed_region(header, payload) == header[:28] + payload
    assert ih.verify_image(image[:-1])[0] == ih.BAD_LENGTH           # the trailer is part of the length
    assert ih.sign(KEY, header, payload + b"!") != image[-32:]


def test_an_embedded_image_is_sealed_to_the_same_bytes_every_time_and_verifies():
    binary = embedded_binary()
    sealed = ih.seal_embedded(binary, HARDWARE, VERSION)
    assert sealed == ih.seal_embedded(binary, HARDWARE, VERSION)
    assert len(sealed) == len(binary) and sealed[:ih.EMBED_OFFSET] == binary[:ih.EMBED_OFFSET]
    assert sealed[ih.EMBED_OFFSET + 32:] == binary[ih.EMBED_OFFSET + 32:]
    status, info = ih.verify_embedded(sealed)
    assert status == ih.OK and info is not None and info.embedded and info.payload_length == len(binary)
    assert info.payload_crc32 == ih.embedded_crc(sealed)


def test_an_embedded_image_that_was_never_sealed_cannot_pass_for_a_sealed_one():
    binary = embedded_binary()
    assert ih.verify_embedded(binary) == (ih.NOT_SEALED, None)
    assert ih.verify_embedded(binary[:100]) == (ih.SHORT, None)


def test_sealing_refuses_a_binary_without_the_slot_another_board_and_another_version():
    with pytest.raises(ValueError, match="too short"):
        ih.seal_embedded(bytes(100))
    with pytest.raises(ValueError, match="no header slot"):
        ih.seal_embedded(bytes(1024))
    binary = embedded_binary()
    with pytest.raises(ValueError, match="hardware"):
        ih.seal_embedded(binary, HARDWARE ^ 0x100)
    with pytest.raises(ValueError, match="version"):
        ih.seal_embedded(binary, HARDWARE, (0, 4, 7, 3))
    signed_slot = bytearray(binary)
    signed_slot[ih.EMBED_OFFSET + 6:ih.EMBED_OFFSET + 8] = struct.pack(">H", ih.FLAG_EMBEDDED | ih.FLAG_SIGNED)
    with pytest.raises(ValueError, match="no header slot"):
        ih.seal_embedded(bytes(signed_slot))


def test_a_sealed_image_that_is_changed_anywhere_is_refused_with_a_reason():
    sealed = ih.seal_embedded(embedded_binary(), HARDWARE, VERSION)
    rng = random.Random(11)
    for _ in range(40):
        offset = rng.choice([i for i in range(len(sealed)) if not ih.EMBED_OFFSET <= i < ih.EMBED_OFFSET + 32])
        changed = bytearray(sealed)
        changed[offset] ^= 1 << rng.randrange(8)
        assert ih.verify_embedded(bytes(changed))[0] == ih.BAD_PAYLOAD_CRC
    assert ih.verify_embedded(sealed + b"\x00")[0] == ih.BAD_LENGTH
    flat_flags = bytearray(sealed)
    import zlib
    flat_flags[ih.EMBED_OFFSET + 6:ih.EMBED_OFFSET + 8] = struct.pack(">H", 0)
    flat_flags[ih.EMBED_OFFSET + 28:ih.EMBED_OFFSET + 32] = struct.pack(">I", zlib.crc32(bytes(flat_flags[ih.EMBED_OFFSET:ih.EMBED_OFFSET + 28])) & 0xFFFFFFFF)
    assert ih.verify_embedded(bytes(flat_flags))[0] == ih.BAD_FLAGS
    broken_crc = bytearray(sealed)
    broken_crc[ih.EMBED_OFFSET + 31] ^= 1
    assert ih.verify_embedded(bytes(broken_crc))[0] == ih.BAD_HEADER_CRC


@pytest.mark.parametrize("value, expected", [(None, ih.POLICY_WARN), ("", ih.POLICY_WARN), ("  ", ih.POLICY_WARN), ("ACCEPT", ih.POLICY_ACCEPT), (" warn ", ih.POLICY_WARN),
                                              ("require", ih.POLICY_REQUIRE), ("nonsense", ih.POLICY_REQUIRE), (0, ih.POLICY_REQUIRE)])
def test_the_switch_reads_a_known_word_and_an_unknown_value_is_the_strictest(value, expected):
    assert ih.parse_policy(value) == expected


def test_a_file_is_classified_and_the_switch_decides_about_an_image_without_a_header():
    legacy = bytes(range(256)) * 8
    assert ih.inspect_image(legacy, ih.POLICY_ACCEPT) == ih.ImageCheck(True, ih.KIND_LEGACY, ih.REASON_OK)
    warned = ih.inspect_image(legacy, ih.POLICY_WARN)
    assert warned.accepted and warned.warn and warned.reason == ih.REASON_NO_HEADER
    required = ih.inspect_image(legacy, ih.POLICY_REQUIRE)
    assert not required.accepted and required.reason == ih.REASON_REQUIRED
    assert not ih.inspect_image(legacy, "nonsense").accepted


def test_a_stamped_file_is_never_flashed_and_a_header_that_is_there_is_always_checked():
    stamped = ih.build_image(b"payload", HARDWARE, VERSION)
    assert ih.inspect_image(stamped, ih.POLICY_ACCEPT) == ih.ImageCheck(False, ih.KIND_STAMPED_FILE, ih.REASON_STAMPED)
    sealed = ih.seal_embedded(embedded_binary(), HARDWARE, VERSION)
    ok = ih.inspect_image(sealed, ih.POLICY_ACCEPT, HARDWARE, (0, 4, 7))
    assert ok.accepted and ok.kind == ih.KIND_EMBEDDED and ok.reason == ih.REASON_OK and ok.info is not None and not ok.warn
    assert ih.inspect_image(sealed, ih.POLICY_ACCEPT, HARDWARE ^ 1).reason == ih.REASON_HARDWARE
    assert ih.inspect_image(sealed, ih.POLICY_ACCEPT, HARDWARE, (0, 4, 8)).reason == ih.REASON_VERSION
    changed = bytearray(sealed)
    changed[5] ^= 1
    for policy in ih.POLICIES:
        refused = ih.inspect_image(bytes(changed), policy)
        assert not refused.accepted and refused.reason == "header_bad_payload_crc"
    unsealed = ih.inspect_image(embedded_binary(), ih.POLICY_ACCEPT)
    assert not unsealed.accepted and unsealed.reason == "header_not_sealed"
