"""Build the localization-only installer from the user's original game files."""
from pathlib import Path
import argparse
import gzip
import hashlib
import io
import json
import os
import re
import struct
import subprocess

import localize

ROOT = Path(__file__).resolve().parent
ORIGINALS = {
    'RoadRash95.exe': '9e40e25737149ab095061b7154797a35495faea97644fafc5a1e616f1400c968',
    'TEXT/ENU.DLL': '2309d5b30560103c7a8b3b97e626877fb89fd85164f82186082dc1c665466e70',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def spans(before, after):
    """Offset replacements; the destination starts as a copy of the original."""
    changed = [i for i in range(len(after)) if i >= len(before) or before[i] != after[i]]
    result = []
    if changed:
        start = end = changed[0]
        for offset in changed[1:]:
            if offset - end > 12:
                result.append((start, after[start:end + 1]))
                start = offset
            end = offset
        result.append((start, after[start:end + 1]))
    return result


def build(original_dir):
    original_dir = original_dir.resolve()
    original = {}
    for name, expected in ORIGINALS.items():
        original[name] = (original_dir / name).read_bytes()
        if digest(original[name]) != expected:
            raise ValueError(f'原版文件版本不匹配：{name}。需要 Steam build 26105967 的英文原版文件。')

    stage = ROOT / 'build' / 'localized'
    for name, data in original.items():
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    strings = localize.read_strings(stage / 'TEXT/ENU.DLL')
    translated = json.loads((ROOT / 'translations.json').read_text(encoding='utf-8'))
    tokens = re.compile(r'%(?:[-+ #0]*\d*(?:\.\d+)?[hlL]*[diuoxXfFeEgGcs%])')
    for key, value in translated.items():
        index = int(key)
        if index not in strings or tokens.findall(strings[index]) != tokens.findall(value):
            raise ValueError(f'翻译占位符或字符串编号不匹配：{index}')
        value.encode('gbk')
        strings[index] = value
    localize.update_strings(stage / 'TEXT/ENU.DLL', strings)
    exe = stage / 'RoadRash95.exe'
    localize.patch_font_renderer(exe)
    localize.patch_character_image_names(exe)
    localize.patch_executable_text(exe)
    if localize.read_strings(stage / 'TEXT/ENU.DLL') != strings:
        raise ValueError('语言资源写入校验失败')
    # No HD entry stub, renderer import, graphics hook or resolution override.
    if b'RoadRashHD' in exe.read_bytes() or b'.rrhd' in exe.read_bytes():
        raise ValueError('纯汉化程序包含了高清模块标记')

    payload = io.BytesIO()
    payload.write(b'RRZH0001')
    payload.write(struct.pack('<I', len(ORIGINALS)))
    manifest = {'version': '1.0.0', 'steam_build': 26105967, 'localization_only': True, 'files': {}}
    for name, before in original.items():
        after = (stage / name).read_bytes()
        changes = spans(before, after)
        # Check the actual delta, rather than only its target file.
        rebuilt = bytearray(before[:len(after)])
        rebuilt.extend(b'\0' * (len(after) - len(rebuilt)))
        for offset, data in changes:
            rebuilt[offset:offset + len(data)] = data
        if rebuilt != after:
            raise ValueError(f'差分重建失败：{name}')
        encoded = name.encode('utf-8')
        payload.write(struct.pack('<I', len(encoded)) + encoded)
        payload.write(struct.pack('<II', len(before), len(after)))
        payload.write(hashlib.sha256(before).digest() + hashlib.sha256(after).digest())
        payload.write(struct.pack('<I', len(changes)))
        for offset, data in changes:
            payload.write(struct.pack('<II', offset, len(data)) + data)
        manifest['files'][name] = {'original_sha256': digest(before), 'localized_sha256': digest(after),
                                   'original_bytes': len(before), 'localized_bytes': len(after), 'spans': len(changes)}
    packed = ROOT / 'build' / 'payload.gz'
    packed.write_bytes(gzip.compress(payload.getvalue(), mtime=0))

    compiler = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Microsoft.NET/Framework/v4.0.30319/csc.exe'
    if not compiler.is_file():
        raise FileNotFoundError('需要 Windows .NET Framework 4.x 自带的 csc.exe')
    output = ROOT / 'dist' / 'RoadRash_ZH_CN_Setup.exe'
    output.parent.mkdir(exist_ok=True)
    subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:anycpu', '/optimize+', '/utf8output',
                    '/out:' + str(output), '/win32manifest:' + str(ROOT / 'app.manifest'),
                    '/resource:' + str(packed) + ',payload.gz', '/reference:System.Windows.Forms.dll',
                    str(ROOT / 'Installer.cs')], check=True)
    manifest['installer_sha256'] = digest(output.read_bytes())
    manifest['installer_bytes'] = output.stat().st_size
    (ROOT / 'build' / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'installer': str(output), 'bytes': output.stat().st_size,
                      'translated_entries': len(translated), 'localization_only': True}, ensure_ascii=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-dir', required=True, type=Path,
                        help='包含英文原版 RoadRash95.exe 和 TEXT/ENU.DLL 的目录；只读取，不修改')
    build(parser.parse_args().original_dir)
