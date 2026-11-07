// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Windows.Forms;

[assembly: AssemblyTitle("暴力摩托：30周年纪念版 简体中文补丁")]
[assembly: AssemblyDescription("Road Rash 30th Anniversary Edition localization-only patch")]
[assembly: AssemblyVersion("1.1.0.0")]
[assembly: AssemblyFileVersion("1.1.0.0")]

internal static class Installer
{
    const string BackupName = "中文补丁_原版备份";
    static readonly string[] Names = { "RoadRash95.exe", "TEXT/ENU.DLL" };
    static readonly string Root = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);

    sealed class Span
    {
        public int Offset;
        public byte[] Bytes;
    }
    sealed class Patch
    {
        public string Name;
        public int OriginalSize, LocalizedSize;
        public byte[] OriginalHash, LocalizedHash;
        public readonly List<Span> Spans = new List<Span>();
    }
    sealed class Operation
    {
        public string Path, Backup;
        public byte[] Before, After;
        public string Temporary;
    }

    static bool Equal(byte[] a, byte[] b)
    {
        if (a.Length != b.Length) return false;
        for (int i = 0; i < a.Length; ++i) if (a[i] != b[i]) return false;
        return true;
    }
    static byte[] Hash(byte[] bytes)
    {
        using (var sha = SHA256.Create()) return sha.ComputeHash(bytes);
    }
    static byte[] ReadExact(BinaryReader reader, int count)
    {
        if (count < 0 || count > 32 * 1024 * 1024) throw new InvalidDataException("补丁数据长度无效。");
        byte[] data = reader.ReadBytes(count);
        if (data.Length != count) throw new InvalidDataException("补丁数据不完整。");
        return data;
    }
    static List<Patch> ReadPayload()
    {
        var result = new List<Patch>();
        using (var resource = Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.gz"))
        using (var gzip = new GZipStream(resource, CompressionMode.Decompress))
        using (var reader = new BinaryReader(gzip, Encoding.UTF8))
        {
            if (Encoding.ASCII.GetString(ReadExact(reader, 8)) != "RRZH0001" || reader.ReadInt32() != Names.Length)
                throw new InvalidDataException("补丁格式无效。");
            for (int i = 0; i < Names.Length; ++i)
            {
                var patch = new Patch();
                patch.Name = Encoding.UTF8.GetString(ReadExact(reader, reader.ReadInt32()));
                if (patch.Name != Names[i]) throw new InvalidDataException("补丁文件名无效。");
                patch.OriginalSize = reader.ReadInt32(); patch.LocalizedSize = reader.ReadInt32();
                if (patch.OriginalSize <= 0 || patch.LocalizedSize <= 0 || patch.LocalizedSize > 32 * 1024 * 1024)
                    throw new InvalidDataException("补丁目标大小无效。");
                patch.OriginalHash = ReadExact(reader, 32); patch.LocalizedHash = ReadExact(reader, 32);
                int count = reader.ReadInt32();
                if (count < 0 || count > patch.LocalizedSize) throw new InvalidDataException("补丁片段数无效。");
                int previousEnd = 0;
                for (int n = 0; n < count; ++n)
                {
                    int offset = reader.ReadInt32(), length = reader.ReadInt32();
                    if (offset < previousEnd || length < 0 || (long)offset + length > patch.LocalizedSize)
                        throw new InvalidDataException("补丁片段越界。");
                    patch.Spans.Add(new Span { Offset = offset, Bytes = ReadExact(reader, length) });
                    previousEnd = offset + length;
                }
                result.Add(patch);
            }
        }
        return result;
    }
    static string LocalPath(string directory, string relative)
    {
        return Path.Combine(directory, relative.Replace('/', Path.DirectorySeparatorChar));
    }
    static List<Operation> Prepare(List<Patch> patches, bool restore)
    {
        var operations = new List<Operation>();
        foreach (var patch in patches)
        {
            string target = LocalPath(Root, patch.Name);
            if (!File.Exists(target))
                throw new InvalidOperationException("找不到 " + patch.Name + "。\n请把本 EXE 放到游戏根目录（与 RoadRash95.exe 同一目录）后运行。");
            byte[] current = File.ReadAllBytes(target), hash = Hash(current);
            bool original = current.Length == patch.OriginalSize && Equal(hash, patch.OriginalHash);
            bool localized = current.Length == patch.LocalizedSize && Equal(hash, patch.LocalizedHash);
            if (!original && !localized)
                throw new InvalidOperationException("文件版本不匹配：" + patch.Name +
                    "\n支持 Steam build 26105967 的英文原版，或本纯汉化补丁版本。\n尚未修改游戏文件。");
            if (restore ? original : localized) continue;
            string backup = LocalPath(Path.Combine(Root, BackupName), patch.Name);
            byte[] output;
            if (restore)
            {
                if (!File.Exists(backup) || !Equal(Hash(output = File.ReadAllBytes(backup)), patch.OriginalHash))
                    throw new InvalidOperationException("原版备份缺失或不匹配：" + patch.Name + "\n尚未修改游戏文件。");
            }
            else
            {
                if (File.Exists(backup) && !Equal(Hash(File.ReadAllBytes(backup)), patch.OriginalHash))
                    throw new InvalidOperationException("现有原版备份不匹配：" + patch.Name + "\n为保留已有备份，未安装补丁。");
                output = new byte[patch.LocalizedSize];
                Buffer.BlockCopy(current, 0, output, 0, Math.Min(current.Length, output.Length));
                foreach (var span in patch.Spans) Buffer.BlockCopy(span.Bytes, 0, output, span.Offset, span.Bytes.Length);
                if (!Equal(Hash(output), patch.LocalizedHash)) throw new InvalidDataException("差分重建校验失败：" + patch.Name);
            }
            operations.Add(new Operation { Path = target, Backup = backup, Before = current, After = output });
        }
        return operations;
    }
    static string Stage(string target, byte[] contents)
    {
        string temporary = Path.Combine(Path.GetDirectoryName(target), ".rrzh-" + Guid.NewGuid().ToString("N") + ".tmp");
        try
        {
            using (var file = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                file.Write(contents, 0, contents.Length);
                file.Flush(true);
            }
            return temporary;
        }
        catch { Cleanup(temporary); throw; }
    }
    static void Cleanup(string path)
    {
        if (path == null) return;
        try { File.Delete(path); } catch (IOException) { } catch (UnauthorizedAccessException) { }
    }
    static void Apply(List<Operation> operations, bool restore)
    {
        var applied = new List<Operation>();
        try
        {
            // Verify every target before writing, stage both outputs, and never
            // replace an existing original backup with a localized file.
            foreach (var op in operations)
            {
                if (!restore && !File.Exists(op.Backup))
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(op.Backup));
                    string backupTemporary = Stage(op.Backup, op.Before);
                    try { File.Move(backupTemporary, op.Backup); } finally { Cleanup(backupTemporary); }
                }
                op.Temporary = Stage(op.Path, op.After);
            }
            foreach (var op in operations)
            {
                if (!Equal(Hash(File.ReadAllBytes(op.Path)), Hash(op.Before)))
                    throw new IOException("安装期间游戏文件发生变化，请退出游戏后重试。");
                File.Replace(op.Temporary, op.Path, null);
                applied.Add(op);
            }
            foreach (var op in operations)
                if (!Equal(Hash(File.ReadAllBytes(op.Path)), Hash(op.After))) throw new IOException("写入后校验失败。");
        }
        catch (Exception failure)
        {
            var failedRestores = new List<string>();
            for (int i = applied.Count - 1; i >= 0; --i)
            {
                string temporary = null;
                try
                {
                    temporary = Stage(applied[i].Path, applied[i].Before);
                    File.Replace(temporary, applied[i].Path, null);
                }
                catch { failedRestores.Add(applied[i].Path); }
                finally { Cleanup(temporary); }
            }
            if (failedRestores.Count != 0)
                throw new IOException("操作失败，以下文件需要从“" + BackupName + "”手动恢复：\n" +
                    string.Join("\n", failedRestores.ToArray()) + "\n" + failure.Message);
            throw new IOException("操作未完成，游戏文件保持本次操作前的状态。\n" + failure.Message, failure);
        }
        finally { foreach (var op in operations) Cleanup(op.Temporary); }
    }
    static PatchResult Finish(string message, bool error)
    {
        string log = message + "\n\n许可：PolyForm Noncommercial License 1.0.0\nhttps://polyformproject.org/licenses/noncommercial/1.0.0";
        try { File.WriteAllText(Path.Combine(Root, "RoadRash_ZH_CN_Setup.log"), log + Environment.NewLine, Encoding.UTF8); }
        catch (IOException) { } catch (UnauthorizedAccessException) { }
        return new PatchResult(!error, message);
    }
    static PatchResult Execute(bool restore)
    {
        try
        {
            foreach (var process in Process.GetProcessesByName("RoadRash95"))
            {
                process.Dispose();
                throw new InvalidOperationException("请先退出暴力摩托，再运行汉化补丁。");
            }
            var operations = Prepare(ReadPayload(), restore);
            if (operations.Count == 0)
            {
                return Finish(restore ? "游戏文件已经是原版。" : "已经安装本版本汉化，无需重复安装。", false);
            }
            Apply(operations, restore);
            return Finish(restore ? "已恢复英文原版。" :
                "汉化完成。\n请从 Steam 启动游戏，语言保持为英语。\n\n原版备份已保存在游戏目录的“" + BackupName + "”文件夹。", false);
        }
        catch (Exception error)
        {
            string message = error.Message;
            if (error is UnauthorizedAccessException || error.InnerException is UnauthorizedAccessException)
                message += "\n当前目录没有写入权限，请以管理员身份运行本补丁。";
            return Finish(message, true);
        }
    }
    static Form CreateWindow()
    {
        return new PatchWindow("暴力摩托：30周年纪念版 简体中文补丁", Execute);
    }
    [STAThread]
    static int Main(string[] args)
    {
        bool quiet = Array.Exists(args, a => string.Equals(a, "/quiet", StringComparison.OrdinalIgnoreCase)), restore = false;
        foreach (string arg in args)
        {
            if (string.Equals(arg, "/restore", StringComparison.OrdinalIgnoreCase)) restore = true;
            else if (!string.Equals(arg, "/quiet", StringComparison.OrdinalIgnoreCase))
            {
                var invalid = Finish("用法：双击打开安装与还原窗口；/restore 直接还原；/quiet 静默执行。", true);
                if (!quiet) MessageBox.Show(invalid.Message, "暴力摩托：30周年纪念版 简体中文补丁", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 1;
            }
        }
        if (quiet || restore)
        {
            var result = Execute(restore);
            if (!quiet) MessageBox.Show(result.Message, "暴力摩托：30周年纪念版 简体中文补丁", MessageBoxButtons.OK,
                                        result.Success ? MessageBoxIcon.Information : MessageBoxIcon.Error);
            return result.Success ? 0 : 1;
        }
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        using (var window = CreateWindow()) Application.Run(window);
        return 0;
    }
}
