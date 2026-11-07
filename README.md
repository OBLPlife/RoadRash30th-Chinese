# 暴力摩托：30 周年纪念版 简体中文补丁

适用于 Steam 英文原版 **build 26105967** 的简体中文补丁。

**分辨率修复补丁请移步：** [RoadRash30th-HD](https://github.com/OBLPlife/RoadRash30th-HD)

## 汉化内容

- 菜单、设置、角色对白、车辆与赛道介绍、比赛提示
- 1166 条文本翻译
- 中文字体显示与长文本排版优化
- 角色背景图片显示修正

人物姓名、公司名、乐队名及标准按键名称保留原文。

## 安装方法

1. 在 Steam 中将游戏语言设为 **英语**，并退出游戏。
2. 将 `RoadRash_ZH_CN_Setup.exe` 放入游戏根目录，与 `RoadRash95.exe` 位于同一目录。
3. 双击运行安装器，出现“汉化完成”后，从 Steam 启动游戏。

安装器会自动将原版文件备份至游戏目录下的 `中文补丁_原版备份` 文件夹。

## 恢复英文原版

退出游戏，在游戏根目录打开 PowerShell，运行：

```powershell
.\RoadRash_ZH_CN_Setup.exe /restore
```

## 从源码构建

构建环境：Windows、Python 3.10+、.NET Framework 4.x 编译器。

准备 Steam 英文原版游戏文件，在源码目录执行：

```powershell
python build.py --original-dir "D:\Games\RoadRash"
```

生成的安装器位于 `dist/RoadRash_ZH_CN_Setup.exe`。

构建完成后可运行安装器测试：

```powershell
python test_installer.py --original-dir "D:\Games\RoadRash"
```

## 项目文件

- `translations.json`：中文翻译文本
- `localize.py`：文字、字体和显示相关的汉化处理
- `Installer.cs`：安装及恢复程序
- `build.py`：生成汉化安装器
- `test_installer.py`：安装器测试
- `app.manifest`：安装器清单

## 许可证

本项目采用 [PolyForm Noncommercial License 1.0.0](LICENSE)，允许非商业使用、修改及分发；未经许可不得用于商业用途或收费倒卖。
