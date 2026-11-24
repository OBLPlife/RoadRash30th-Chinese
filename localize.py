# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from pathlib import Path
import ctypes
from ctypes import wintypes
import struct

def read_resources(path):
    b = Path(path).read_bytes()
    u16 = lambda p: struct.unpack_from('<H', b, p)[0]
    u32 = lambda p: struct.unpack_from('<I', b, p)[0]
    pe = u32(0x3c)
    opt = pe + 24
    sections = []
    for i in range(u16(pe + 6)):
        o = opt + u16(pe + 20) + i * 40
        sections.append((u32(o + 12), u32(o + 8), u32(o + 20), u32(o + 16)))
    def offset(rva):
        for va, vs, rp, rs in sections:
            if va <= rva < va + max(vs, rs):
                return rp + rva - va
        raise ValueError(hex(rva))
    dd = opt + (96 if u16(opt) == 0x10b else 112)
    root = offset(u32(dd + 16))
    leaves = []
    def walk(rel, path):
        o = root + rel
        for i in range(u16(o + 12) + u16(o + 14)):
            name, child = struct.unpack_from('<II', b, o + 16 + 8 * i)
            if name & 0x80000000:
                n = root + (name & 0x7fffffff)
                name = b[n + 2:n + 2 + u16(n) * 2].decode('utf-16-le')
            p = path + [name]
            if child & 0x80000000:
                walk(child & 0x7fffffff, p)
            else:
                rva, size = struct.unpack_from('<II', b, root + child)
                leaves.append((p, b[offset(rva):offset(rva) + size]))
    walk(0, [])
    return leaves

def read_strings(path):
    strings = {}
    for p, d in read_resources(path):
        if p[0] != 6:
            continue
        pos = 0
        for i in range(16):
            n = struct.unpack_from('<H', d, pos)[0]
            pos += 2
            s = d[pos:pos + n * 2].decode('utf-16-le')
            pos += n * 2
            if s:
                strings[(p[1] - 1) * 16 + i] = s
    return strings

def update_strings(path, strings):
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
    k.BeginUpdateResourceW.restype = wintypes.HANDLE
    k.UpdateResourceW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, wintypes.WORD, ctypes.c_void_p, wintypes.DWORD]
    k.UpdateResourceW.restype = wintypes.BOOL
    k.EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
    k.EndUpdateResourceW.restype = wintypes.BOOL
    handle = k.BeginUpdateResourceW(str(path), False)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        for block in sorted({i // 16 + 1 for i in strings}):
            data = bytearray()
            for i in range((block - 1) * 16, block * 16):
                encoded = strings.get(i, '').encode('utf-16-le')
                data += struct.pack('<H', len(encoded) // 2) + encoded
            buf = ctypes.create_string_buffer(bytes(data))
            if not k.UpdateResourceW(handle, 6, block, 1033, buf, len(data)):
                raise ctypes.WinError(ctypes.get_last_error())
    except BaseException:
        k.EndUpdateResourceW(handle, True)
        raise
    if not k.EndUpdateResourceW(handle, False):
        raise ctypes.WinError(ctypes.get_last_error())

