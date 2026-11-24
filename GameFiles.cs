// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

internal sealed class TextEntry
{
    public int Id, Language;
    public string Before, After;
    public string Key { get { return Language + ":" + Id; } }
}

internal sealed class Pattern
{
    public string Name;
    public byte[] Bytes, Mask;
    public int Count, Call;
}

internal sealed class Translation
{
    public int Id;
    public string English, Previous, Chinese;
}

internal sealed class Compatibility
{
    public readonly List<string> Warnings = new List<string>();
}

internal sealed class GameImage
{
    public readonly byte[] Data;
    public readonly int Optional;
    public readonly bool IsX86;
    readonly int directories;
    sealed class Section { public int Rva, Virtual, Raw, Size, Flags; }
    readonly List<Section> sections = new List<Section>();
    public GameImage(byte[] data)
    {
        Data = data;
        if (U16(0) != 0x5a4d) throw new InvalidDataException("不是有效的 Windows 程序文件。");
        int pe = I(60); Optional = pe + 24;
        if (I(pe) != 0x4550 || (U16(Optional) != 0x10b && U16(Optional) != 0x20b))
            throw new InvalidDataException("程序的 PE 文件结构损坏或无法读取。");
        IsX86 = U16(pe + 4) == 0x14c && U16(Optional) == 0x10b;
        directories = Optional + (U16(Optional) == 0x10b ? 96 : 112);
        int start = Optional + U16(pe + 20), count = U16(pe + 6);
        if (count == 0 || count > 96) throw new InvalidDataException("PE 区段表无效。");
        for (int n = 0; n < count; ++n)
        {
            int p = start + n * 40;
            var s = new Section { Rva = I(p + 12), Virtual = I(p + 8), Raw = I(p + 20), Size = I(p + 16), Flags = I(p + 36) };
            Bounds(s.Raw, s.Size); sections.Add(s);
        }
    }
    void Bounds(int p, int n)
    {
        if (p < 0 || n < 0 || (long)p + n > Data.Length) throw new InvalidDataException("文件结构越界或不完整。");
    }
    public int I(int p) { Bounds(p, 4); return BitConverter.ToInt32(Data, p); }
    int U16(int p) { Bounds(p, 2); return BitConverter.ToUInt16(Data, p); }
    int Offset(int rva)
    {
        foreach (var s in sections) if (rva >= s.Rva && (long)rva < (long)s.Rva + s.Size) return s.Raw + rva - s.Rva;
        throw new InvalidDataException("文件地址不在有效区段内。");
    }
    string CString(int rva)
    {
        int p = Offset(rva), end = p;
        while (end < Data.Length && Data[end] != 0 && end - p <= 32768) ++end;
        if (end == Data.Length || end - p > 32768) throw new InvalidDataException("文件字符串未结束。");
        return Encoding.ASCII.GetString(Data, p, end - p);
    }
    bool Match(int p, byte[] b, byte[] mask)
    {
        if (p < 0 || (long)p + b.Length > Data.Length) return false;
        for (int i = 0; i < b.Length; ++i) if (mask[i] != 0 && Data[p + i] != b[i]) return false;
        return true;
    }
    bool Prefix(int rva, byte[] b)
    {
        int p = Offset(rva); Bounds(p, b.Length);
        for (int i = 0; i < b.Length; ++i) if (Data[p + i] != b[i]) return false;
        return true;
    }
    public Compatibility CheckGame(List<Pattern> patterns)
    {
        var result = new Compatibility();
        if (!IsX86)
        {
            result.Warnings.Add("游戏程序不再是已知的 32 位架构。继续会安装完整补丁，其中的 32 位文字 DLL 可能无法加载或导致游戏启动失败。");
            return result;
        }
        var imports = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        bool xinput = false;
        int importRva = I(directories + 8);
        if (importRva == 0)
        {
            result.Warnings.Add("游戏没有可识别的导入表。继续会安装完整补丁，但文字模块可能无法加载或生效。");
            return result;
        }
        int d = Offset(importRva);
        for (; I(d + 12) != 0; d += 20)
        {
            string module = CString(I(d + 12));
            if (module.Equals("xinput9_1_0.dll", StringComparison.OrdinalIgnoreCase)) xinput = true;
            int names = I(d); if (names == 0) continue;
            int p = Offset(names);
            for (; I(p) != 0; p += 4) if (I(p) > 0) imports.Add(CString(I(p) + 2));
        }
        if (!xinput)
        {
            result.Warnings.Add("游戏的文字模块加载入口已变化。继续会安装完整补丁，但中文字体和排版模块可能无法加载或生效。");
            return result;
        }
        foreach (string name in new[] { "LoadStringA", "CreateFontA", "DrawTextA", "DrawTextExA", "TextOutA", "GetTextExtentPoint32A", "MessageBoxA" })
            if (!imports.Contains(name)) result.Warnings.Add("文字接口已变化：" + name + "。完整补丁的文字适配可能无法初始化。");
        int? commonTarget = null;
        foreach (var pattern in patterns)
        {
            var hits = new List<int>();
            foreach (var s in sections)
            {
                if ((s.Flags & 0x20000000) == 0) continue;
                int length = Math.Min(s.Size, s.Virtual);
                for (int i = 0; i <= length - pattern.Bytes.Length; ++i)
                    if (Match(s.Raw + i, pattern.Bytes, pattern.Mask)) hits.Add(s.Rva + i);
            }
            if (hits.Count != pattern.Count)
            {
                result.Warnings.Add((pattern.Call < 0 ? "菜单排版" : "人物立绘查找") + "结构已变化（" + pattern.Name + "），可能出现文字错位、缺图或汉化失效。");
                continue;
            }
            if (pattern.Call < 0) continue;
            foreach (int hit in hits)
            {
                try
                {
                    int call = hit + pattern.Call, p = Offset(call);
                    if (Data[p] != 0xe8) throw new InvalidDataException();
                    int target = call + 5 + I(p + 1);
                    p = Offset(target); if (Data[p] == 0xe9) target += 5 + I(p + 1);
                    byte[] original = { 0x0f, 0xb6, 0xc1, 0x83, 0xf8, 0x08 };
                    byte[] legacy = { 0x52, 0x0f, 0xb6, 0xc1, 0x83, 0xf8, 0x08, 0x77, 0x0d, 0xe8, 0, 0, 0, 0, 0x5a, 0xc1, 0xe0, 0x03, 0x8d, 0x44, 0x02, 0x0a, 0x5a, 0xc3 };
                    bool known = Prefix(target, original);
                    if (!known && Prefix(target, legacy))
                    {
                        known = true;
                        string[] names = { "Thrash", "Axle", "Bose", "Cydney", "Jon", "Pearl", "Rhonda", "Jim", "Mike" };
                        for (int n = 0; n < names.Length; ++n) if (CString(target + legacy.Length + n * 8) != names[n]) known = false;
                    }
                    if (!known || (commonTarget.HasValue && commonTarget.Value != target)) throw new InvalidDataException();
                    commonTarget = target;
                }
                catch (InvalidDataException)
                {
                    result.Warnings.Add("人物立绘调用目标已变化（" + pattern.Name + "），完整文字模块可能无法初始化，角色背景也可能无法正确显示。");
                }
            }
        }
        return result;
    }
    public Dictionary<string, TextEntry> Strings()
    {
        var result = new Dictionary<string, TextEntry>();
        int rva = I(directories + 16);
        if (rva == 0) throw new InvalidDataException("未找到语言资源。");
        int root = Offset(rva);
        ReadTree(root, 0, 0, 0, result);
        if (result.Count == 0) throw new InvalidDataException("未找到 RT_STRING 文本资源。");
        return result;
    }
    void ReadTree(int root, int relative, int level, int block, Dictionary<string, TextEntry> result)
    {
        int p = checked(root + relative), count = U16(p + 12) + U16(p + 14);
        for (int i = 0; i < count; ++i)
        {
            int at = p + 16 + i * 8, id = I(at), child = I(at + 4);
            if (id < 0 || (level == 0 && id != 6)) continue;
            if (level < 2)
            {
                if (child >= 0) throw new InvalidDataException("语言资源目录层级不完整。");
                ReadTree(root, child & 0x7fffffff, level + 1, level == 1 ? id : block, result);
            }
            else
            {
                if (child < 0 || block < 1 || block > 4096 || id > 65535) throw new InvalidDataException("语言资源编号无效。");
                int record = checked(root + child), start = Offset(I(record)), size = I(record + 4);
                Bounds(start, size); int cursor = start;
                for (int n = 0; n < 16; ++n)
                {
                    int bytes = U16(cursor) * 2; cursor += 2;
                    if ((long)cursor + bytes > (long)start + size) throw new InvalidDataException("文本资源被截断。");
                    string value = Encoding.Unicode.GetString(Data, cursor, bytes); cursor += bytes;
                    var entry = new TextEntry { Id = (block - 1) * 16 + n, Language = id, Before = value, After = value };
                    result.Add(entry.Key, entry);
                }
            }
        }
    }
}

