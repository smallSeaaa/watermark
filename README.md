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
python watermark.py 图片路径 --font-size 字体大小 --text-color 文本颜色 --bg-color 背景颜色 --position 位置
```

#### 可用选项：

- `--font-size`：设置水印字体大小（默认值：30）
- `--text-color`：设置水印文本颜色（支持多种格式，默认值：black）
- `--bg-color`：设置水印背景颜色（支持多种格式，默认值：white）
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

2. 使用红色文本和半透明白色背景：

   ```bash
   python watermark.py picture\1.jpg --text-color red --bg-color "(255,255,255,128)"
   ```

3. 将水印放在图片中心：

   ```bash
   python watermark.py picture\1.jpg --position center
   ```

4. 组合多个选项：
   ```bash
   python watermark.py picture --font-size 25 --text-color blue --bg-color "#FFFF0080" --position top-left
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
