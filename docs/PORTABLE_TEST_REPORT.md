# LiveWatch v0.1.1 Windows 便携测试版

## 2026-11-15 GitHub Actions 验收

发布提交 `70a8e1356e963271951c9ddf31a85965f99dae72` 在 GitHub `windows-latest` x64 Runner 使用 Python 3.11.9 完成测试和打包。前一轮有一个测试用系统默认编码读取 UTF-8 的中文 metadata，修正后重跑通过。

| 验收项 | 实际结果 |
| --- | --- |
| pytest | 38 项通过，用时 47.95 秒 |
| 自生成媒体录制 | 验证 FFmpeg 录制、停止保存、FFprobe 检测、TS 转 MP4、三路并发和本地断流续录 |
| 中文及空格路径 | 测试媒体读写和启动自检在 Windows Runner 通过 |
| EXE 启动验证 | 内置运行时导入、依赖检测及真实 Flet 客户端加载四页通过 |
| 便携版发布 | v0.1.1 预发布包含 Windows x64 ZIP 和 SHA256 校验文件 |

[Windows 构建及日志](https://github.com/fanxiaolong537-a11y/livewatch-douyin-recorder/actions/runs/43693033735) · [JUnit 测试报告](https://github.com/fanxiaolong537-a11y/livewatch-douyin-recorder/actions/runs/43693033735/artifacts/14153685753) · [Release](https://github.com/fanxiaolong537-a11y/livewatch-douyin-recorder/releases/tag/v0.1.1)

发布 ZIP 的 SHA256 为 `4084d74fd5738a9668b4c383ea29330a308c637016f77b4a10609eff9defa4b0`。

真实抖音解析与录制仍需本人或获授权的开播链接。Windows 10/11 用户电脑上的托盘、高 DPI、自启动、长时间录制和首次启动时的在线组件下载仍待实测。

## 2026-11-14 本地构建记录

日期：2026-11-14。此版本已经生成真正的 Windows x64 GUI 子系统 PE 启动程序 `LiveWatch.exe`，不再仅交付源码。它是原生 C 启动器＋官方 Windows Python 嵌入式运行时＋Windows wheels＋官方 Flet Windows 客户端的文件夹式分发。

## 已完成验证

- 原有33项录制/断流/持久化测试重新通过。
- 新增组件安全提取、非法二进制拒绝、缺失组件拒绝、重复路径拒绝、便携路径测试。最终共38项通过（38 passed in 34.32s），当前复测Python 3.12 Linux；Windows嵌入式Python为3.11.9。
- 启动器 PE x86-64 架构、GUI 子系统、Python/Flet/Node PE 架构检查通过。
- 85个 Python .pyd 扩展均为 Windows x64；31个运行依赖 wheel 依据 Python 3.11 Windows平台解析。
- Flet 客户端直接依赖的插件 DLL、MSVC DLL及Flutter资源存在性检查通过。
- Python、Flet和Node下载哈希固定；Node哈希与官方SHASUMS256一致。
- 自动准备的 FFmpeg 8.1.2 官方构建 ZIP 已在开发环境下载，并核对官网SHA256；用户侧安装同样严格核对固定哈希。
- 不执行第三方安装脚本、不使用管理员权限、不更改系统PATH、不收集账号密码。

## 尚未通过的验收

**尚未在真实 Windows 10/11 上执行本包。** 尝试使用 Wine 10.0 进行启动验证，但 Wine 在启动任何 Windows 程序前即报 `free(): invalid pointer`；虚拟显示服务也无法在当前环境建立所需socket。因此无法把该尝试标记为 EXE 成功启动或 GUI 测试通过。

Linux源码测试、PE结构和DLL检查均不等价于 Windows 实机运行。托盘、自启动、高DPI、系统播放器和首次下载完整流程仍待Windows实测。真实抖音测试也仍未执行，因为没有用户本人或获授权的直播间。

## 包内容与使用

- `LiveWatch.exe`：真实 Windows x64启动器，负责加载内置Python，无需用户安装Python。
- `_runtime`：官方Python 3.11.9 Windows嵌入式运行时及锁定依赖。3.11.9是该系列最后一个官方Windows嵌入式bugfix分发版本；与之前Linux3.11.18测试环境补丁级不同。
- `_desktop`：Flet 0.85.3 Windows客户端及原有DLL/资源。
- `tools/node.exe`：官方Node.js 22.20.0，随附完整LICENSE。
- 首次运行自动下载约105MiB的FFmpeg/FFprobe；这个包不重新分发FFmpeg二进制。下载失败时在设置页一键重试。
- `data`：运行后在软件目录内创建，含数据库、日志及默认录像目录。程序退出后可复制整个目录带走。
- `源码与构建`：包括所有应用源码、原生启动器代码、许可证和构建脚本，便于后续维护。

## Windows 双击后异常的处理

启动器将后端输出保存至 `data/startup.log`。窗口能打开时可以在软件设置中导出脱敏诊断日志。此版本不要求用户安装开发环境或登录GitHub。没有创建远程仓库或Release，不存在Actions通过记录。
