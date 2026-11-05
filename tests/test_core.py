import unittest

from fssutf_unicode_predicate_utils import (
    FSSUTFError,
    is_fssutf,
    is_fssutf_string,
)


class ScalarValueTests(unittest.TestCase):
    def test_ascii_range_is_valid(self):
        for value in (0x00, 0x41, 0x7F):
            with self.subTest(value=value):
                self.assertTrue(is_fssutf(value))

    def test_boundaries_are_valid(self):
        for value in (0x80, 0x7FF, 0x800, 0xFFFF, 0x10000, 0x10FFFF):
            with self.subTest(value=value):
                self.assertTrue(is_fssutf(value))

    def test_negative_and_too_large_are_invalid(self):
        for value in (-1, -0x80000000, 0x110000, 0x7FFFFFFF):
            with self.subTest(value=value):
                self.assertFalse(is_fssutf(value))

    def test_surrogates_are_invalid(self):
        for value in (0xD800, 0xDBFF, 0xDC00, 0xDFFF):
            with self.subTest(value=value):
                self.assertFalse(is_fssutf(value))

    def test_just_outside_surrogates_is_valid(self):
        self.assertTrue(is_fssutf(0xD7FF))
        self.assertTrue(is_fssutf(0xE000))

    def test_bool_is_rejected(self):
        with self.assertRaises(TypeError):
            is_fssutf(True)
        with self.assertRaises(TypeError):
            is_fssutf(False)

    def test_other_types_are_rejected(self):
        for value in (None, 1.0, b"a", [0x41]):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    is_fssutf(value)


class ByteSequenceTests(unittest.TestCase):
    def test_empty_sequence_is_valid(self):
        self.assertTrue(is_fssutf_string(b""))
        self.assertTrue(is_fssutf_string(bytearray()))
        self.assertTrue(is_fssutf_string(""))

    def test_pure_ascii_is_valid(self):
        self.assertTrue(is_fssutf_string(b"hello, world"))
        self.assertTrue(is_fssutf_string("hello, world"))

    def test_known_good_multibyte_sequences(self):
        # U+00A9 (2 bytes), U+20AC (3 bytes), U+1F600 (4 bytes).
        cases = [
            b"\xc2\xa9",
            b"\xe2\x82\xac",
            b"\xf0\x9f\x98\x80",
            "\xc2\xa9",
            "\xe2\x82\xac",
            "\xf0\x9f\x98\x80",
        ]
        for data in cases:
            with self.subTest(data=data):
                self.assertTrue(is_fssutf_string(data))

    def test_truncated_sequences_are_invalid(self):
        cases = [
            b"\xc2",
            b"\xe2\x82",
            b"\xf0\x9f\x98",
            b"\xc2\x41",
            b"\xe2\x82\x41",
            b"\xf0\x9f\x98\x41",
        ]
        for data in cases:
            with self.subTest(data=data):
                self.assertFalse(is_fssutf_string(data))

    def test_continuation_byte_alone_is_invalid(self):
        self.assertFalse(is_fssutf_string(b"\x80"))
        self.assertFalse(is_fssutf_string(b"\xbf"))

    def test_invalid_lead_bytes_are_rejected(self):
        for byte in (0xC0, 0xC1, 0xF5, 0xF6, 0xF7, 0xF8, 0xFF):
            with self.subTest(byte=byte):
                self.assertFalse(is_fssutf_string(bytes([byte, 0x80, 0x80, 0x80])))

    def test_overlong_encodings_are_rejected(self):
        # Overlong two-byte forms of ASCII (must be rejected by the C2 lower
        # bound).
        self.assertFalse(is_fssutf_string(b"\xc0\xaf"))
        self.assertFalse(is_fssutf_string(b"\xc1\xbf"))
        # Overlong three-byte form of U+0080 (E0 requires second byte >= A0).
        self.assertFalse(is_fssutf_string(b"\xe0\x80\x80"))
        self.assertFalse(is_fssutf_string(b"\xe0\x9f\xbf"))
        # Overlong four-byte form of U+FFFF (F0 requires second byte >= 90).
        self.assertFalse(is_fssutf_string(b"\xf0\x80\x80\x80"))
        self.assertFalse(is_fssutf_string(b"\xf0\x8f\xbf\xbf"))

    def test_surrogate_encodings_are_rejected(self):
        # U+D800 and U+DFFF encoded as three bytes.
        self.assertFalse(is_fssutf_string(b"\xed\xa0\x80"))
        self.assertFalse(is_fssutf_string(b"\xed\xbf\xbf"))

    def test_above_unicode_max_is_rejected(self):
        # U+110000 and above require F4 with second byte > 8F, or F5..
        self.assertFalse(is_fssutf_string(b"\xf4\x90\x80\x80"))
        self.assertFalse(is_fssutf_string(b"\xf4\xbf\xbf\xbf"))

    def test_high_value_boundary_is_accepted(self):
        # U+10FFFF is the maximum scalar value.
        self.assertTrue(is_fssutf_string(b"\xf4\x8f\xbf\xbf"))

    def test_bytearray_is_accepted(self):
        self.assertTrue(is_fssutf_string(bytearray(b"\xc2\xa9")))
        self.assertFalse(is_fssutf_string(bytearray(b"\xc2")))

    def test_str_with_non_latin1_char_is_invalid(self):
        # A Python str is treated as byte ordinals; U+20AC cannot be a byte.
        self.assertFalse(is_fssutf_string("\u20ac"))

    def test_wrong_type_raises(self):
        for value in (None, 5, [0x41], {b"a": 1}):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    is_fssutf_string(value)


class StrByteOrdinalTests(unittest.TestCase):
    def test_str_is_interpreted_as_byte_ordinals(self):
        # The two-character string "\xc2\xa9" is two byte ordinals, not the
        # decoded character U+00A9, and it is a valid FSS-UTF encoding.
        self.assertTrue(is_fssutf("\xc2\xa9"))
        self.assertFalse(is_fssutf("\xc2"))

    def test_str_with_high_char_is_invalid(self):
        self.assertFalse(is_fssutf("\u20ac"))


class ErrorTests(unittest.TestCase):
    def test_error_is_a_value_error(self):
        err = FSSUTFError("bad", 3)
        self.assertIsInstance(err, ValueError)
        self.assertEqual(err.offset, 3)
        self.assertIn("byte offset 3", str(err))


if __name__ == "__main__":
    unittest.main()
