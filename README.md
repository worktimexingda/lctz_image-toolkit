# lctz_image-toolkit

LCTZ Image Toolkit 是一个基于 PySide6 的桌面图像工具箱，提供比例计算、图片对比、差异高亮和合并导出等常用功能。

当前版本：0.01

## 项目说明

这是一个个人学习和实践项目，代码结构、交互细节和跨平台打包流程都还在持续打磨中。欢迎提交 Issue、建议和改进思路，也请各位大佬友善指正。

## 功能特性

- 比例计算：支持常用比例预设、自定义比例，以及宽高联动计算。
- 图片对比：支持图像 A / 图像 B 独立上传，并提供滑动对比、点击对比和差异高亮。
- 预览操作：支持鼠标滚轮缩放、以鼠标位置为中心缩放，以及左键拖动画布。
- 合并导出：支持横向、纵向和自动方向合并，并按原图尺寸导出。
- 桌面体验：基于 PySide6 构建，可在 Windows 和 macOS 上运行或打包。

## 安装与运行

建议使用 Python 3.11 或更新版本。

```bat
python -m pip install -r requirements.txt
python lctz_image_toolkit.py
```

也可以使用中文启动器运行：

```bat
python 比例计算器.py
```

## Windows 打包

构建文件夹版：

```bat
build_folder.bat
```

输出位置：

```text
dist\lctz_image-toolkit\lctz_image-toolkit.exe
```

构建单文件版：

```bat
build_exe.bat
```

输出位置：

```text
dist\lctz_image-toolkit.exe
```

## macOS 打包

macOS 应用建议在 macOS 环境中构建。

```bash
chmod +x scripts/build_macos_app.sh
scripts/build_macos_app.sh
```

指定目标架构：

```bash
scripts/build_macos_app.sh x86_64
scripts/build_macos_app.sh arm64
```

尝试构建 universal2：

```bash
chmod +x scripts/build_macos_universal2.sh
scripts/build_macos_universal2.sh
```

## GitHub Actions

仓库包含自动构建和发布 workflow：

```text
.github/workflows/release.yml
```

推送 `v*` tag 后，会自动构建并发布：

```text
lctz_image-toolkit-windows-x64.exe
lctz_image-toolkit-macos-x86_64.zip
lctz_image-toolkit-macos-arm64.zip
```

## 项目结构

```text
lctz_image_toolkit.py       主程序源码
比例计算器.py                  中文启动器
requirements.txt            Python 依赖
build_folder.bat            Windows 文件夹版构建脚本
build_exe.bat               Windows 单文件版构建脚本
lctz_image-toolkit.spec     PyInstaller 配置
scripts/                    macOS 构建脚本
.github/workflows/          GitHub Actions 配置
CHANGELOG.md                更新记录
LICENSE                     许可证
NOTICE                      第三方灵感来源说明
```

`build/`、`dist/` 和 `__pycache__/` 为本地生成目录，不会提交到 Git。

## 许可证

本项目使用 MIT License。详见 [LICENSE](LICENSE)。

## 致谢

图片滑动/点击对比体验参考了 rgthree-comfy 的 `Image Comparer (rgthree)` 节点。

rgthree-comfy 使用 MIT License，Copyright (c) 2023 Regis Gaughan, III (rgthree)。

本项目没有复制 rgthree-comfy 的前端代码，而是使用 PySide6 独立实现桌面端交互。详见 [NOTICE](NOTICE)。
