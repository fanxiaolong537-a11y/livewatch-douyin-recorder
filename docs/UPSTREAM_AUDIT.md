# 上游审核与实现边界

审核日期：2026-11-14。使用 Git 克隆实际读取以下项目的 README、许可证、目录、依赖和核心模块。这里只复用明确授权的部分。

| 项目 | 固定提交 | 许可证 | 使用方式 |
|---|---|---|---|
| ihmily/StreamCap | `e1e8dbf1657df58f363e6de7a9ce739c340dba55` | Apache-2.0 | 提取 TS 分段构建器与其基类；改编抖音解析分发及 Windows PyInstaller 打包流程 |
| ihmily/streamget | `016a8d6fbef4f5f14c0ec986dc3528c5a22235ab` | MIT | 运行时依赖 PyPI `streamget==4.0.10`；读过 DouyinLiveStream、StreamData、BaseLiveStream |
| ihmily/DouyinLiveRecorder | `add187f8d8c7ff7d231fcbee45cbb4f1ed247d3a` | MIT | 参考 `check_subprocess` 正常退出逻辑；未复制代码 |
| LyzenX/DouyinLiveRecorder | `0e73c346b24ed5ff2b3d2ff7f6b42395ceb8abda` | 未发现独立许可证；README 有科研及非商业限制 | 仅研究 README、requirements、app/record_manager 目录结构；不复制、不依赖 |

## 与 StreamCap 的关系

这是基于 StreamCap 已授权组件做的范围收敛版二次开发，不是整个上游仓库的完整 fork。保留 Flet 0.85.3、StreamGet 和 FFmpeg 技术路线。上游完整界面服务于40多个平台，含多种格式、账户、通知和可选 Web 服务；本项目只提供用户要求的四页抖音桌面 UI，采用 SQLite 的统一任务记录。没有继承全部上游功能或暗示与原作者存在合作。

原样保留 `vendor/streamcap/base.py`、`vendor/streamcap/video/ts.py`；LiveWatch 在 CaptureBuilder 子类中覆盖输入参数，保留 TS 输出分段和流复制逻辑。去除 `-y` 覆盖写入、额外输入协议与同 URL 自动重连，改由 Monitor 重新解析、指数退避。添加选定音视频映射，避免平台附加数据轨道导致封装失败。

StreamGet 的获取接口由独立适配层调用；它内部仍包含上游平台签名与默认请求 Cookie。LiveWatch 不添加用户 Cookie、不存用户凭据、不提供登录/验证码/DRM 绕过；风控或拒绝访问时暂停任务。平台接口有效性必须通过授权直播间单独验证。

## 依赖与构建

- Python 3.11.18 本地实际验证，CI 使用 3.11 x64；GUI Flet 0.85.3。
- requirements.lock.txt 固定 Python 3.11 下实际安装的所有间接依赖版本；其中 Windows 平台专属依赖只做固定，待 Windows CI 验证。
- StreamGet 4.0.10 需要 Node.js 执行抖音解析使用的 JS，打包时保留其 JS 资源。
- Actions 按已查询到的 Git 提交锁定；Node CI 固定 22.20.0，FFmpeg CI 使用 Chocolatey 7.1.1（已确认下载包存在）。它们仅用于测试，不进入发行 ZIP。
- 打包从官方 Flet release v0.85.3 下载桌面客户端。构建复制 Python wheel 许可文本和 Flet archive 原始资源至发行包。
- 首轮在 Python 3.12 上生成锁文件导致 Deprecated 3.0.1 不兼容 3.11，已在 3.11 环境重新解析并锁定 Deprecated 1.3.1。

## 尚未验证

Windows EXE 构建、实际桌面渲染、托盘、注册表自启动及真实抖音兼容性均不得由 Python 单元测试推断为已通过。详见 TEST_REPORT.md。
