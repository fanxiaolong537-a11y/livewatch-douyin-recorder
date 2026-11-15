# LiveWatch 直播观察助手

中文本地直播录制桌面应用，工程版本 **v0.1.0 预发布**，对应 V1.0 首版需求。目标平台 Windows 10/11 x64。仅用于本人或获得授权的直播内容。

**交付状态：源码、测试、Windows 构建脚本已提供；尚未在 Windows 构建或发布 EXE。GitHub 目标仓库不可访问，未推送。真实抖音直播解析及录制未验证。请不要把本源码压缩包当作已验收的 Windows 便携版。**

## 已实现

- 中文 Flet 四页界面：直播监控、录像管理、数据统计、软件设置；浅色绿色主题，窗口缩放与最小尺寸。
- 抖音网页直播间、分享短链、主播主页输入清洗，批量添加；URL 去重，解析后的主播标识二次去重。
- 独立异步监控、默认120秒间隔、全局请求错峰；单项/全部启停、SQLite 保存任务、重启恢复。
- StreamGet 4.0.10 适配层。网络异常不视为下播，明确风控/403/429后暂停；不处理付费、登录或验证码绕过。
- FFmpeg 流复制到 TS；30/60分钟分段，默认最多3路并发，可配置1–20路。分段在关键帧边界发生，不保证精确秒数。
- FFmpeg `q` 正常退出，超时后升级终止；断流重新解析并指数退避5–300秒，重连使用新文件，不覆盖旧录像。
- FFprobe 检测时长、轨道、编码、分辨率、帧率；可选 TS→MP4 无损封装、时长/音轨和数据包扫描校验。校验成功才允许删 TS。
- 低于5GB自动安全停止，不会在磁盘仍不足时自动重启；提醒在主播状态详情中显示。
- 独立会话 metadata.json、分段与重连事件；本地记录检索、播放首段、打开目录、删除记录；实际视频删除二次确认。
- Windows 托盘菜单、关闭选择、用户主动设置开机启动代码；尚待 Windows 验证。源码模式不提供自启动设置。
- 分离应用/解析/录制日志，滚动日志与脱敏诊断导出；不会将凭据、直播流签名 URL 写入 metadata。
- Windows PyInstaller 文件夹式打包、EXE 自检和实际 GUI 挂载冒烟测试、ZIP/SHA256、按标签发布 Actions。

## 运行源码（Windows）

1. 安装 Python 3.11 x64（勾选 PATH）、Node.js 22 LTS。
2. 从 https://ffmpeg.org/download.html 中的 Windows 构建入口获得 FFmpeg 和 FFprobe。把 `ffmpeg.exe`、`ffprobe.exe`、`node.exe` 放入项目根目录 `tools`，或分别安装到 PATH。
3. PowerShell 在项目目录执行：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

启动后进入「软件设置」检查三个依赖。缺少依赖时界面仍能启动，但不能录制。无需服务器、账号注册或收费 API。Windows 默认数据目录 `%LOCALAPPDATA%\LiveWatch`，不是源码目录。可用 `LIVEWATCH_HOME` 为测试指定隔离目录。

## 使用

1. 设置录像保存目录（确保有5GB以上空闲）。默认保存在应用数据目录的 Recordings 下。
2. 点击「添加主播 / 批量添加」，粘贴链接，确认拥有录制授权，再添加。
3. 后台获取主播信息。未开播持续等待；开播且有有效流则开始录制。解析失败显示原因并退避，受限制则停止任务等待手动重试。
4. 点击「停止」结束当前任务并正常保存。正在转封装时等待完成，不要强制关机。
5. 在「录像管理」播放首段，或打开目录选择其他分段。TS/MP4 能否直接播放取决于系统播放器和源视频编码。
6. 关闭窗口时可选择继续后台（托盘可用时）或保存退出。电脑关机、休眠、进程退出后不能继续录制。
7. 「软件设置→导出脱敏诊断日志」生成诊断 ZIP。它不包含数据库、Cookie、原始视频或完整直播链接。

画质选项是请求档位，不等于分辨率保证。实际分辨率/帧率见 metadata.json。主播重名不会合并文件，因为每次会话有独立随机 ID。

文件结构：

```text
Recordings/主播名称/2026-11-14/173000_会话ID/
  主播名称_20261114_173000_r001_0000.ts
  主播名称_20261114_173000_r001_0001.ts
  主播名称_20261114_173000_r002_0000.ts
  metadata.json
```

为避免 metadata 覆盖和主播同名冲突，较原需求额外增加了唯一会话子目录。`r002` 表示第二次连接。同一主播不同日期会分开目录；跨午夜的一场会话仍归入开始日期。

