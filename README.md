# 暴力摩托：30 周年纪念版 简体中文补丁

适用于 Steam《暴力摩托：30 周年纪念版》英文原版（build **26105967**）。

**[下载最新版汉化补丁（EXE）](https://github.com/OBLPlife/RoadRash30th-Chinese/releases/latest)** · **[原生分辨率与高清重绘补丁](https://github.com/OBLPlife/RoadRash30th-HD)**

## 安装与还原

**安装汉化**

1. 在 Steam 将游戏语言设为**英语**，退出游戏。
2. 下载 `RoadRash_ZH_CN_Setup.exe`，放进游戏根目录（与 `RoadRash95.exe` 在同一文件夹）。
3. **双击 EXE → 点击「安装」**。出现完成提示后，从 Steam 正常启动游戏。

**恢复英文原版**

退出游戏，再次双击同一个 `RoadRash_ZH_CN_Setup.exe`，点击**「还原」**即可。无需打开 PowerShell 或输入命令。

安装器会在游戏目录的 `中文补丁_原版备份` 文件夹中保存原文件，安装和还原均有结果提示；不会修改游戏存档。遇到不匹配的游戏版本会停止操作，避免覆盖其他版本文件。

如果同时安装了高清补丁，**先安装汉化，再安装高清补丁**；还原时按相反顺序操作。

## 实机截图

| 开场画面 | 游戏模式 |
| :---: | :---: |
| ![中文开场画面](screenshots/title-credits.png) | ![游戏模式界面](screenshots/game-mode.png) |
| 休息室：存档菜单 | 休息室：模式菜单 |
| ![休息室存档菜单](screenshots/restroom-save-menu.png) | ![休息室模式菜单](screenshots/restroom-mode-menu.png) |
| 车手资料 | 车手对白 |
| ![中文车手资料](screenshots/rider-profile.png) | ![中文车手对白](screenshots/rider-dialogue.png) |

## 汉化内容

- **1166 条中文译文**：涵盖游戏菜单、设置、角色对白、车辆与赛道介绍、比赛提示等。
- **中文显示适配**：中文字体、较长文本排版和角色背景图片查找修正。
- 人名、公司名、乐队名及标准按键名称等专有名称保留原文。

## 从源码构建

仅面向需要自行编译的开发者：需要 Windows、Python 3.10 或更高版本，以及 .NET Framework 4.x 自带的 C# 编译器。无需第三方 Python 包。准备自己的英文原版游戏文件；构建程序只读取该目录。

```powershell
python build.py --original-dir "D:\Games\RoadRash"
```

如果游戏已经装过汉化，可将 `--original-dir` 指向包含上述两个原版文件的备份目录。

输出为 `dist/RoadRash_ZH_CN_Setup.exe`。安装器内嵌二进制差分，根据用户已有的原版文件重建汉化文件，不打包完整游戏 EXE、原版语言库或游戏素材。

```powershell
python test_installer.py --original-dir "D:\Games\RoadRash"
```

测试仅在临时目录复制两个原版文件，检查窗口只有安装与还原两个按钮且打开不写入，以及命令行安装、重复安装、恢复、不兼容版本拒绝及写入失败回滚。窗口在离屏状态检查，预览输出为 `build/window.png`；不启动游戏、不修改实际安装目录。

## 文件

- `Installer.cs`：单文件安装器，自动定位自身所在目录。
- `PatchWindow.cs`：只有安装与还原两个按钮的小窗口。
- `localize.py`：中文字体、内置文字、语言资源和角色背景查找补丁。
- `translations.json`：1166 条替换译文；未改动的字符串从用户原版文件读取。
- `build.py`：校验原版、生成纯汉化差分、编译 EXE。
- `test_installer.py`：安装器文件操作测试。
- `test_window.cs`：安装器小窗口与打开不写入检查，由上述 Python 测试自动编译运行。

`build/` 和 `dist/` 已在 `.gitignore` 中；正式安装包在 Releases 发布。不分发完整游戏文件。

本项目新增代码及提供的译文采用 **PolyForm Noncommercial License 1.0.0**，源码公开，可按许可允许的非商业目的使用、修改和分发；许可范围之外的用途需要另行授权。完整条款见 [LICENSE](LICENSE)。本许可不涵盖原版游戏程序、素材和商标。
