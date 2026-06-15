# lctz_image-toolkit

版本：0.01

一个基于 PySide6 的桌面图像小工具。当前包含比例计算、图片对比、差异观察和图片合并导出，后续可以继续扩展成更完整的图像处理工具箱。应用窗口名称为 LCTZ Image Toolkit。

## 功能

- 比例计算
  - 默认打开页面
  - 常用比例预设
  - 自定义比例
  - 输入宽度自动计算高度
  - 输入高度自动计算宽度
  - 显示精确比例和最接近的常见比例

- 图片对比
  - 图像 A / 图像 B 独立上传
  - 支持点击选择图片
  - 支持拖拽图片到上传区域
  - 支持 PNG、JPG、JPEG、WEBP、BMP
  - 滑动对比
  - 点击对比
  - 差异高亮
  - 合并预览

- 查看体验
  - 鼠标滚轮缩放
  - 缩放以鼠标位置为中心
  - 左键拖动画布
  - 滑动对比模式下鼠标悬停为十字光标
  - 预览背景色可切换，仅用于观察图片边界
  - 下拉框未展开时不会被滚轮误改

- 合并导出
  - 自动判断横向并排或纵向并列
  - 也可以手动指定方向
  - 导出时保持原图尺寸，不使用预览压缩
  - 尺寸不一致产生的空白区域固定用白色填充
  - 后台导出，避免界面长时间卡死
  - PNG 导出使用 RGB PNG 路径，避免无意义 alpha 通道导致文件过大

## 安装与运行

建议使用 Python 3.11 或更新版本。

```bat
python -m pip install -r requirements.txt
python lctz_image_toolkit.py
```

如果只想运行打包后的程序，普通用户不需要安装 Python。

## Windows 打包

文件夹版启动更快，适合日常使用和分享：

```bat
build_folder.bat
```

输出位置：

```text
dist\lctz_image-toolkit\lctz_image-toolkit.exe
```

单文件版更方便拷贝，但启动会慢一些：

```bat
build_exe.bat
```

输出位置：

```text
dist\lctz_image-toolkit.exe
```

## macOS 打包

macOS 应用通常需要在 macOS 上打包，不能在 Windows 上直接交叉构建出可靠可用的 `.app`。

苹果 Mac 主要分两类芯片：

- Intel：`x86_64`
- Apple Silicon：`arm64`，例如 M1、M2、M3、M4

如果不知道同事的 Mac 是哪种芯片，建议优先用 GitHub Actions 同时构建 `x86_64` 和 `arm64` 两份，或者在一台合适的 Mac 上尝试构建 `universal2`。

本地 macOS 构建：

```bash
chmod +x scripts/build_macos_app.sh
scripts/build_macos_app.sh
```

指定架构：

```bash
scripts/build_macos_app.sh x86_64
scripts/build_macos_app.sh arm64
```

尝试 universal2：

```bash
chmod +x scripts/build_macos_universal2.sh
scripts/build_macos_universal2.sh
```

输出位置通常为：

```text
dist/lctz_image-toolkit.app
dist/lctz_image-toolkit-macos-*.zip
```

注意：脚本使用的是 ad-hoc 签名，不是 Apple Developer ID 正式签名。第一次打开时，macOS 可能提示来自未知开发者。测试阶段可以让同事在 Finder 中右键应用，选择“打开”。

## GitHub Actions 打包 macOS

仓库中提供了：

```text
.github/workflows/build-macos.yml
```

推送 `v*` tag 或在 GitHub Actions 页面手动运行 workflow 后，会分别构建：

- `lctz_image-toolkit-macos-x86_64.zip`
- `lctz_image-toolkit-macos-arm64.zip`

这两个压缩包可以放到 GitHub Releases 里给同事测试。

## 项目结构

```text
lctz_image_toolkit.py 主程序源码
比例计算器.py          中文文件名启动器，方便本地查看
requirements.txt      Python 依赖
build_folder.bat      打包文件夹版
build_exe.bat         打包单文件版
lctz_image-toolkit.spec PyInstaller 打包配置
scripts/              macOS 本地打包脚本
.github/workflows/    GitHub Actions 构建配置
README.md             项目说明
CHANGELOG.md          更新记录
LICENSE               项目许可证
NOTICE                第三方灵感来源说明
```

`build/`、`dist/` 和 `__pycache__/` 属于构建产物，默认不会提交到 Git。

## 发布建议

源码仓库建议只提交源码和文档，不提交 `build/` 和 `dist/`。

如果要给普通用户下载，建议在 GitHub Releases 里上传打包好的文件夹版压缩包，或者上传单文件版 exe。

## 开源许可

本项目使用 MIT License。详见 [LICENSE](LICENSE)。

## 致谢

图片滑动/点击对比体验参考了 rgthree-comfy 的 `Image Comparer (rgthree)` 节点。

rgthree-comfy 使用 MIT License，Copyright (c) 2023 Regis Gaughan, III (rgthree)。

本项目没有复制 rgthree-comfy 的前端代码，而是使用 PySide6 独立实现桌面端交互。详见 [NOTICE](NOTICE)。