internal static class TextResources
{
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern IntPtr BeginUpdateResourceW(string file, bool deleteExisting);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool UpdateResourceW(IntPtr handle, IntPtr type, IntPtr name, ushort language, byte[] data, uint size);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool EndUpdateResourceW(IntPtr handle, bool discard);

    public static byte[] Rewrite(byte[] before, Dictionary<string, TextEntry> entries)
    {
        var groups = new Dictionary<string, List<TextEntry>>();
        var dirty = new HashSet<string>();
        foreach (var entry in entries.Values)
        {
            string key = entry.Language + ":" + (entry.Id / 16 + 1);
            if (!groups.ContainsKey(key)) groups[key] = new List<TextEntry>();
            groups[key].Add(entry);
            if (entry.Before != entry.After) dirty.Add(key);
        }
        if (dirty.Count == 0) return before;
        string temporary = Path.Combine(Path.GetTempPath(), "rrzh-resource-" + Guid.NewGuid().ToString("N") + ".dll");
        try
        {
            File.WriteAllBytes(temporary, before);
            IntPtr handle = BeginUpdateResourceW(temporary, false);
            if (handle == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error());
            try
            {
                foreach (string key in dirty)
                {
                    var list = groups[key]; list.Sort((a, b) => a.Id.CompareTo(b.Id));
                    if (list.Count != 16) throw new InvalidDataException("文本资源块不完整。");
                    using (var stream = new MemoryStream())
                    using (var writer = new BinaryWriter(stream, Encoding.Unicode))
                    {
                        foreach (var entry in list)
                        {
                            byte[] value = Encoding.Unicode.GetBytes(entry.After);
                            if (value.Length / 2 > 65535) throw new InvalidDataException("文本过长。");
                            writer.Write((ushort)(value.Length / 2)); writer.Write(value);
                        }
                        byte[] bytes = stream.ToArray();
                        if (!UpdateResourceW(handle, new IntPtr(6), new IntPtr(list[0].Id / 16 + 1), (ushort)list[0].Language, bytes, (uint)bytes.Length))
                            throw new Win32Exception(Marshal.GetLastWin32Error());
                    }
                }
            }
            catch { EndUpdateResourceW(handle, true); throw; }
            if (!EndUpdateResourceW(handle, false)) throw new Win32Exception(Marshal.GetLastWin32Error());
            byte[] after = File.ReadAllBytes(temporary);
            var actual = new GameImage(after).Strings();
            foreach (var entry in entries.Values) if (!actual.ContainsKey(entry.Key) || actual[entry.Key].Before != entry.After)
                throw new InvalidDataException("文本资源写入核对失败。");
            return after;
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }
    public static void CheckBudget(Dictionary<string, TextEntry> entries)
    {
        var encoding = Encoding.GetEncoding(936, EncoderFallback.ExceptionFallback, DecoderFallback.ExceptionFallback);
        foreach (var entry in entries.Values)
        {
            if (entry.Id != 0) continue;
            string[] parts = entry.After.Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
            int budget, count;
            if (parts.Length != 2 || !int.TryParse(parts[0], out budget) || !int.TryParse(parts[1], out count) || count < 1 || count > 65535)
                throw new InvalidDataException("游戏文本表的容量字段不兼容。");
            long used = 0;
            for (int i = 1; i <= count; ++i)
            {
                TextEntry item;
                if (entries.TryGetValue(entry.Language + ":" + i, out item)) used += encoding.GetByteCount(item.After) + 1;
                else ++used;
            }
            if (used > budget) throw new InvalidDataException("中文文本超过本版本分配的容量，未安装。");
        }
    }
}
