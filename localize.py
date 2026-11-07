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

def patch_font_renderer(path):
    b = bytearray(path.read_bytes())
    # This patch targets Steam build 26105967. Keep original font filenames;
    # only the CreateFontA calls are redirected to a small position-independent
    # adapter selecting SimHei and GB2312_CHARSET. The original IAT thunk remains.
    cave = 0x460cc4
    file_offset = lambda va: va - 0x400c00
    # Preserve Wingdings, which supplies the menu selection arrow.
    # All text faces use SimHei at 75% of the original condensed-font height.
    guard = bytes.fromhex('8b442438813857696e67750981780464696e677400')
    resize = bytes.fromhex('8b44240483f8187c0a6bc003c1f80289442404')
    body_size = 28 + len(resize)
    stub = bytearray(guard)
    stub += bytes.fromhex('e8000000005805')
    stub += struct.pack('<I', body_size - 5)
    stub += bytes.fromhex('89442438c744242486000000')
    stub += resize
    stub += b'\xe9' + struct.pack('<i', 0x48821c - (cave + len(guard) + body_size))
    # The guard jumps to the shared original CreateFontA thunk.
    # Replace its short JE with a jump to a local tail jump after the face name.
    stub += b'SimHei\0'
    tail = len(stub)
    stub[20] = tail - 21
    stub += b'\xe9' + struct.pack('<i', 0x48821c - (cave + tail + 5))
    pos = file_offset(cave)
    assert b[pos:pos + len(stub)] == b'\xcc' * len(stub)
    b[pos:pos + len(stub)] = stub
    for va in [0x43e658, 0x457f9e]:
        pos = file_offset(va)
        assert b[pos:pos+6] == bytes.fromhex('8b354cc16100')
        b[pos:pos+6] = b'\x8d\x35' + struct.pack('<I', cave)
    pos = file_offset(0x460d9d)
    assert b[pos:pos+6] == bytes.fromhex('ff154cc16100')
    b[pos:pos+6] = b'\xe8' + struct.pack('<i', cave - 0x460da2) + b'\x90'
    # The direct call no longer contains an absolute address: remove its old
    # HIGHLOW relocation so ASLR does not corrupt the new relative call.
    u16 = lambda p: struct.unpack_from('<H', b, p)[0]
    u32 = lambda p: struct.unpack_from('<I', b, p)[0]
    pe = u32(0x3c)
    opt = pe + 24
    rva, size = struct.unpack_from('<II', b, opt + 96 + 5*8)
    def rva_offset(r):
        for i in range(u16(pe+6)):
            s = opt + u16(pe+20) + i*40
            va, vs, raw, rs = u32(s+12), u32(s+8), u32(s+20), u32(s+16)
            if va <= r < va+max(vs,rs):
                return raw+r-va
        raise ValueError(hex(r))
    removed = 0
    if rva:
        p = rva_offset(rva)
        end = p + size
        while p < end:
            page, length = struct.unpack_from('<II', b, p)
            if length < 8:
                raise ValueError('Invalid relocation block')
            for q in range(p+8, p+length, 2):
                entry = u16(q)
                if entry >> 12 == 3 and page+(entry & 4095) == 0x60d9f:
                    struct.pack_into('<H', b, q, 0)
                    removed += 1
            p += length
        assert removed == 1
    path.write_bytes(b)

def patch_character_image_names(path):
    b = bytearray(path.read_bytes())
    # The original name accessor reads display strings 358..365. These names
    # are also interpolated into Chars/%s-%c and Chars/%s-F resource paths.
    # Redirect only those three filename callers to English asset identifiers;
    # all display-name callers keep using the translated resource strings.
    cave = 0x4367b0
    stub = bytearray(bytes.fromhex(
        '52'                  # push edx
        '0fb6c1'              # movzx eax,cl
        '83f808'              # cmp eax,8
        '770d'                # ja restore_edx
        'e800000000'          # call next; position-independent table base
        '5a'                  # pop edx
        'c1e003'              # shl eax,3
        '8d44020a'            # lea eax,[edx+eax+10]
        '5a'                  # restore_edx: pop edx
        'c3'                  # ret
    ))
    names = ['Thrash', 'Axle', 'Bose', 'Cydney', 'Jon', 'Pearl', 'Rhonda', 'Jim', 'Mike']
    for name in names:
        stub += name.encode('ascii').ljust(8, b'\0')
    pos = cave - 0x400c00
    assert b[pos:pos+len(stub)] == b'\xcc' * len(stub)
    b[pos:pos+len(stub)] = stub
    for caller in [0x4353b0, 0x4365e1, 0x4366ca]:
        pos = caller - 0x400c00
        old = b'\xe8' + struct.pack('<i', 0x40448f - (caller+5))
        assert b[pos:pos+5] == old
        b[pos:pos+5] = b'\xe8' + struct.pack('<i', cave - (caller+5))
    path.write_bytes(b)

def patch_executable_text(path):
    b = bytearray(path.read_bytes())
    literals = {
        0x1058a8: ('On', '开'),
        0x1058ac: ('Off', '关'),
        0x103634: ('Direct Sound Error', 'DirectSound错误'),
        0x10364c: ('Could not lock the DS Buffer', '无法锁定声音缓冲区'),
        0x10368c: ('Compressed data will overflow buffer. Increase size of buffer!', '压缩数据超出缓冲区，请增大缓冲区！'),
        0x1036d8: ('Uncompressed data will overflow buffer. Increase size of buffer!', '解压数据超出缓冲区，请增大缓冲区！'),
        0x103728: ('Unable to allocate destination buffer.', '无法分配目标缓冲区。'),
        0x103758: ('Error in compressed data!', '压缩数据出错！'),
        0x1037d0: ('Unknown error %d', '未知错误%d'),
        0x104218: ('Line Unavailable', '线路不可用'),
        0x10422c: ('Line Unnamed', '未命名线路'),
        0x10423c: ('Line Name is Empty', '线路名称为空'),
        0x10429c: ('Invalid Location Selected', '所选地点无效'),
        0x104320: ('Could not set format', '无法设置格式'),
        0x10433c: ('Error', '错误'),
        0x104344: ("File corrupt or doesn't exist", '文件损坏或不存在'),
        0x104368: ('Error loading wavefile', '波形音频载入失败'),
        0x104514: ('The IP/X address you specified is invalid.', '指定的IP/X地址无效。'),
        0x104548: ('The name field must be non-NULL', '姓名字段不能为空'),
        0x105a10: ('Audio synchonization', '音频同步'),
    }
    for offset, (english, chinese) in literals.items():
        old = english.encode('ascii') + b'\0'
        new = chinese.encode('gbk') + b'\0'
        assert len(new) <= len(old), english
        assert b[offset:offset+len(old)] == old, english
        b[offset:offset+len(old)] = new.ljust(len(old), b'\0')
    path.write_bytes(b)
    strings = read_strings(path)
    startup = [
        '严重错误', '警告',
        '请先安装暴力摩托，再运行游戏。请执行安装程序。',
        "已忽略无效参数'%s'。\n用法：%s [存档文件]",
        '找不到光驱。', '找不到暴力摩托游戏光盘。',
        '找不到主语言文件。', '找不到所选语言文件，改用英文语言资源。',
    ]
    for index, text in enumerate(startup):
        strings[index] = text
        strings[80+index] = text
    update_strings(path, strings)

