# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Build the localization installer from this source tree; no game binaries required."""
from pathlib import Path
import gzip, hashlib, io, json, os, re, struct, subprocess
import build_runtime

ROOT = Path(__file__).resolve().parent
VERSION = '1.2.0'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build():
    runtime = build_runtime.build()
    english = json.loads((ROOT/'data/english-strings.json').read_text(encoding='utf-8'))
    previous = json.loads((ROOT/'data/previous-translations.json').read_text(encoding='utf-8'))
    translated = json.loads((ROOT/'translations.json').read_text(encoding='utf-8'))
    tokens = re.compile(r'%(?:[-+ #0]*\d*(?:\.\d+)?[hlL]*[diuoxXfFeEgGcs%])')
    stream = io.BytesIO()
    integer = lambda n: stream.write(struct.pack('<i', n))

    def blob(value):
        integer(len(value)); stream.write(value)

    def string(value):
        value = value.encode('utf-8'); n = len(value)
        while n >= 128:
            stream.write(bytes([(n & 127) | 128])); n >>= 7
        stream.write(bytes([n])); stream.write(value)

    stream.write(b'RRZH0002'); blob(runtime.read_bytes())
    # Only our own earlier runtimes are identified by hash. No game EXE or
    # language-file hash, Steam build ID or store identifier gates installation.
    hashes=['7bbfe342e09258779788fbaacd4c6f216fdc9a57f7d695ead5df147a60768cbc',
            'fc4b8369afa5f1b50e46e218c78d4f46bb5354d57cb62aba78c41e6a144bcff5',
            'dba0101605a968f0080e2f8d3a6cd5097dd23c681cd8daa38b4d8f0dd1bc4568']
    integer(len(hashes))
    for value in hashes:blob(bytes.fromhex(value))
    integer(len(translated))
    for key, chinese in sorted(translated.items(), key=lambda item: int(item[0])):
        original = english[key]
        if tokens.findall(original) != tokens.findall(chinese): raise ValueError('Placeholder mismatch: '+key)
        chinese.encode('gbk')
        integer(int(key)); string(original); string(previous.get(key, original)); string(chinese)
    assert translated.get('357', '.') == '.'
    patterns = json.loads((ROOT/'compat_patterns.json').read_text(encoding='utf-8'))
    patterns += [dict(item, count=1, call_offset=-1) for item in json.loads((ROOT/'data/layout-sites.json').read_text(encoding='utf-8'))]
    integer(len(patterns))
    for p in patterns:
        string(p['name']); integer(p['count']); integer(p['call_offset'])
        parts = p['pattern'].split()
        blob(bytes(0 if x == '??' else int(x, 16) for x in parts))
        blob(bytes(0 if x == '??' else 1 for x in parts))
    payload = ROOT/'build/payload.gz'; payload.write_bytes(gzip.compress(stream.getvalue(), mtime=0))
    compiler = Path(os.environ.get('WINDIR', r'C:\Windows'))/'Microsoft.NET/Framework/v4.0.30319/csc.exe'
    output = ROOT/'dist/RoadRash_ZH_CN_Setup.exe'; output.parent.mkdir(exist_ok=True)
    subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:anycpu', '/optimize+', '/utf8output',
                    '/out:'+str(output), '/win32manifest:'+str(ROOT/'app.manifest'),
                    '/resource:'+str(payload)+',payload.gz', '/resource:'+str(ROOT/'LICENSE')+',LICENSE',
                    '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll',
                    str(ROOT/'PatchWindow.cs'), str(ROOT/'GameFiles.cs'), str(ROOT/'Installer.cs')], check=True)
    manifest = dict(version=VERSION, translation_count=len(translated), installer_sha256=digest(output),
                    runtime_sha256=digest(runtime), installer_bytes=output.stat().st_size,
                    game_exe_modified=False, game_hash_allowlist=False, compatibility_warning_allows_full_install=True,
                    install_files=['TEXT/ENU.DLL', 'XINPUT9_1_0.dll'],
                    backup='中文补丁_安装备份/state.bin', license='PolyForm-Noncommercial-1.0.0')
    (ROOT/'build/manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=True))


if __name__ == '__main__':
    build()
