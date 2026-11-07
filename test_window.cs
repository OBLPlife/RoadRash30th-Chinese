// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Render the installer's small window offscreen; file operations are covered by test_installer.py.
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Windows.Forms;

internal static class WindowTest
{
    [DllImport("user32.dll")] static extern int GetWindowLong(IntPtr window, int index);
    [DllImport("user32.dll")] static extern int SetWindowLong(IntPtr window, int index, int value);
    static string Hash(string path)
    {
        using (var sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path)));
    }
    [STAThread]
    static int Main(string[] args)
    {
        try
        {
            if (args.Length != 2) throw new ArgumentException("Expected installer path and output PNG");
            string installer = Path.GetFullPath(args[0]), root = Path.GetDirectoryName(installer);
            var before = new Dictionary<string, string>();
            foreach (var path in Directory.GetFiles(root, "*", SearchOption.AllDirectories)) before.Add(path, Hash(path));
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            var assembly = Assembly.LoadFrom(installer);
            var factory = assembly.GetType("Installer").GetMethod("CreateWindow", BindingFlags.NonPublic | BindingFlags.Static);
            using (var window = (Form)factory.Invoke(null, null))
            {
                if (window.Controls.Count != 2 || !(window.Controls[0] is Button) || !(window.Controls[1] is Button) ||
                    window.Controls[0].Text != "安装" || window.Controls[1].Text != "还原")
                    throw new InvalidOperationException("Window must contain only Install and Restore buttons");
                window.StartPosition = FormStartPosition.Manual;
                window.Location = new Point(-30000, -30000);
                window.ShowInTaskbar = false;
                var handle = window.Handle;
                SetWindowLong(handle, -20, GetWindowLong(handle, -20) | 0x08000000); // WS_EX_NOACTIVATE
                window.Show();
                Application.DoEvents();
                if (Directory.GetFiles(root, "*", SearchOption.AllDirectories).Length != before.Count)
                    throw new InvalidOperationException("Opening the window created files");
                foreach (var file in before)
                    if (Hash(file.Key) != file.Value) throw new InvalidOperationException("Opening changed " + file.Key);
                using (var bitmap = new Bitmap(window.Width, window.Height))
                {
                    window.DrawToBitmap(bitmap, new Rectangle(Point.Empty, window.Size));
                    bitmap.Save(args[1], ImageFormat.Png);
                }
            }
            Console.WriteLine("GUI: only Install and Restore buttons; opening does not change files");
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
