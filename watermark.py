import os
import sys
import argparse
from PIL import Image, ImageDraw, ImageFont
import exifread
from datetime import datetime
import re


def get_exif_datetime(image_path):
    """
    从图片文件中读取EXIF信息中的拍摄时间
    """
    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f)
            # 尝试获取不同格式的日期时间标签
            datetime_tags = ['EXIF DateTimeOriginal', 'EXIF DateTimeDigitized', 'Image DateTime']
            for tag in datetime_tags:
                if tag in tags:
                    datetime_str = str(tags[tag])
                    # 解析日期时间字符串，通常格式为 'YYYY:MM:DD HH:MM:SS'
                    try:
                        dt = datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
                        return dt.strftime('%Y-%m-%d')  # 返回年月日格式
                    except ValueError:
                        continue
            # 如果没有找到有效的EXIF日期时间，返回None
            return None
    except Exception as e:
        print(f"读取EXIF信息时出错 {image_path}: {e}")
        return None


def parse_color(color_str):
    """
    解析颜色字符串，支持多种格式：
    - 十六进制：#RRGGBB 或 #RRGGBBAA
    - RGB元组：(r,g,b) 或 (r,g,b,a)
    - 预定义颜色名称：如 'black', 'white', 'red' 等
    """
    # 预定义颜色映射
    color_map = {
        'black': (0, 0, 0, 255),
        'white': (255, 255, 255, 255),
        'red': (255, 0, 0, 255),
        'green': (0, 255, 0, 255),
        'blue': (0, 0, 255, 255),
        'yellow': (255, 255, 0, 255),
        'cyan': (0, 255, 255, 255),
        'magenta': (255, 0, 255, 255),
    }

    # 检查是否为预定义颜色
    if color_str.lower() in color_map:
        return color_map[color_str.lower()]

    # 检查是否为十六进制颜色
    hex_pattern = r'^#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?$'
    match = re.match(hex_pattern, color_str)
    if match:
        rgb_hex = match.group(1)
        alpha_hex = match.group(2) or 'FF'
        r = int(rgb_hex[0:2], 16)
        g = int(rgb_hex[2:4], 16)
        b = int(rgb_hex[4:6], 16)
        a = int(alpha_hex, 16)
        return (r, g, b, a)

    # 检查是否为RGB/RGBA元组格式
    tuple_pattern = r'^\((\d{1,3}),(\d{1,3}),(\d{1,3})(?:,(\d{1,3}))?\)$'
    match = re.match(tuple_pattern, color_str)
    if match:
        r = int(match.group(1))
        g = int(match.group(2))
        b = int(match.group(3))
        a = int(match.group(4)) if match.group(4) else 255
        # 确保值在有效范围内
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        a = max(0, min(255, a))
        return (r, g, b, a)

    # 默认返回黑色
    print(f"警告: 无法解析颜色 '{color_str}'，使用默认黑色")
    return (0, 0, 0, 255)

def add_watermark_to_image(image_path, output_dir, font_size=30, text_color='black', bg_color='white', position='bottom-right'):
    """
    为图片添加水印并保存到输出目录
    """
    try:
        # 打开图片
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        width, height = img.size

        # 获取水印文本（拍摄日期）
        watermark_text = get_exif_datetime(image_path)
        if not watermark_text:
            # 如果没有EXIF日期信息，使用文件修改时间
            mtime = os.path.getmtime(image_path)
            dt = datetime.fromtimestamp(mtime)
            watermark_text = dt.strftime('%Y-%m-%d')
            print(f"警告: {image_path} 没有EXIF日期信息，使用文件修改时间")

        # 设置水印字体和大小
        try:
            # 尝试使用系统字体
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            # 如果没有找到指定字体，使用默认字体
            font = ImageFont.load_default()

        # 获取文本大小
        # 对于较新版本的Pillow，使用font.getbbox()获取文本边界
        bbox = font.getbbox(watermark_text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # 计算水印位置
        margin = 10
        if position == 'top-left':
            x, y = margin, margin
        elif position == 'top-right':
            x, y = width - text_width - margin, margin
        elif position == 'bottom-left':
            x, y = margin, height - text_height - margin
        elif position == 'bottom-right':
            x, y = width - text_width - margin, height - text_height - margin
        elif position == 'center':
            x, y = (width - text_width) // 2, (height - text_height) // 2
        else:
            # 默认右下角
            x, y = width - text_width - margin, height - text_height - margin

        # 解析颜色
        text_color_rgba = parse_color(text_color)
        bg_color_rgba = parse_color(bg_color)

        # 添加半透明背景
        draw.rectangle([x-5, y-5, x+text_width+5, y+text_height+5], fill=bg_color_rgba)
        # 添加水印文本
        draw.text((x, y), watermark_text, font=font, fill=text_color_rgba)

        # 保存图片到输出目录
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.basename(image_path)
        output_path = os.path.join(output_dir, f"watermarked_{filename}")
        img.save(output_path)
        print(f"已保存带水印的图片到: {output_path}")
        return True
    except Exception as e:
        print(f"处理图片时出错 {image_path}: {e}")
        return False


def process_directory(input_path, font_size=30, text_color='black', bg_color='white', position='bottom-right'):
    """
    处理输入路径，可能是单个文件或目录
    """
    if not os.path.exists(input_path):
        print(f"错误: 路径不存在 {input_path}")
        return

    # 确定输出目录
    if os.path.isfile(input_path):
        parent_dir = os.path.dirname(input_path)
        output_dir = os.path.join(parent_dir, f"{os.path.basename(parent_dir)}_watermark")
        add_watermark_to_image(input_path, output_dir, font_size, text_color, bg_color, position)
    else:
        # 是目录，处理目录下所有图片
        output_dir = os.path.join(input_path, f"{os.path.basename(input_path)}_watermark")
        # 支持的图片格式
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']
        
        # 遍历目录下所有文件
        for filename in os.listdir(input_path):
            file_path = os.path.join(input_path, filename)
            # 只处理文件和支持的图片格式
            if os.path.isfile(file_path) and any(filename.lower().endswith(ext) for ext in image_extensions):
                add_watermark_to_image(file_path, output_dir, font_size, text_color, bg_color, position)


if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='为图片添加基于拍摄日期的水印')
    parser.add_argument('image_path', help='图片文件路径或包含图片的目录路径')
    parser.add_argument('--font-size', type=int, default=30, help='水印字体大小（默认：30）')
    parser.add_argument('--text-color', type=str, default='black', help='水印文本颜色（支持十六进制、RGB元组或预定义颜色名，默认：black）')
    parser.add_argument('--bg-color', type=str, default='white', help='水印背景颜色（支持十六进制、RGB元组或预定义颜色名，默认：white）')
    parser.add_argument('--position', type=str, default='bottom-right', 
                        choices=['top-left', 'top-right', 'bottom-left', 'bottom-right', 'center'],
                        help='水印位置（默认：bottom-right）')
    args = parser.parse_args()

    # 处理输入路径
    process_directory(args.image_path, args.font_size, args.text_color, args.bg_color, args.position)