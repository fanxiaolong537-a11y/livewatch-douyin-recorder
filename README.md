# LiveWatch 直播观察助手 v0.1.1

已生成 Windows 10/11 x64 文件夹式便携测试版，入口为 **LiveWatch.exe**。无需安装Python、无需注册账号、无需GitHub登录。

**状态：真实Windows PE程序已生成；Linux核心测试和包结构检查通过；尚未完成Windows实机启动验收，不能承诺所有电脑均可正常运行。** 见 `docs/PORTABLE_TEST_REPORT.md`。

## 直接使用

1. 完整解压 `LiveWatch-v0.1.1-Windows-x64.zip`，不要在ZIP预览窗口内直接运行，也不要只复制EXE。
2. 将整个文件夹放到桌面或其他可写目录，双击 `LiveWatch.exe`。
3. 首次启动自动准备录制组件，约105MB，保持联网即可。下载失败可在软件设置点击“一键准备录制组件”重试。
4. 点击“添加主播 / 批量添加”，粘贴自己或获得授权的抖音直播链接。
5. 点击停止后到“录像管理”播放。默认数据保存在软件目录 `data` 下，可在设置中修改录像目录。

网吧使用不需要保存账号密码，也不建议开启自启动。离开前退出程序并复制需要保留的录像；电脑关机或网吧还原系统后无法继续录制。

## 功能

中文监控、录像、统计、设置四页；StreamGet链接解析，FFmpeg低占用流复制、TS分段、3路默认并发、断流刷新地址与退避、低磁盘安全停止、可选MP4转封装、独立会话metadata、日志脱敏、任务持久化、Windows托盘和主动自启动。

网络错误不会当作下播；受平台限制时暂停。实际分辨率以FFprobe检测为准。没有弹幕、在线人数估算或AI分析。真实抖音平台有效性尚待授权直播间验证。

## 包结构

```text
LiveWatch/
  LiveWatch.exe          Windows GUI启动器
  _app/                 应用代码
  _runtime/             内置Windows Python及依赖
  _desktop/             Flet Windows界面运行时
  tools/node.exe        内置Node.js
  licenses/             许可证、上游归属及部分对应源码
  docs/                 测试报告
  源码与构建/            完整项目及启动器源代码
  data/                 首次运行后创建的个人数据目录
```

FFmpeg/FFprobe由软件首次联网自动下载，无需手动安装；该压缩包不分发其二进制。下载来源为Gyan官方固定版本8.1.2，严格核对官网SHA256。用户可以将已自行取得的两个EXE放入tools使用。

## 验证与构建

源码测试：`python -m pip install -r requirements-dev.txt`，`python -m pytest -q`。

新便携路线：安装Zig 0.13.0，按 `scripts/build_portable.py` 获取固定资产并下载Windows wheel，再由 `scripts/assemble_portable.py` 组装。`scripts/launcher.c` 是完整可审阅启动器代码，`scripts/check_portable.py` 验证PE结构与资源。

Windows Actions 已改为便携构建路线，包含原生 Windows GUI 冒烟测试，但本轮没有执行 Actions 或发布 Release。原始 PyInstaller 脚本保留为另一种构建方式。

## 故障

如果双击后退出，查看 `data/startup.log`；窗口能打开时在设置导出脱敏日志。没有Windows实机验证记录时，不将静态检查冒充启动成功。不需要为排错安装Python。

## 已知限制与扩展

Windows桌面行为、托盘、高DPI、自启动尚待实测；不支持自动重编码不兼容MP4的视频，失败保留TS；断线期间无法追回内容；异常关机残片不自动修复。平台接口会受网络和平台调整影响。

V2先补齐Windows真实长稳和授权平台验证，再加Whisper、SRT、逐秒话术、片段标注和复盘报告。详见metadata schema和app/extensions.py。

Apache-2.0；第三方版权与修改记录见THIRD_PARTY_NOTICES.md。原v0.1.0文档保留在docs作为历史记录，不代表当前便携包状态。