## Windows 构建

必须在 Windows 上构建，Linux 不能生成并验证 Windows EXE。

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

该命令需要已安装的 Python 3.11、FFmpeg、FFprobe、Node.js，以及访问 PyPI/GitHub 的网络。`ExecutionPolicy Bypass` 仅作用于本次进程，不修改系统策略。输出：

```text
dist/LiveWatch/LiveWatch.exe
dist/LiveWatch/_internal/...
dist/LiveWatch/tools/安装依赖.txt
dist/LiveWatch-Windows-x64.zip
dist/SHA256SUMS.txt
```

分发版本包含 Python 和 GUI 运行时，无需用户安装 Python。**FFmpeg/FFprobe/Node 不随包分发**：按依赖向导安装到 PATH 或放进 `LiveWatch/tools`。EXE 不具有代码签名，首次下载可能触发 Windows SmartScreen；不要绕过未知来源安全警告，应核验发布来源和 SHA256。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe main.py --self-test --report smoke.json
```

测试仅使用 lavfi 自行生成的320×180画面和正弦音频、本地 HTTP 流与可控解析替身。没有录制或上传其他主播内容。完整证据见 `docs/TEST_REPORT.md` 与 `docs/test-results.xml`。

授权平台测试（必须是你有权录制的链接）：

```powershell
.\.venv\Scripts\python.exe scripts\platform_check.py "https://live.douyin.com/你的直播间" --authorized --seconds 15
```

这一步会实际联网、生成录像与 metadata，但不上传。没有有效授权直播链接时不得填随机主播替代测试。

## GitHub 提交与发布

目前连接账号 `fanxiaolong537-a11y`；目标仓库读取404，可访问仓库列表为空；连接工具没有创建仓库功能，CLI未登录。**没有远程提交、Actions运行、Release或EXE下载链接。**

请在 GitHub 创建并向连接授权私有仓库 `livewatch-douyin-recorder`。不要改为公开，不要覆盖其他仓库。连接恢复后可从随源码提供的 `LiveWatch-history.bundle` 恢复 Git 提交；或在本机已登录的 Git CLI 推送：

```powershell
git clone LiveWatch-history.bundle LiveWatch-git
cd LiveWatch-git
git remote remove origin
git remote add origin https://github.com/fanxiaolong537-a11y/livewatch-douyin-recorder.git
git push -u origin main
git push origin v0.1.0
```

main 推送触发测试和构建；标签触发通过构建后的预发布 Release。仓库权限需允许 Actions 运行及 `contents: write` 发布。私有仓库产物和 Release 需登录相应账号下载。包内不包含测试生成录像。

## 架构与源码目录

见 `docs/TREE.txt`。主要调用链：

`Flet UI → SQLite Store / asyncio Monitor → StreamGet Resolver → RecordingSession → FFmpeg → FFprobe / MP4 Remux → metadata.json`。

GUI 和后台在异步事件循环中协调；网络请求、录制子进程和视频检测不阻塞 UI。托盘使用单独线程，把操作调度回页面事件循环。数据库访问使用锁与参数化 SQL。当前单机单用户，不支持同时启动多个实例。

## 已知限制

- 真实抖音平台未验证；短链/主页支持依赖 StreamGet，接口变更、地区、网络、风控均可能影响解析；没有声称当前所有链接都可录。
- 目前只做无损转封装，不自动重新编码不兼容流；失败保留 TS，在日志记录原因。全文件包扫描不等于逐帧解码无损证明。
- 分段长度受源关键帧间隔影响；断线期间内容无法找回。新连接在同一会话内独立分段。
- 源码导入和控件构造通过，不等于已完成 Windows 窗口、托盘、高DPI或自启动实机验收。
- 退出时转封装大文件可能需要等待。转封装子进程默认120秒超时，超时保留 TS；长视频后续可单独转换。
- 重启会恢复启用的监控任务；崩溃遗留记录标记“异常中断”，不自动修复残片，也不伪装仍在录制。
- 记录删除后不再计入统计；移动外部视频后记录不会自动追踪路径。
- 未开发自动转码、弹幕、在线人数、AI分析；不展示推测数据。

## V2 方向

先补齐授权真实平台回归、Windows用户验收、签名和可合规分发依赖；再按 metadata schema 增加独立的 Whisper/SRT、逐秒话术、片段标注和报告插件。不要让 AI 模块影响录制进程的稳定性。

## 开源许可

Apache-2.0。上游版本、具体复用及修改见 `docs/UPSTREAM_AUDIT.md`；第三方许可见 `THIRD_PARTY_NOTICES.md` 与 `licenses/`。
