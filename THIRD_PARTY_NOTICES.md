# 第三方许可与归属

LiveWatch 自有代码采用 Apache License 2.0。Copyright 2026 LiveWatch contributors。

## StreamCap

Copyright (c) Hmily / StreamCap contributors。项目：https://github.com/ihmily/StreamCap

基线：e1e8dbf1657df58f363e6de7a9ce739c340dba55。Apache-2.0 完整文本见 `licenses/StreamCap-Apache-2.0.txt`。

原样复用：`vendor/streamcap/base.py`、`vendor/streamcap/video/ts.py`。
改编：抖音 resolver 分发方式、Windows 打包脚本。改动说明见 `docs/UPSTREAM_AUDIT.md`。没有使用其名称、图标或素材作为 LiveWatch 品牌。

## StreamGet

Copyright (c) 2025 Hmily。https://github.com/ihmily/streamget
运行时调用 4.0.10，MIT 全文见 `licenses/StreamGet-MIT.txt`。保留原有版权声明。

## Flet、Python 与 Python 依赖

Flet 0.85.3 使用 Apache-2.0；PyInstaller 使用 GPL-2.0-or-later 附带打包例外，生成的应用不会仅因使用 PyInstaller 而需要采用 GPL。Python 运行时按 PSF 许可分发。发行构建会复制已安装 wheel 中 LICENSE/NOTICE/COPYING 文件，并生成 `licenses/inventory.json`。桌面 Flet 原始 archive 中的许可、Flutter 相关资源随客户端一并保留。发布前应检查实际构建包中的许可目录。

Pillow 11.3.0 的元数据声明 MIT-CMU，pystray 使用 LGPL-3.0。发行时保留其许可及源代码获取位置 https://github.com/moses-palmer/pystray ，版本0.19.5；无修改。完整源代码归档与 GPL/LGPL 全文随 licenses 目录附带。Python 动态模块打包，用户可从同版本源代码重新构建和替换，构建步骤与完整源码随本项目提供。不要删除发行包许可证。

## FFmpeg、FFprobe、Node.js

**v0.1.1 便携包内置 Node.js 22.20.0，完整 Node LICENSE 随包附带。FFmpeg/FFprobe 不随包分发，由用户侧程序首次运行从官网自动下载、校验并放置到 tools 目录。**FFmpeg 官方入口 https://ffmpeg.org/download.html ，源代码 https://ffmpeg.org/download.html#get-sources 。Node.js 官方入口 https://nodejs.org/en/download ，源代码 https://github.com/nodejs/node 。

FFmpeg 许可证随编译配置可能为 LGPL/GPL；如未来捆绑，必须先审核具体构建及依赖许可证、提供对应源码与构建配置，不能仅附上通用主页。Node.js 还包含多项第三方声明，未来捆绑时需附带该版本完整 LICENSE。

LyzenX/DouyinLiveRecorder 没有在本项目中复制或分发。ihmily/DouyinLiveRecorder 仅作为参考，没有复制代码。

## v0.1.1 Windows 便携运行时

官方 CPython 3.11.9 embed-amd64 原样随包分发，完整许可位于 `_runtime/LICENSE.txt`。官方 Node.js 22.20.0 win-x64 的 node.exe 未修改，完整许可位于 `licenses/Node-LICENSE.txt`，对应源代码：https://nodejs.org/dist/v22.20.0/node-v22.20.0.tar.xz 。

Flet Windows v0.85.3 原发行包的插件DLL、Flutter资源及NOTICES一并保留；源代码与构建脚本：https://github.com/flet-dev/flet/tree/v0.85.3 。

原生启动器由本项目C源码用Zig 0.13.0交叉编译，其源代码和构建命令随包提供。原PyInstaller构建路线仍保留，但这次便携包没有用PyInstaller，也不宣称在Linux执行了Windows原生测试。

启动器链接的 Zig/MinGW-w64 运行时对应声明见 licenses/Zig-MIT.txt 与 licenses/MinGW-w64-COPYING.txt；编译器版本0.13.0，来源 https://ziglang.org/download/0.13.0/ 。
