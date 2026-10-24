# 🐱 笺启 · 可拆卸个人 AI 学习工作站

一个完全运行在 U 盘里的本地 AI 学习工作站。插上 U 盘即可拥有离线大模型、本地知识库、自动化文档转换和像素风日程管理。

## ✨ 特性

- **🔌 完全插件化**：基于 `modules` 目录，主面板自动读取 `config.json` 并动态生成小猫按钮。加功能只需拖入新文件夹。
- **🧠 本地大模型**：深度集成 Open WebUI 与 Ollama，数据永久保存在 U 盘。
- **📄 自动化转换**：拖拽 PDF/PPTX 即可自动转 Markdown，并利用大模型 API 同步至知识库。
- **🎬 音视频转录**：基于本地 Whisper 引擎，拖入视频自动提取带时间戳的 Markdown 文本。
- **🎨 像素风 UI**：包含换肤面板、自定义颜色、动态粒子特效和可互动的像素小猫。

## 🚀 快速开始

1. 克隆本仓库到你本地的移动硬盘或 U 盘。
2. 安装 Python 依赖：
   `pip install -r requirements.txt`
3. 请确保你已经安装了 [Open WebUI](https://github.com/open-webui/open-webui) 和 [Ollama](https://ollama.com/)。
4. 修改 `modules` 目录下各插件的 `app.py`，填入你自己的 API Key 和知识库 ID。
5. 双击 `双击启动AI助手.bat` 即可运行。

## 🧩 插件结构开发

如果你想自己开发插件，只需在 `modules` 目录下新建一个文件夹，放入 `config.json` 和你的 FastAPI 后端，重启主面板即可自动生成对应按钮。

*注意：本仓库不包含模型文件（GGUF/Whisper），请自行下载。*
<img width="1280" height="800" alt="屏幕截图 2026-10-24 200303" src="https://github.com/user-attachments/assets/899d759f-c598-47d3-b3c5-51b8cdf03395" />
