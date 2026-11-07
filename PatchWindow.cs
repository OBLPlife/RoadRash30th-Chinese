// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
using System;
using System.Drawing;
using System.Windows.Forms;

internal sealed class PatchResult
{
    public readonly bool Success;
    public readonly string Message;
    public PatchResult(bool success, string message) { Success = success; Message = message; }
}

internal sealed class PatchWindow : Form
{
    readonly Func<bool, PatchResult> execute;
    readonly Button install = new Button(), restore = new Button();

    public PatchWindow(string title, Func<bool, PatchResult> action)
    {
        execute = action;
        Text = title;
        Font = new Font("Microsoft YaHei UI", 10F);
        AutoScaleDimensions = new SizeF(96F, 96F);
        AutoScaleMode = AutoScaleMode.Dpi;
        ClientSize = new Size(380, 84);
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false; MinimizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;
        install.Name = "InstallButton"; install.Text = "安装";
        install.SetBounds(60, 22, 120, 40);
        restore.Name = "RestoreButton"; restore.Text = "还原";
        restore.SetBounds(200, 22, 120, 40);
        Controls.Add(install); Controls.Add(restore);
        install.Click += delegate { Run(false); };
        restore.Click += delegate { Run(true); };
    }
    void Run(bool restoring)
    {
        PatchResult result;
        install.Enabled = restore.Enabled = false;
        UseWaitCursor = true;
        try { result = execute(restoring); }
        finally { install.Enabled = restore.Enabled = true; UseWaitCursor = false; }
        MessageBox.Show(this, result.Message, Text, MessageBoxButtons.OK,
                        result.Success ? MessageBoxIcon.Information : MessageBoxIcon.Error);
    }
}
