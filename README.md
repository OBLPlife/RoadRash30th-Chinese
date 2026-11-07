# 暴力摩托：30 周年纪念版 简体中文补丁

纯汉化补丁，适用于 Steam build **26105967** 的英文原版。

内容包括中文菜单、设置、角色对白、车辆与赛道介绍、比赛提示，以及中文字体显示、长文本排版和角色背景图片查找修正。制作人员姓名、公司名、乐队名、标准按键名等保留原文。

本包不包含高清渲染模块、宽屏适配、分辨率菜单或帧率修改。

## 安装

1. 在 Steam 将游戏语言设为**英语**，退出游戏。
2. 将 `RoadRash_ZH_CN_Setup.exe` 放到游戏根目录，与 `RoadRash95.exe` 放在一起。
3. 双击补丁。出现“汉化完成”后，从 Steam 正常启动游戏。

用户只需要这一个 EXE，不需要 Python、开发工具或额外的补丁 DLL。安装器使用 Windows .NET Framework 4.x；Windows 10/11 通常已提供该运行环境。汉化画面此前在简体中文 Windows 环境检查，其他系统语言环境尚未验证。

安装器只修改 `RoadRash95.exe` 和 `TEXT/ENU.DLL`，并在 `中文补丁_原版备份` 保存原文件，不修改存档。重复运行会提示已安装。文件版本不匹配会停止，不覆盖其他版本或其他改版。

如果提示没有写入权限，以管理员身份运行补丁。安装结果写入同目录的 `RoadRash_ZH_CN_Setup.log`。

## 恢复英文原版

退出游戏。在游戏目录打开 PowerShell，运行：

```powershell
.\RoadRash_ZH_CN_Setup.exe /restore
```

也可以将 `中文补丁_原版备份` 中的 `RoadRash95.exe` 和 `TEXT/ENU.DLL` 按原路径复制回游戏目录。

## 从源码构建

需要 Windows、Python 3.10 或更高版本，以及 .NET Framework 4.x 自带的 C# 编译器。不需要第三方 Python 包。准备自己的英文原版游戏文件；构建程序只读取该目录。

```powershell
python build.py --original-dir "D:\Games\RoadRash"
```

如果游戏已经装过汉化，可将 `--original-dir` 指向包含上述两个原版文件的备份目录。

输出为 `dist/RoadRash_ZH_CN_Setup.exe`。安装器内嵌二进制差分，根据用户已有的原版文件重建汉化文件，不打包完整游戏 EXE、原版语言库或游戏素材。

```powershell
python test_installer.py --original-dir "D:\Games\RoadRash"
```

测试仅在临时目录复制两个原版文件，执行安装、重复安装、恢复、不兼容版本拒绝及写入失败回滚，不启动游戏、不修改实际安装目录。

## 文件

- `Installer.cs`：单文件安装器，自动定位自身所在目录。
- `localize.py`：中文字体、内置文字、语言资源和角色背景查找补丁。
- `translations.json`：1166 条替换译文；未改动的字符串从用户原版文件读取。
- `build.py`：校验原版、生成纯汉化差分、编译 EXE。
- `test_installer.py`：安装器文件操作测试。

提交 GitHub 时提交这些源码；`build/` 和 `dist/` 已在 `.gitignore` 中。安装 EXE 可作为 Release 附件单独上传。请勿将构建中间文件里的完整游戏文件加入仓库。

本项目新增代码采用 MIT 许可证。许可证不涵盖原版游戏程序、素材和商标。
