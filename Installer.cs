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
[assembly: AssemblyDescription("Chinese text resources and app-local text runtime; no game EXE replacement")]
[assembly: AssemblyVersion("1.2.0.0")]
[assembly: AssemblyFileVersion("1.2.0.0")]

internal static class Installer
{
    const string Title = "暴力摩托：30周年纪念版 简体中文补丁";
    const string Backup = "中文补丁_安装备份";
    const string StateName = Backup + "/state.bin", PendingName = Backup + "/pending.bin";
    const string LanguageFile = "TEXT/ENU.DLL", RuntimeFile = "XINPUT9_1_0.dll";
    static readonly string Root = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
    static bool quietMode, acceptCompatibilityRisk;
    sealed class Payload
    {
        public byte[] Dll;
        public readonly List<byte[]> CandidateHashes = new List<byte[]>();
        public readonly List<Translation> Text = new List<Translation>();
        public readonly List<Pattern> Patterns = new List<Pattern>();
    }
    sealed class State
    {
        public bool Active;
        public byte[] BeforeLanguage, InstalledLanguage, BeforeDll, InstalledDllHash;
        public readonly Dictionary<string, TextEntry> Changes = new Dictionary<string, TextEntry>();
    }
    sealed class Operation { public string Name; public byte[] Before, After; }
    static string PathOf(string name) { return Path.Combine(Root, name.Replace('/', Path.DirectorySeparatorChar)); }
    static byte[] ReadOptional(string name) { string p = PathOf(name); return File.Exists(p) ? File.ReadAllBytes(p) : null; }
    static bool Equal(byte[] a, byte[] b)
    {
        if (a == null || b == null) return a == b;
        if (a.Length != b.Length) return false;
        for (int i = 0; i < a.Length; ++i) if (a[i] != b[i]) return false;
        return true;
    }
    static byte[] Hash(byte[] data) { using (var sha = SHA256.Create()) return sha.ComputeHash(data); }
    static int Count(BinaryReader reader, int limit)
    {
        int n = reader.ReadInt32();
        if (n < 0 || n > limit) throw new InvalidDataException("补丁或备份记录长度无效。");
        return n;
    }
    static byte[] Bytes(BinaryReader reader)
    {
        int n = reader.ReadInt32(); if (n == -1) return null;
        if (n < 0 || n > 64 * 1024 * 1024) throw new InvalidDataException("补丁或备份数据长度无效。");
        byte[] value = reader.ReadBytes(n);
        if (value.Length != n) throw new EndOfStreamException("补丁或备份不完整。");
        return value;
    }
    static void Bytes(BinaryWriter writer, byte[] value) { writer.Write(value == null ? -1 : value.Length); if (value != null) writer.Write(value); }
    static void Magic(BinaryReader r, string expected)
    {
        if (Encoding.ASCII.GetString(r.ReadBytes(8)) != expected) throw new InvalidDataException("补丁或备份格式不兼容。");
    }
    static Payload ReadPayload()
    {
        var result = new Payload();
        using (var resource = Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.gz"))
        using (var gzip = new GZipStream(resource, CompressionMode.Decompress))
        using (var reader = new BinaryReader(gzip, Encoding.UTF8))
        {
            Magic(reader, "RRZH0002"); result.Dll = Bytes(reader);
            if (result.Dll == null) throw new InvalidDataException("缺少文字模块。");
            int n = Count(reader, 16);
            for (int i = 0; i < n; ++i) result.CandidateHashes.Add(Bytes(reader));
            n = Count(reader, 65536);
            for (int i = 0; i < n; ++i) result.Text.Add(new Translation { Id = reader.ReadInt32(), English = reader.ReadString(), Previous = reader.ReadString(), Chinese = reader.ReadString() });
            n = Count(reader, 64);
            for (int i = 0; i < n; ++i)
            {
                var p = new Pattern { Name = reader.ReadString(), Count = Count(reader, 16), Call = reader.ReadInt32(), Bytes = Bytes(reader), Mask = Bytes(reader) };
                if (p.Bytes == null || p.Mask == null || p.Bytes.Length == 0 || p.Mask.Length != p.Bytes.Length) throw new InvalidDataException("定位特征无效。");
                result.Patterns.Add(p);
            }
        }
        return result;
    }
    static State ReadState(byte[] bytes)
    {
        var state = new State(); if (bytes == null) return state;
        using (var stream = new MemoryStream(bytes))
        using (var r = new BinaryReader(stream, Encoding.UTF8))
        {
            Magic(r, "RRZHST02"); state.Active = r.ReadBoolean();
            state.BeforeLanguage = Bytes(r); state.InstalledLanguage = Bytes(r);
            state.BeforeDll = Bytes(r); state.InstalledDllHash = Bytes(r);
            int count = Count(r, 65536);
            for (int i = 0; i < count; ++i)
            {
                var c = new TextEntry { Id = r.ReadInt32(), Language = r.ReadInt32(), Before = r.ReadString(), After = r.ReadString() };
                state.Changes.Add(c.Key, c);
            }
            if (state.Active && (state.BeforeLanguage == null || state.InstalledLanguage == null || state.InstalledDllHash == null || state.InstalledDllHash.Length != 32))
                throw new InvalidDataException("安装备份记录不完整。");
        }
        return state;
    }
    static byte[] SaveState(State state)
    {
        using (var stream = new MemoryStream())
        using (var w = new BinaryWriter(stream, Encoding.UTF8))
        {
            w.Write(Encoding.ASCII.GetBytes("RRZHST02")); w.Write(state.Active);
            Bytes(w, state.BeforeLanguage); Bytes(w, state.InstalledLanguage); Bytes(w, state.BeforeDll); Bytes(w, state.InstalledDllHash);
            w.Write(state.Changes.Count);
            foreach (var c in state.Changes.Values) { w.Write(c.Id); w.Write(c.Language); w.Write(c.Before); w.Write(c.After); }
            return stream.ToArray();
        }
    }
    static void WriteAtomic(string name, byte[] value)
    {
        string target = PathOf(name);
        if (value == null) { File.Delete(target); return; }
        Directory.CreateDirectory(Path.GetDirectoryName(target));
        string temp = target + ".rrzh-" + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            using (var f = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None)) { f.Write(value, 0, value.Length); f.Flush(true); }
            if (File.Exists(target)) File.Replace(temp, target, null); else File.Move(temp, target);
        }
        finally { if (File.Exists(temp)) File.Delete(temp); }
    }
    static byte[] Journal(List<Operation> operations)
    {
        using (var stream = new MemoryStream())
        using (var w = new BinaryWriter(stream, Encoding.UTF8))
        {
            w.Write(Encoding.ASCII.GetBytes("RRZHJN02")); w.Write(operations.Count);
            foreach (var op in operations) { w.Write(op.Name); Bytes(w, op.Before); Bytes(w, op.After); }
            return stream.ToArray();
        }
    }
    static void Recover()
    {
        byte[] pending = ReadOptional(PendingName); if (pending == null) return;
        var operations = new List<Operation>();
        using (var r = new BinaryReader(new MemoryStream(pending), Encoding.UTF8))
        {
            Magic(r, "RRZHJN02"); int n = Count(r, 3);
            for (int i = 0; i < n; ++i)
            {
                string name = r.ReadString();
                if (name != LanguageFile && name != RuntimeFile && name != StateName) throw new InvalidDataException("恢复记录包含未知文件。");
                operations.Add(new Operation { Name = name, Before = Bytes(r), After = Bytes(r) });
            }
        }
        foreach (var op in operations)
        {
            byte[] current = ReadOptional(op.Name);
            if (!Equal(current, op.Before) && !Equal(current, op.After)) throw new IOException("上次操作中断后，文件又被其他程序修改：" + op.Name + "。已保留恢复记录，请勿删除“" + Backup + "”。");
        }
        for (int i = operations.Count - 1; i >= 0; --i)
        {
            var op = operations[i]; if (!Equal(ReadOptional(op.Name), op.Before)) WriteAtomic(op.Name, op.Before);
        }
        File.Delete(PathOf(PendingName));
    }
    static void Apply(List<Operation> operations)
    {
        operations.RemoveAll(op => Equal(op.Before, op.After));
        if (operations.Count == 0) return;
        WriteAtomic(PendingName, Journal(operations));
        try
        {
            foreach (var op in operations)
            {
                if (!Equal(ReadOptional(op.Name), op.Before)) throw new IOException("操作期间文件发生变化：" + op.Name);
                WriteAtomic(op.Name, op.After);
                if (!Equal(ReadOptional(op.Name), op.After)) throw new IOException("写入核对失败：" + op.Name);
            }
            File.Delete(PathOf(PendingName));
        }
        catch (Exception failure)
        {
            try { Recover(); }
            catch (Exception recovery) { throw new IOException("操作中断，已保留备份和恢复记录。关闭占用文件的程序后，重新运行安装器。\n" + failure.Message + "\n" + recovery.Message); }
            throw new IOException("操作未完成，已回滚到本次操作前的状态。\n" + failure.Message);
        }
    }
    static bool Ours(byte[] dll, State state, Payload payload)
    {
        if (dll == null) return true;
        byte[] hash = Hash(dll);
        if (state.Active && Equal(hash, state.InstalledDllHash)) return true;
        if (Equal(dll, payload.Dll)) return true;
        foreach (var known in payload.CandidateHashes) if (Equal(hash, known)) return true;
        return false;
    }
    static void ConfirmCompatibility(List<string> warnings)
    {
        if (warnings.Count == 0) return;
        string warning = "检测到当前游戏的相关结构与已知版本存在差异：\n\n" +
            string.Join("\n", new List<string>(new HashSet<string>(warnings)).ToArray()) +
            "\n\n继续将安装完整汉化资源和文字 DLL，不会自动改为精简安装。" +
            "\n可能出现文本异常、画面异常、功能失效、报错或游戏崩溃。" +
            "\n操作会保留备份，可退出游戏后用本安装器还原。";
        if (acceptCompatibilityRisk) return;
        if (quietMode) throw new InvalidOperationException(warning + "\n\n静默模式需要明确确认：接受上述风险时添加 /accept-risk，或双击安装器选择继续。");
        if (MessageBox.Show(warning + "\n\n仍要继续全量安装吗？（是：继续；否：取消）", Title,
            MessageBoxButtons.YesNo, MessageBoxIcon.Warning, MessageBoxDefaultButton.Button2) != DialogResult.Yes)
            throw new OperationCanceledException("已取消安装，未写入本次汉化改动。");
    }
    static string Perform(bool restore)
    {
        foreach (var process in Process.GetProcessesByName("RoadRash95"))
        {
            process.Dispose(); throw new InvalidOperationException("请先退出暴力摩托，再安装或还原补丁。");
        }
        byte[] exe = ReadOptional("RoadRash95.exe"), language = ReadOptional(LanguageFile);
        if (exe == null || language == null) throw new InvalidOperationException("请把本 EXE 放到游戏根目录（与 RoadRash95.exe 同一文件夹）。需要 TEXT/ENU.DLL。");
        Recover(); language = ReadOptional(LanguageFile);
        byte[] beforeState = ReadOptional(StateName), currentDll = ReadOptional(RuntimeFile);
        State state = ReadState(beforeState); Payload payload = ReadPayload();
        if (restore && !state.Active) return "未发现本版的安装记录，无需还原。旧版备份保持原样。";
        if (!Ours(currentDll, state, payload)) throw new InvalidOperationException("已有其他来源的 XINPUT9_1_0.dll，已保留原文件。请先处理同名模块冲突，再安装或还原。" );
        byte[] afterLanguage, afterDll;
        int changed = 0, preserved = 0;
        string compatibilityNote = "";
        if (restore)
        {
            if (Equal(language, state.InstalledLanguage)) afterLanguage = state.BeforeLanguage;
            else
            {
                var entries = new GameImage(language).Strings();
                foreach (var c in state.Changes.Values)
                {
                    TextEntry item;
                    if (entries.TryGetValue(c.Key, out item) && item.Before == c.After) item.After = c.Before;
                    else ++preserved;
                }
                afterLanguage = TextResources.Rewrite(language, entries);
            }
            afterDll = state.BeforeDll; state.Active = false;
        }
        else
        {
            var compatibility = new GameImage(exe).CheckGame(payload.Patterns);
            var entries = new GameImage(language).Strings();
            var table = new Dictionary<int, Translation>(); foreach (var t in payload.Text) table.Add(t.Id, t);
            if (!state.Active) state = new State { BeforeLanguage = language, BeforeDll = currentDll };
            int recognized = 0;
            foreach (var item in entries.Values)
            {
                Translation t; if (!table.TryGetValue(item.Id, out t)) continue;
                if (item.Before != t.English && item.Before != t.Previous && item.Before != t.Chinese) { ++preserved; continue; }
                ++recognized; item.After = t.Chinese;
                if (item.Before == item.After) continue;
                ++changed;
                TextEntry owned;
                if (!state.Changes.TryGetValue(item.Key, out owned)) state.Changes[item.Key] = new TextEntry { Id = item.Id, Language = item.Language, Before = item.Before, After = item.After };
                else
                {
                    if (item.Before != owned.After && item.Before != owned.Before) owned.Before = item.Before;
                    owned.After = item.After;
                }
            }
            if (recognized == 0) throw new InvalidDataException("语言资源没有可识别的原文或已有译文，未安装汉化。");
            TextResources.CheckBudget(entries);
            afterLanguage = TextResources.Rewrite(language, entries); afterDll = payload.Dll;
            // The complete output is prepared before asking. A warning never
            // selects a reduced payload or silently omits the runtime DLL.
            ConfirmCompatibility(compatibility.Warnings);
            if (compatibility.Warnings.Count != 0)
                compatibilityNote = "\n已接受兼容性风险，完整汉化资源和文字 DLL 均已安装。\n" +
                    string.Join("\n", new List<string>(new HashSet<string>(compatibility.Warnings)).ToArray());
            state.Active = true; state.InstalledLanguage = afterLanguage; state.InstalledDllHash = Hash(afterDll);
        }
        var operations = new List<Operation> {
            new Operation { Name = LanguageFile, Before = language, After = afterLanguage },
            new Operation { Name = RuntimeFile, Before = currentDll, After = afterDll },
            new Operation { Name = StateName, Before = beforeState, After = SaveState(state) }
        };
        Apply(operations);
        string note = preserved == 0 ? "" : "\n保留了 " + preserved + " 条由其他版本或补丁改动的文本。";
        if (restore) return "已恢复本版安装前的资源和文字模块。\n安装前已有的旧汉化会保留。高清补丁和存档不受影响。" + note;
        return "汉化安装完成（更新 " + changed + " 条文本）。\n按原来的方式启动游戏，语言保持英语。\n还原备份保存在“" + Backup + "”。" + compatibilityNote + note;
    }
    static PatchResult Execute(bool restore)
    {
        bool success = true; string message;
        try { message = Perform(restore); }
        catch (OperationCanceledException e) { message = e.Message; }
        catch (Exception e) { success = false; message = e.Message; }
        try { File.WriteAllText(PathOf("RoadRash_ZH_CN_Setup.log"), DateTime.Now.ToString("s") + "\r\n" + message + "\r\n", Encoding.UTF8); }
        catch (IOException) { } catch (UnauthorizedAccessException) { }
        return new PatchResult(success, message);
    }
    [STAThread]
    static int Main(string[] args)
    {
        bool quiet = false, restore = false;
        foreach (string arg in args)
        {
            if (arg.Equals("/quiet", StringComparison.OrdinalIgnoreCase)) quiet = true;
            else if (arg.Equals("/accept-risk", StringComparison.OrdinalIgnoreCase)) acceptCompatibilityRisk = true;
            else if (arg.Equals("/restore", StringComparison.OrdinalIgnoreCase)) restore = true;
            else return 2;
        }
        quietMode = quiet;
        if (quiet || restore)
        {
            var result = Execute(restore);
            if (!quiet) MessageBox.Show(result.Message, Title, MessageBoxButtons.OK, result.Success ? MessageBoxIcon.Information : MessageBoxIcon.Error);
            return result.Success ? 0 : 1;
        }
        Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
        using (var window = new PatchWindow(Title, Execute)) Application.Run(window);
        return 0;
    }
}
