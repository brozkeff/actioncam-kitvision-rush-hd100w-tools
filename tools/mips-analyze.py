"""Disassemble sectionless big-endian MIPS ELF locally; annotate static references.

Usage: python3 tools/mips-analyze.py PATH OUTPUT_PREFIX
Requires llvm-objdump-14. Input is never executed or modified.
Annotations are linear static hints, not control-flow analysis.
"""

import re
import struct
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Annotate a MIPS firmware disassembly using a temporary section-header copy."""
    source, prefix = map(Path, sys.argv[1:])
    data = source.read_bytes()
    if data[:6] != b"\x7fELF\x01\x02":
        raise ValueError("Expected 32-bit big-endian ELF")
    phoff = struct.unpack_from(">I", data, 28)[0]
    phnum = struct.unpack_from(">H", data, 44)[0]
    headers = [struct.unpack_from(">8I", data, phoff + i * 32) for i in range(phnum)]
    segments = [(h[2], h[1], h[4]) for h in headers if h[0] == 1]

    def offset(address: int) -> int | None:
        """Translate a virtual address into the original ELF file.

        Args:
            address: Virtual address in a loadable segment.

        Returns:
            File offset, or None if the address is unmapped.
        """
        for va, off, size in segments:
            if va <= address < va + size:
                return off + address - va
        return None

    def word(address: int) -> int:
        """Read a big-endian word from a mapped virtual address.

        Args:
            address: Virtual address to inspect.

        Returns:
            Word value, or zero when unmapped.
        """
        off = offset(address)
        return (
            struct.unpack_from(">I", data, off)[0]
            if off is not None and off + 4 <= len(data)
            else 0
        )

    def string(address: int) -> str | None:
        """Identify a plausible printable string at a mapped virtual address.

        Args:
            address: Virtual address to inspect.

        Returns:
            Quoted ASCII text, or None when the bytes do not look like text.
        """
        off = offset(address)
        if off is None:
            return None
        value = data[off : off + 200].split(b"\0")[0]
        if len(value) > 3 and all(32 <= c < 127 or c in (9, 10, 13) for c in value):
            return repr(value.decode("ascii"))
        return None

    tags: dict[int, int] = {}
    for header in headers:
        if header[0] == 2:
            for off in range(header[1], header[1] + header[4], 8):
                tag, value = struct.unpack_from(">2I", data, off)
                tags[tag] = value
    got = tags.get(3, 0)
    symbols: dict[int, str] = {}
    symbol_values: dict[int, str] = {}
    if all(tag in tags for tag in (5, 6, 0x70000011)):
        for index in range(tags[0x70000011]):
            off = offset(tags[6] + index * 16)
            if off is None:
                continue
            nameoff, value = struct.unpack_from(">2I", data, off)
            start = offset(tags[5] + nameoff)
            if start is not None and value:
                name = data[start:].split(b"\0")[0].decode("ascii", errors="replace")
                symbol_values[value] = name
        for address in range(got, got + 4096, 4):
            if word(address) in symbol_values:
                symbols[address] = symbol_values[word(address)]
    patched = bytearray(data)
    if struct.unpack_from(">I", data, 32)[0] == 0:
        textoff = 0x1000
        textva = next(
            va + textoff - off
            for va, off, size in segments
            if off <= textoff < off + size
        )
        size = next(
            off + size - textoff
            for va, off, size in segments
            if off <= textoff < off + size
        )
        names = b"\0.text\0.shstrtab\0"
        namesoff = len(patched)
        patched += names
        while len(patched) % 4:
            patched += b"\0"
        shoff = len(patched)
        patched += b"\0" * 40
        patched += struct.pack(">10I", 1, 1, 6, textva, textoff, size, 0, 0, 4, 0)
        patched += struct.pack(">10I", 7, 3, 0, 0, namesoff, len(names), 0, 0, 1, 0)
        struct.pack_into(">I", patched, 32, shoff)
        struct.pack_into(">3H", patched, 46, 40, 3, 2)
    elf = prefix.with_suffix(".elf")
    elf.write_bytes(patched)
    result = subprocess.run(
        ["llvm-objdump-14", "-d", "--no-show-raw-insn", str(elf)],
        check=True,
        capture_output=True,
        text=True,
    )
    regs: dict[str, int] = {"$gp": got + 0x7FF0, "$zero": 0}
    lines: list[str] = []
    for line in result.stdout.splitlines():
        annotation = None
        location = re.match(r"  ([0-9a-f]+):", line)
        if location and int(location[1], 16) in symbol_values:
            lines.append("\n# FUNCTION " + symbol_values[int(location[1], 16)])
        match = re.search(r"\blui\s+(\$\w+), (\d+)", line)
        if match:
            regs[match[1]] = int(match[2]) << 16
        match = re.search(r"\baddiu\s+(\$\w+), (\$\w+), (-?\d+)", line)
        if match:
            regs[match[1]] = (regs.get(match[2], 0) + int(match[3])) & 0xFFFFFFFF
            annotation = string(regs[match[1]])
        match = re.search(r"\blw\s+(\$\w+), (-?\d+)\((\$\w+)\)", line)
        if match and match[3] == "$gp":
            address = got + 0x7FF0 + int(match[2])
            regs[match[1]] = word(address)
            annotation = symbols.get(address) or string(regs[match[1]])
        lines.append(line + (" # " + annotation if annotation else ""))
    prefix.with_suffix(".txt").write_text("\n".join(lines) + "\n")
    print(f"{source}: {len(symbols)} named GOT references; output {prefix}.txt")


if __name__ == "__main__":
    main()
