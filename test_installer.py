"""Exercise the packaged EXE on temporary file fixtures; never start the game."""
from pathlib import Path
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
FILES = ('RoadRash95.exe', 'TEXT/ENU.DLL')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(original_dir):
    build = (ROOT / 'build').resolve()
    fixture_root = Path(tempfile.mkdtemp(prefix='installer-test-', dir=build)).resolve()
    # Every generated file and subsequent recursive cleanup stays in build/.
    if fixture_root.parent != build:
        raise RuntimeError('测试目录不在 build 内')
    manifest = json.loads((build / 'manifest.json').read_text(encoding='utf-8'))
    cwd = fixture_root / '不同的工作目录'
    cwd.mkdir()
    checks = []

    def fixture(name, originals=True):
        folder = fixture_root / name
        folder.mkdir()
        shutil.copyfile(ROOT / 'dist/RoadRash_ZH_CN_Setup.exe', folder / '汉化补丁.exe')
        if originals:
            for relative in FILES:
                target = folder / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original_dir / relative, target)
        (folder / '1.RRS').write_bytes(b'test save - must stay unchanged')
        (folder / '原有文件.txt').write_bytes(b'unrelated file - must stay unchanged')
        return folder

    def execute(folder, *args, success=True):
        result = subprocess.run([str(folder / '汉化补丁.exe'), '/quiet', *args], cwd=cwd, timeout=30)
        log = (folder / 'RoadRash_ZH_CN_Setup.log').read_text(encoding='utf-8-sig')
        assert (result.returncode == 0) == success, (result.returncode, log)
        assert (folder / '1.RRS').read_bytes() == b'test save - must stay unchanged'
        assert (folder / '原有文件.txt').read_bytes() == b'unrelated file - must stay unchanged'
        assert not list(folder.rglob('.rrzh-*.tmp')), 'temporary files left behind'
        assert not (folder / 'RoadRashHD.dll').exists(), 'HD module was installed'
        assert not (folder / 'RoadRashHD.ini').exists(), 'HD configuration was installed'
        return log

    def hashes(folder, kind):
        for name in FILES:
            assert sha(folder / name) == manifest['files'][name][kind + '_sha256'], name

    try:
        missing = fixture('没有游戏文件', originals=False)
        assert '根目录' in execute(missing, success=False)
        checks.append('missing game rejected')

        normal = fixture('中文路径 与 空格')
        assert '汉化完成' in execute(normal)
        hashes(normal, 'localized')
        hashes(normal / '中文补丁_原版备份', 'original')
        checks.append('single EXE installs from its own directory and preserves saves')
        assert '无需重复' in execute(normal)
        hashes(normal, 'localized')
        hashes(normal / '中文补丁_原版备份', 'original')
        checks.append('repeat install keeps original backups')
        assert '已恢复' in execute(normal, '/restore')
        hashes(normal, 'original')
        hashes(normal / '中文补丁_原版备份', 'original')
        checks.append('restore returns byte-identical originals')

        unknown = fixture('不兼容版本')
        data = bytearray((unknown / FILES[0]).read_bytes()); data[256] ^= 1
        (unknown / FILES[0]).write_bytes(data)
        before = [sha(unknown / name) for name in FILES]
        assert '版本不匹配' in execute(unknown, success=False)
        assert before == [sha(unknown / name) for name in FILES]
        assert not (unknown / '中文补丁_原版备份').exists()
        checks.append('unknown game version rejected before mutation')

        conflict = fixture('已有不同备份')
        bad_backup = conflict / '中文补丁_原版备份/RoadRash95.exe'
        bad_backup.parent.mkdir(); bad_backup.write_bytes(b'keep this existing backup')
        assert '备份不匹配' in execute(conflict, success=False)
        hashes(conflict, 'original')
        assert bad_backup.read_bytes() == b'keep this existing backup'
        checks.append('conflicting existing backup retained')

        locked = fixture('第二文件被占用')
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                      wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        # Reads remain possible, but replacement of the second file must fail.
        handle = kernel.CreateFileW(str(locked / FILES[1]), 0x80000000, 1, None, 3, 0, None)
        assert handle != ctypes.c_void_p(-1).value, ctypes.get_last_error()
        try:
            assert '操作未完成' in execute(locked, success=False)
        finally:
            kernel.CloseHandle(handle)
        hashes(locked, 'original')
        hashes(locked / '中文补丁_原版备份', 'original')
        checks.append('second-file replacement failure rolls the first file back')

        report = {'passed': checks, 'game_started': False, 'real_install_modified': False,
                  'installer_sha256': sha(ROOT / 'dist/RoadRash_ZH_CN_Setup.exe')}
        (build / 'test-results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report))
    finally:
        if fixture_root.resolve().parent != build:
            raise RuntimeError('拒绝清理 build 以外的目录')
        shutil.rmtree(fixture_root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-dir', required=True, type=Path)
    run(parser.parse_args().original_dir.resolve())
