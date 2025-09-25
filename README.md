# 图片日期水印工具

一个命令行工具，用于为图片添加基于拍摄日期（EXIF 信息）的水印。

## 功能特点

- 从图片的 EXIF 信息中提取拍摄日期
- 如无 EXIF 信息，使用文件修改时间作为备选
- 将日期水印（年月日格式）添加到图片右下角
- 自动创建输出目录并保存带水印的图片
- 支持处理单个图片文件或整个目录下的所有图片

## 安装说明

1. 确保已安装 Python 3.6 或更高版本

2. 安装所需依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本用法

处理单个图片文件：

```bash
python watermark.py 图片文件路径
```

处理整个目录下的所有图片：

```bash
python watermark.py 目录路径
```

### 高级选项

程序提供了多个可选参数来自定义水印效果：

```bash
python watermark.py 图片路径 --font-size 字体大小 --text-color 文本颜色 --position 位置
```

#### 可用选项：

- `--font-size`：设置水印字体大小（默认值：30）
- `--text-color`：设置水印文本颜色（支持多种格式，默认值：black）
- `--position`：设置水印位置（可选值：top-left、top-right、bottom-left、bottom-right、center、top、bottom、left、right，默认值：bottom-right）

#### 颜色格式：

颜色参数支持以下几种格式：

1. 预定义颜色名称：`black`、`white`、`red`、`green`、`blue`、`yellow`、`cyan`、`magenta`
2. 十六进制格式：`#RRGGBB` 或 `#RRGGBBAA`（例如：`#FF0000` 表示红色）
3. RGB/RGBA 元组格式：`(r,g,b)` 或 `(r,g,b,a)`（例如：`(255,0,0)` 表示红色）

### 示例

1. 使用 40 号字体大小：

   ```bash
   python watermark.py picture\1.jpg --font-size 40
   ```

2. 使用红色文本：

   ```bash
   python watermark.py picture\1.jpg --text-color red
   ```

3. 将水印放在图片中心：

   ```bash
   python watermark.py picture\1.jpg --position center
   ```

4. 组合多个选项：
   ```bash
   python watermark.py picture --font-size 25 --text-color blue --position top-left
   ```

## 输出说明

- 程序会在原图片所在目录下创建一个名为`原目录名_watermark`的子目录
- 处理后的图片将保存在该目录中，文件名格式为`watermarked_原文件名`

## 示例

假设你有一个包含图片的目录 `picture`：

```bash
python watermark.py picture
```

这将在 `picture` 目录下创建 `picture_watermark` 子目录，并将所有处理后的图片保存在其中。

## GUI 版本使用说明

除了命令行工具外，项目还提供了图形界面版本的水印工具 `watermark_gui.py`，让您可以通过可视化界面轻松添加水印。

### 功能特点

- 支持单张图片或批量导入图片文件
- 支持选择整个文件夹中的图片
- 图形化设置水印参数（字体大小、颜色、位置、透明度等）
- 设置输出文件夹和导出格式（JPEG/PNG）
- 自定义输出文件命名规则（保留原名、添加前缀/后缀）
- JPEG质量调节（0-100范围滑块控制）
- 图片尺寸调整功能（原始尺寸、等比例缩放、调整宽度、调整高度）
- 显示处理进度和结果统计
- 水印类型选择：支持使用拍摄日期或自定义文本作为水印
- 自定义水印文本：用户可以输入任意文字作为水印内容
- 水印透明度调节：0表示完全不透明，100表示完全透明（初始值为0）

### 使用方法

运行 GUI 版本：

```bash
python watermark_gui.py
```

### 界面说明

1. **图片导入区域**：

   - 点击"导入图片"按钮选择单个或多个图片
   - 点击"导入文件夹"按钮选择包含图片的文件夹
   - 点击"清空列表"按钮移除所有已导入的图片

2. **水印设置区域**：

   - 通过滑块设置字体大小
   - 选择水印位置（支持 9 种位置选项）
   - 选择文本颜色
   - 通过滑块设置水印透明度（0表示完全不透明，100表示完全透明）

3. **导出设置区域**：

   - 选择输出文件夹
   - 选择输出格式（JPEG 或 PNG）
   - 设置JPEG质量（0-100范围）
   - 设置图片尺寸调整方式（原始尺寸、等比例缩放、调整宽度、调整高度）
   - 设置文件命名规则（保留原名、添加前缀、添加后缀）

4. **已导入图片区域**：

   - 显示已导入图片的缩略图和文件路径
   - 可以单独删除不需要处理的图片

5. **处理控制区域**：
   - 点击"开始处理"按钮批量处理所有图片
   - 处理过程中显示进度条
   - 处理完成后显示成功和失败的统计信息
   - 可选择打开输出文件夹查看结果

### 注意事项

- 为防止覆盖原图，程序默认禁止导出到原文件夹
- 程序会自动检测图片的 EXIF 信息获取拍摄日期
- 如无 EXIF 信息，将使用文件修改时间作为水印日期
- 支持直接将图片拖放到程序窗口中进行导入
  - 拖放时光标会显示为允许拖放的手型
  - 支持同时拖拽多个图片文件

### 系统要求

- Windows 或 macOS 操作系统
- Python 3.6 或更高版本
- 已安装的依赖库（见 requirements.txt）

## 依赖说明

项目使用以下主要依赖库：

- **Pillow**：用于图像处理和水印添加
- **exifread**：用于读取图片的 EXIF 信息
- **tkinter**：Python 标准 GUI 库（大多数 Python 安装已包含）
- **tkinterdnd2**：提供拖放功能支持

安装所有依赖：

```bash
pip install -r requirements.txt
```
