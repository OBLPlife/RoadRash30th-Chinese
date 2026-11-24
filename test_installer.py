# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""File-only installer regression checks in disposable copies. Never starts the game."""
from pathlib import Path
import argparse, ctypes, hashlib, io, json, os, shutil, struct, subprocess, tempfile
from ctypes import wintypes
from localize import read_resources, read_strings, update_strings

ROOT = Path(__file__).resolve().parent
SETUP = ROOT/'dist/RoadRash_ZH_CN_Setup.exe'
ENU = 'TEXT/ENU.DLL'
DLL = 'XINPUT9_1_0.dll'
STATE = '中文补丁_安装备份/state.bin'
PENDING = '中文补丁_安装备份/pending.bin'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def journal(operations):
    stream = io.BytesIO(); stream.write(b'RRZHJN02'); stream.write(struct.pack('<i', len(operations)))
    for name, before, after in operations:
        name = name.encode('utf-8'); length = len(name)
        while length >= 128:
            stream.write(bytes([(length & 127) | 128])); length >>= 7
        stream.write(bytes([length])); stream.write(name)
        for value in (before, after):
            stream.write(struct.pack('<i', -1 if value is None else len(value)))
            if value is not None:stream.write(value)
    return stream.getvalue()


def main(args):
    work = Path(tempfile.mkdtemp(prefix='installer-files-', dir=ROOT/'build')).resolve()
    assert work.parent == (ROOT/'build').resolve()
    cwd = work/'另一工作目录'; cwd.mkdir()
    checks = []
    original = {n:(args.original_dir/n).read_bytes() for n in ['RoadRash95.exe', ENU]}
    translation = json.loads((ROOT/'translations.json').read_text(encoding='utf-8'))

    def fixture(name, source=None):
        p = work/name; p.mkdir(); (p/'TEXT').mkdir()
        for n,v in original.items():
            (p/n).write_bytes((source/n).read_bytes() if source else v)
        shutil.copy2(SETUP,p/'汉化补丁.exe')
        for n in range(1,4):(p/(str(n)+'.RRS')).write_bytes(('unchanged save '+str(n)).encode())
        (p/'用户资料.txt').write_bytes(b'preserve unrelated file')
        return p

    def run(p, restore=False, ok=True, hd=False, accept_risk=False, previous=False):
        name = '高清补丁.exe' if hd else ('上一版汉化.exe' if previous else '汉化补丁.exe')
        command = [str(p/name), '/quiet']+(['/restore'] if restore else [])
        if accept_risk: command.append('/accept-risk')
        result = subprocess.run(command, cwd=cwd, timeout=60)
        log = p/('RoadRash_HD_Setup.log' if hd else 'RoadRash_ZH_CN_Setup.log')
        msg = log.read_text(encoding='utf-8-sig') if log.exists() else 'no log'
        assert (result.returncode == 0) == ok, (p.name,result.returncode,msg)
        for n in range(1,4):assert (p/(str(n)+'.RRS')).read_bytes()==('unchanged save '+str(n)).encode()
        assert (p/'用户资料.txt').read_bytes()==b'preserve unrelated file'
        assert not (p/PENDING).exists(), msg
        return msg

    def unchanged_exe(p, expected=None):
        assert (p/'RoadRash95.exe').read_bytes()==(original['RoadRash95.exe'] if expected is None else expected)

    def localized(p):
        texts=read_strings(p/ENU)
        for key,value in translation.items():assert texts[int(key)]==value,(p.name,key,texts[int(key)],value)
        assert texts[357]=='.'
        assert (p/DLL).read_bytes()==(ROOT/'build/runtime'/DLL).read_bytes()

    normal=fixture('中文路径 与 空格')
    run(normal); localized(normal); unchanged_exe(normal)
    nontext=lambda p:{tuple(k):v for k,v in read_resources(p) if k[0]!=6}
    assert nontext(normal/ENU)==nontext(args.original_dir/ENU)
    checks.append('original install: all 1166 translations, original police placeholder, non-string resources, EXE and three save fixtures preserved')
    state=(normal/STATE).read_bytes(); run(normal); assert (normal/STATE).read_bytes()==state
    checks.append('repeat install preserves first restore point and does not duplicate hooks')
    run(normal,restore=True)
    assert (normal/ENU).read_bytes()==original[ENU] and not (normal/DLL).exists()
    unchanged_exe(normal); run(normal,restore=True); run(normal); localized(normal); run(normal,restore=True)
    checks.append('restore is byte-identical on clean baseline; repeated restore and reinstall work')

    unknown=fixture('无关版本字段变化')
    b=bytearray(original['RoadRash95.exe']);b[0x40]^=1;(unknown/'RoadRash95.exe').write_bytes(b)
    run(unknown);localized(unknown);unchanged_exe(unknown,b);run(unknown,restore=True)
    checks.append('unrelated EXE byte change accepted without whole-file hash whitelist')

    def warning_case(name, exe, warning):
        p=fixture(name); (p/'RoadRash95.exe').write_bytes(exe)
        msg=run(p,ok=False)
        assert warning in msg and '/accept-risk' in msg, msg
        assert (p/ENU).read_bytes()==original[ENU] and not (p/DLL).exists() and not (p/STATE).exists()
        unchanged_exe(p,exe)
        msg=run(p,accept_risk=True)
        assert warning in msg and '已接受兼容性风险' in msg, msg
        localized(p); unchanged_exe(p,exe)
        state=(p/STATE).read_bytes(); run(p,accept_risk=True)
        assert (p/STATE).read_bytes()==state
        run(p,restore=True)
        assert (p/ENU).read_bytes()==original[ENU] and not (p/DLL).exists()
        unchanged_exe(p,exe)
        checks.append(name+': warning without consent leaves files unchanged; accepting installs all 1166 texts and the complete DLL; repeat and exact restore work')

    b=bytearray(original['RoadRash95.exe'])
    # Mutate a known accessor only in the disposable file, which is never run.
    assert b[0x332e0-0xc00:0x332e0-0xc00+6]==bytes.fromhex('0fb6c183f808')
    b[0x332e0-0xc00]^=1
    warning_case('人物立绘调用变化',b,'人物立绘调用目标')

    b=bytearray(original['RoadRash95.exe'])
    at=b.lower().index(b'xinput9_1_0.dll\0'); b[at]=ord('z')
    warning_case('文字模块入口变化',b,'加载入口已变化')

    b=bytearray(original['RoadRash95.exe'])
    at=b.index(b'LoadStringA\0'); b[at+10]=ord('Z')
    warning_case('文字接口变化',b,'文字接口已变化')

    b=bytearray(original['RoadRash95.exe'])
    site=json.loads((ROOT/'data/layout-sites.json').read_text(encoding='utf-8'))[0]
    tokens=site['pattern'].split(); hits=[i for i in range(len(b)-len(tokens)+1)
        if all(t=='??' or b[i+j]==int(t,16) for j,t in enumerate(tokens))]
    assert len(hits)==1
    b[hits[0]]^=1
    warning_case('菜单排版结构变化',b,'菜单排版结构已变化')

    b=bytearray(original['RoadRash95.exe'])
    optional=struct.unpack_from('<I',b,60)[0]+24
    struct.pack_into('<II',b,optional+104,0,0)
    warning_case('导入表缺失',b,'没有可识别的导入表')

    # This Windows PE64 file is only a non-game parsing fixture. Never execute it.
    b=(Path(os.environ['WINDIR'])/'System32/cmd.exe').read_bytes()
    pe=struct.unpack_from('<I',b,60)[0]
    assert struct.unpack_from('<H',b,pe+24)[0]==0x20b
    warning_case('程序架构变化',b,'不再是已知的 32 位架构')

    foreign=fixture('同名第三方模块');(foreign/DLL).write_bytes(b'foreign dll, preserve me')
    assert '其他来源' in run(foreign,ok=False)
    assert (foreign/DLL).read_bytes()==b'foreign dll, preserve me' and (foreign/ENU).read_bytes()==original[ENU]
    checks.append('unknown same-name proxy retained without overwrite')

    repaired=fixture('校验修复与模块丢失');run(repaired);(repaired/DLL).unlink();(repaired/ENU).write_bytes(original[ENU])
    run(repaired);localized(repaired);run(repaired,restore=True);assert (repaired/ENU).read_bytes()==original[ENU]
    checks.append('reinstall after resource replacement and missing own DLL repairs patch and retains restore point')

    merged=fixture('资源外部修改');run(merged)
    strings=read_strings(merged/ENU);strings[73]='用户保留的分辨率说明';strings[992]='external change';update_strings(merged/ENU,strings)
    run(merged,restore=True)
    expected=read_strings(args.original_dir/ENU);expected[73]=strings[73];expected[992]=strings[992]
    assert read_strings(merged/ENU)==expected
    checks.append('resource-level restore preserves externally modified text without restoring stale full file')

    locked=fixture('第二文件被占用');run(locked)
    before={n:(locked/n).read_bytes() for n in [ENU,DLL,STATE]}
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE;kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateFileW(str(locked/DLL),0x80000000,1,None,3,0,None)
    assert handle!=ctypes.c_void_p(-1).value
    try: assert '回滚' in run(locked,restore=True,ok=False)
    finally:kernel.CloseHandle(handle)
    assert all((locked/n).read_bytes()==v for n,v in before.items())
    checks.append('second-file restore failure rolls resource file back atomically')

    for step in [1,2,3]:
        interrupted=fixture('模拟中断'+str(step));run(interrupted)
        operations=[(ENU,original[ENU],(interrupted/ENU).read_bytes()),(DLL,None,(interrupted/DLL).read_bytes()),(STATE,None,(interrupted/STATE).read_bytes())]
        for n,pre,post in operations[step:]:
            if pre is None:(interrupted/n).unlink()
            else:(interrupted/n).write_bytes(pre)
        (interrupted/PENDING).write_bytes(journal(operations))
        run(interrupted,restore=True)
        assert (interrupted/ENU).read_bytes()==original[ENU] and not (interrupted/DLL).exists()
    checks.append('simulated interruption after each of three writes is recovered on next invocation')

    if args.legacy_dir:
        legacy=fixture('旧汉化升级',args.legacy_dir)
        prior={n:(legacy/n).read_bytes() for n in ['RoadRash95.exe',ENU]}
        run(legacy);unchanged_exe(legacy,prior['RoadRash95.exe'])
        assert read_strings(legacy/ENU)[6]=='洗手间';run(legacy,restore=True)
        assert all((legacy/n).read_bytes()==v for n,v in prior.items())
        checks.append('legacy localization upgrade restores its own preinstall state without replacing legacy/HD EXE')
    if args.candidate_dir:
        candidate=fixture('本地候选版接管',args.candidate_dir)
        shutil.copy2(args.candidate_dir/DLL,candidate/DLL)
        prior={n:(candidate/n).read_bytes() for n in ['RoadRash95.exe',ENU,DLL]}
        run(candidate);run(candidate,restore=True)
        assert all((candidate/n).read_bytes()==v for n,v in prior.items())
        checks.append('known local candidate upgrade and restore preserves user-confirmed prior DLL/resources')
    if args.previous_installer:
        previous=fixture('先前候选包升级'); shutil.copy2(args.previous_installer,previous/'上一版汉化.exe')
        run(previous,previous=True)
        run(previous); localized(previous); unchanged_exe(previous)
        run(previous,restore=True)
        assert (previous/ENU).read_bytes()==original[ENU] and not (previous/DLL).exists()
        checks.append('earlier candidate upgrade installs the complete current runtime and retains original restore point')
    if args.hd_installer:
        for order in ['zh-hd','hd-zh']:
            for first_restore in ['zh','hd']:
                p=fixture(order+'-restore-'+first_restore);shutil.copy2(args.hd_installer,p/'高清补丁.exe')
                for which in order.split('-'):run(p,hd=which=='hd')
                localized(p)
                hd_exe=(p/'RoadRash95.exe').read_bytes();hd_dll=(p/'RoadRashHD.dll').read_bytes();ini=(p/'RoadRashHD.ini').read_bytes()
                run(p,hd=True);run(p);assert (p/'RoadRash95.exe').read_bytes()==hd_exe
                if first_restore=='zh':
                    run(p,restore=True);assert (p/'RoadRash95.exe').read_bytes()==hd_exe and (p/'RoadRashHD.dll').read_bytes()==hd_dll
                    run(p,restore=True,hd=True)
                else:
                    run(p,restore=True,hd=True);localized(p);run(p,restore=True)
                unchanged_exe(p);assert (p/ENU).read_bytes()==original[ENU] and not (p/DLL).exists() and not (p/'RoadRashHD.dll').exists()
                assert (p/'RoadRashHD.ini').read_bytes()==ini
                checks.append(order+' / restore '+first_restore+' first: independent restore, repeated installers and original EXE/resource recovery; HD retains its own INI by design')

    report=dict(version='1.2.0',passed=checks,game_started=False,gui_opened=False,live_game_modified=False,
                save_tests='three synthetic file-preservation fixtures only; no in-game create/load/overwrite test',
                installer_sha256=sha(SETUP),runtime_sha256=sha(ROOT/'build/runtime'/DLL),fixture_root=str(work))
    (ROOT/'build/test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-dir',required=True,type=Path)
    parser.add_argument('--legacy-dir',type=Path)
    parser.add_argument('--candidate-dir',type=Path)
    parser.add_argument('--previous-installer',type=Path)
    parser.add_argument('--hd-installer',type=Path)
    main(parser.parse_args())
