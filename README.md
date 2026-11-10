# fssutf_unicode_predicate_utils

A tiny, dependency-free predicate library that answers whether a value is a
well-formed Unicode FSS-UTF (UTF-8) encoding.

## Usage

```python
from fssutf_unicode_predicate_utils import is_fssutf, is_fssutf_string

# Scalar values: in range and not a surrogate.
is_fssutf(0x41)          # True
is_fssutf(0xD800)        # False

# Byte sequences: bytes, bytearray, or a str of byte ordinals.
is_fssutf_string(b"\xc2\xa9")      # True
is_fssutf_string(b"\xc0\xaf")      # False (overlong)
is_fssutf_string("\xc2\xa9")       # True (two byte ordinals)
is_fssutf_string("\u20ac")         # False (cannot be a byte)
```

## Why this exists

Most UTF-8 validators are tied to a particular language's decoder. That is
fine until you need to check bytes that came from a file, a network packet,
or a memory-mapped region and you do not want to allocate a decoded string
just to throw it away. This library is a single, self-contained predicate
over byte sequences. It implements the original FSS-UTF rules directly:
no Unicode database, no codec, no third-party dependency.

The trade-off is that it does not decode. It tells you *whether* a sequence
is well-formed, not *what* it says. If you need the decoded value, use a
codec after the predicate passes.

## The awkward edge

A Python ``str`` is ambiguous here. This library treats a ``str`` as a
sequence of byte ordinals, so ``"\xc2\xa9"`` is a valid two-byte sequence,
and a string containing a character above U+00FF (such as ``"\u20ac"``) is
not a byte sequence at all and returns ``False`` rather than raising. If you
already have a decoded string and want to validate its UTF-8 encoding,
encode it first: ``is_fssutf_string(s.encode("utf-8"))``.

## API

- ``is_fssutf(value)`` — ``True`` for a valid Unicode scalar value (``int``)
or a valid FSS-UTF byte sequence given as a ``str`` of byte ordinals.
Raises ``TypeError`` for other types, including ``bool``.
- ``is_fssutf_string(value)`` — ``True`` for a valid FSS-UTF byte sequence
given as ``bytes``, ``bytearray``, or ``str`` of byte ordinals. Raises
``TypeError`` for other types.
- ``FSSUTFError`` — a ``ValueError`` subclass with an ``offset`` attribute,
provided for callers that want to raise a typed error from their own
validation code.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

