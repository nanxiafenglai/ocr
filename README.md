# 验证码识别系统

一个基于Python的验证码识别系统，支持文字类和计算类验证码的识别，提供命令行工具和RESTful API服务。

## 项目概述

本项目使用ddddocr模块实现验证码识别功能，能够处理以下类型的验证码：

- **文字类验证码**：识别图片中的文字内容
- **计算类验证码**：识别并计算图片中的数学表达式（如"1+2=?"）

项目提供两种使用方式：

1. **命令行工具**：用于本地识别验证码图片
2. **RESTful API**：提供HTTP接口，支持上传图片、URL图片和Base64编码图片的识别

## 功能特点

- 支持多种类型验证码的识别
- 提供图像预处理功能，提高识别准确率
- 模块化设计，易于扩展
- 提供命令行和API两种使用方式
- 详细的错误处理和日志记录

## 安装指南

### 系统要求

- Python 3.6+
- pip 包管理器

### 安装步骤

1. 克隆项目仓库：

```bash
git clone https://github.com/yourusername/captcha-recognizer.git
cd captcha-recognizer
```

2. 安装依赖项：

```bash
pip install -r requirements.txt
```

## 使用方法

### 命令行工具

命令行工具提供了一个简单的界面，用于识别本地验证码图片：

```bash
python main.py [图片路径] [选项]
```

#### 基本示例

识别文字类验证码：

```bash
python main.py examples/text_captcha.png --type text
```

识别计算类验证码：

```bash
python main.py examples/text_captcha.png --type calculation
```

#### 可用选项

| 选项 | 描述 |
|------|------|
| `--type`, `-t` | 验证码类型，可选值：`text`（默认）或 `calculation` |
| `--preprocess`, `-p` | 是否预处理图像 |
| `--grayscale`, `-g` | 转换为灰度图像 |
| `--contrast`, `-c` | 对比度增强因子（默认：2.0） |
| `--sharpness`, `-s` | 锐度增强因子（默认：1.5） |
| `--noise`, `-n` | 去噪方法，可选值：`median`（默认）、`gaussian`或`none` |
| `--threshold` | 二值化阈值（0-255），不设置则不进行二值化 |
| `--return-expression` | 返回表达式而不是计算结果（仅适用于计算类验证码） |
| `--as-float` | 将计算结果作为浮点数返回（仅适用于计算类验证码） |

### API服务

API服务提供了HTTP接口，用于通过网络识别验证码：

#### 启动API服务

```bash
python flask_api.py
```

默认情况下，API服务将在 http://localhost:5000 上运行。

#### API端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/recognize/upload` | POST | 通过文件上传识别验证码 |
| `/api/recognize/url` | POST | 通过URL识别验证码 |
| `/api/recognize/base64` | POST | 通过Base64编码数据识别验证码 |

#### 请求示例

**1. 文件上传识别**

```bash
curl -X POST -F "file=@examples/text_captcha.png" -F "captcha_type=text" http://localhost:5000/api/recognize/upload
```

**2. URL识别**

```bash
curl -X POST -H "Content-Type: application/json" -d '{"url": "https://example.com/captcha.png", "captcha_type": "text"}' http://localhost:5000/api/recognize/url
```

**3. Base64识别**

```bash
curl -X POST -H "Content-Type: application/json" -d '{"image_data": "BASE64_ENCODED_IMAGE_DATA", "captcha_type": "text"}' http://localhost:5000/api/recognize/base64
```

#### 响应格式

成功响应：

```json
{
  "success": true,
  "result": "识别结果",
  "processing_time": 12.345 // 处理时间（毫秒）
}
```

错误响应：

```json
{
  "success": false,
  "error": "错误信息"
}
```

## 项目结构

```
OCR/
├── captcha_recognizer/       # 核心识别模块
│   ├── __init__.py
│   ├── recognizer.py         # 核心识别类
│   ├── processors/           # 验证码处理器
│   │   ├── __init__.py
│   │   ├── text_processor.py      # 文字验证码处理器
│   │   └── calculation_processor.py  # 计算类验证码处理器
│   └── utils/                # 工具函数
│       ├── __init__.py
│       ├── ddddocr_patch.py  # ddddocr补丁
│       └── image_utils.py    # 图像处理工具
├── examples/                 # 示例验证码图片
│   └── text_captcha.png
├── tests/                    # 测试文件
│   ├── __init__.py
│   └── test_recognizer.py
├── flask_api.py              # Flask API服务
├── main.py                   # 命令行工具
└── requirements.txt          # 项目依赖
```

### 主要模块说明

- **captcha_recognizer/recognizer.py**：核心识别类，提供统一的接口来识别不同类型的验证码
- **captcha_recognizer/processors/**：验证码处理器，包含不同类型验证码的处理逻辑
- **captcha_recognizer/utils/image_utils.py**：图像处理工具，提供图像预处理功能
- **main.py**：命令行工具入口
- **flask_api.py**：API服务入口

## 扩展指南

### 添加新的验证码处理器

1. 在 `captcha_recognizer/processors/` 目录下创建新的处理器文件，如 `new_processor.py`
2. 实现处理器类，必须包含 `process` 方法
3. 在 `captcha_recognizer/recognizer.py` 中注册新的处理器

示例：

```python
# captcha_recognizer/processors/new_processor.py
class NewCaptchaProcessor:
    def __init__(self, ocr_engine):
        self.ocr = ocr_engine

    def process(self, image_data, **kwargs):
        # 实现处理逻辑
        result = self.ocr.classification(image_data)
        # 自定义处理
        return result

# 在 captcha_recognizer/recognizer.py 中注册
from captcha_recognizer.processors.new_processor import NewCaptchaProcessor
self.register_processor('new_type', NewCaptchaProcessor(self.ocr))
```

### 自定义图像预处理

可以在 `captcha_recognizer/utils/image_utils.py` 中添加新的图像预处理函数，然后在处理器中使用。

## 开发规划

项目提供了详细的开发和优化规划文档：

- **[开发路线图](DEVELOPMENT_ROADMAP.md)** - 分阶段的开发计划和时间安排
- **[优化指南](OPTIMIZATION_GUIDE.md)** - 详细的性能和代码优化方案
- **[架构升级计划](ARCHITECTURE_PLAN.md)** - 微服务架构迁移方案

这些文档为项目的长期发展提供了清晰的技术路线图。

## 贡献指南

欢迎为项目做出贡献！请遵循以下步骤：

1. Fork 项目仓库
2. 创建新的分支 (`git checkout -b feature/your-feature`)
3. 提交更改 (`git commit -m 'Add some feature'`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 创建 Pull Request

在开始开发前，建议阅读[开发路线图](DEVELOPMENT_ROADMAP.md)了解项目的发展方向。

## 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。
