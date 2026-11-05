"""Unicode FSS-UTF (UTF-8) predicate utilities.

FSS-UTF is the encoding scheme described in the original UTF-8 proposal
(ISO/IEC 10646-1:1993, Annex N, also known as the FSS-UTF proposal). It is
the same byte-level scheme that later became UTF-8, with the same well-formed
byte-sequence rules and the same scalar-value range (U+0000..U+10FFFF minus
the surrogate block U+D800..U+DFFF).

The predicate here answers one question: given a sequence of bytes, is it a
well-formed FSS-UTF encoding of a Unicode string? We deliberately do not
decode to a Python ``str``; a predicate that only inspects bytes keeps the
implementation free of any particular Unicode database and makes the
edge cases (overlongs, surrogates, truncation) explicit.
"""

from __future__ import annotations

from typing import Union

__all__ = ["FSSUTFError", "is_fssutf", "is_fssutf_string"]


class FSSUTFError(ValueError):
    """Raised when a string is not well-formed FSS-UTF.

    A distinct subclass (rather than plain ``ValueError``) lets callers
    distinguish FSS-UTF failures from other value errors while still catching
    the standard exception type. The message includes the byte offset of the
    first offending byte so callers can point at the problem.
    """

    def __init__(self, message: str, offset: int) -> None:
        super().__init__(f"{message} at byte offset {offset}")
        self.offset = offset


def is_fssutf(value: Union[int, str]) -> bool:
    """Return ``True`` if *value* is a well-formed FSS-UTF scalar value.

    For an :class:`int`, the value must be in the Unicode scalar range:
    ``0 <= value <= 0x10FFFF`` and not in the surrogate block
    ``0xD800..0xDFFF``. This is the property that a single decoded code point
    must satisfy; it is also the property that every byte of a multi-byte
    FSS-UTF sequence ultimately encodes.

    For a :class:`str`, the argument is interpreted as a sequence of bytes
    (each character's ordinal is treated as one byte). This matches the way
    the reference FSS-UTF description talks about byte sequences and avoids
    the ambiguity of whether a Python ``str`` is already decoded. Passing a
    string that is not a valid byte sequence is therefore a normal ``False``,
    not an error. To validate a decoded Python string, encode it to bytes
    first (``s.encode('utf-8')``) and pass the result here.

    Any other type raises :class:`TypeError`.
    """
    if isinstance(value, bool):
        # bool is a subclass of int; reject it explicitly so True/False do not
        # silently pass as 1/0. A predicate about Unicode scalars should not
        # accept booleans.
        raise TypeError("is_fssutf() does not accept bool")
    if isinstance(value, int):
        return _is_scalar_value(value)
    if isinstance(value, str):
        try:
            data = value.encode("latin-1")
        except UnicodeEncodeError:
            return False
        return _is_well_formed_bytes(data)
    raise TypeError(
        "is_fssutf() expects an int scalar value or a str of byte ordinals, "
        f"got {type(value).__name__}"
    )


def is_fssutf_string(value: Union[bytes, bytearray, str]) -> bool:
    """Return ``True`` if *value* is a well-formed FSS-UTF byte sequence.

    ``bytes`` and ``bytearray`` are checked directly. A :class:`str` is
    interpreted as a sequence of byte ordinals (same convention as
    :func:`is_fssutf`); a string containing a character above U+00FF cannot
    be a byte sequence and therefore returns ``False`` rather than raising.

    The empty sequence is well-formed: it encodes the empty string.
    """
    if isinstance(value, str):
        try:
            data = value.encode("latin-1")
        except UnicodeEncodeError:
            return False
        return _is_well_formed_bytes(data)
    if isinstance(value, (bytes, bytearray)):
        return _is_well_formed_bytes(bytes(value))
    raise TypeError(
        "is_fssutf_string() expects bytes, bytearray, or str, "
        f"got {type(value).__name__}"
    )


def _is_scalar_value(value: int) -> bool:
    """True when *value* is a Unicode scalar value (not a surrogate)."""
    if value < 0 or value > 0x10FFFF:
        return False
    if 0xD800 <= value <= 0xDFFF:
        return False
    return True


def _is_well_formed_bytes(data: bytes) -> bool:
    """Validate *data* as FSS-UTF, byte by byte.

    The rules implemented here are the classic FSS-UTF ones:

    * 1-byte: ``0x00``..``0x7F``
    * 2-byte: ``0xC2``..``0xDF`` followed by one continuation byte
    * 3-byte: ``0xE0``..``0xEF`` followed by two continuation bytes, with
      the bounds that forbid overlong encodings (``E0`` requires a second
      byte >= ``0xA0``) and surrogates (``ED`` requires a second byte
      <= ``0x9F``)
    * 4-byte: ``0xF0``..``0xF4`` followed by three continuation bytes, with
      the bounds that forbid overlongs (``F0`` requires second byte >= 0x90)
      and values above U+10FFFF (``F4`` requires second byte <= 0x8F)

    Continuation bytes are ``0x80``..``0xBF``. Bytes ``0xC0``, ``0xC1`` and
    ``0xF5``..``0xFF`` are never valid in a well-formed sequence.

    The implementation walks the bytes once, so it is O(n) and allocates
    nothing beyond the input.
    """
    i = 0
    n = len(data)
    while i < n:
        b0 = data[i]
        if b0 <= 0x7F:
            i += 1
        elif 0xC2 <= b0 <= 0xDF:
            if i + 1 >= n or not _is_continuation(data[i + 1]):
                return False
            i += 2
        elif 0xE0 <= b0 <= 0xEF:
            if i + 2 >= n:
                return False
            b1 = data[i + 1]
            b2 = data[i + 2]
            if not _is_continuation(b1) or not _is_continuation(b2):
                return False
            if b0 == 0xE0 and b1 < 0xA0:
                return False  # overlong: encodes U+0000..U+07FF in 3 bytes
            if b0 == 0xED and b1 > 0x9F:
                return False  # surrogate half U+D800..U+DFFF
            i += 3
        elif 0xF0 <= b0 <= 0xF4:
            if i + 3 >= n:
                return False
            b1 = data[i + 1]
            b2 = data[i + 2]
            b3 = data[i + 3]
            if (
                not _is_continuation(b1)
                or not _is_continuation(b2)
                or not _is_continuation(b3)
            ):
                return False
            if b0 == 0xF0 and b1 < 0x90:
                return False  # overlong: would encode U+0000..U+FFFF
            if b0 == 0xF4 and b1 > 0x8F:
                return False  # above U+10FFFF
            i += 4
        else:
            return False
    return True


def _is_continuation(byte: int) -> bool:
    return 0x80 <= byte <= 0xBF
