import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import exifread
from datetime import datetime
import re
import threading

# 确保中文显示正常
if sys.platform == 'win32':
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)

class WatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片日期水印工具")
        self.root.geometry("900x700")
        
        # 设置中文字体
        self.font_config = {
            'title': ('SimHei', 12, 'bold'),
            'normal': ('SimHei', 10)
        }
        
        # 存储导入的图片路径
        self.image_paths = []
        # 存储缩略图
        self.thumbnails = []
        
        # 创建主布局
        self.create_widgets()
        
        # 设置拖拽功能
        self.setup_drag_and_drop()
    
    def create_widgets(self):
        # 创建顶部按钮区域
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        import_btn = tk.Button(top_frame, text="导入图片", command=self.import_images, font=self.font_config['normal'], width=15)
        import_btn.pack(side=tk.LEFT, padx=5)
        
        import_folder_btn = tk.Button(top_frame, text="导入文件夹", command=self.import_folder, font=self.font_config['normal'], width=15)
        import_folder_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = tk.Button(top_frame, text="清空列表", command=self.clear_images, font=self.font_config['normal'], width=15)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # 开始处理按钮 - 移到顶部区域便于用户找到
        self.process_btn = tk.Button(top_frame, text="开始处理", command=self.start_processing, font=self.font_config['title'], width=15)
        self.process_btn.pack(side=tk.RIGHT, padx=5)
        
        # 创建设置区域
        settings_frame = ttk.LabelFrame(self.root, text="水印设置", padding=(10, 5))
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 字体大小设置
        font_size_frame = tk.Frame(settings_frame)
        font_size_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(font_size_frame, text="字体大小:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.font_size_var = tk.IntVar(value=30)
        tk.Scale(font_size_frame, from_=10, to=100, orient=tk.HORIZONTAL, variable=self.font_size_var, length=200).pack(side=tk.LEFT, padx=5)
        tk.Label(font_size_frame, textvariable=self.font_size_var, font=self.font_config['normal'], width=5).pack(side=tk.LEFT, padx=5)
        
        # 水印位置设置
        position_frame = tk.Frame(settings_frame)
        position_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(position_frame, text="水印位置:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.position_var = tk.StringVar(value="bottom-right")
        positions = ['top-left', 'top-right', 'bottom-left', 'bottom-right', 'center', 'top', 'bottom', 'left', 'right']
        position_combo = ttk.Combobox(position_frame, textvariable=self.position_var, values=positions, state="readonly", width=15)
        position_combo.pack(side=tk.LEFT, padx=5)
        
        # 文本颜色设置
        text_color_frame = tk.Frame(settings_frame)
        text_color_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(text_color_frame, text="文本颜色:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.text_color_var = tk.StringVar(value="black")
        colors = ['black', 'white', 'red', 'green', 'blue', 'yellow', 'cyan', 'magenta']
        text_color_combo = ttk.Combobox(text_color_frame, textvariable=self.text_color_var, values=colors, state="readonly", width=15)
        text_color_combo.pack(side=tk.LEFT, padx=5)
        
        # 背景颜色设置
        bg_color_frame = tk.Frame(settings_frame)
        bg_color_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(bg_color_frame, text="背景颜色:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.bg_color_var = tk.StringVar(value="white")
        bg_color_combo = ttk.Combobox(bg_color_frame, textvariable=self.bg_color_var, values=colors, state="readonly", width=15)
        bg_color_combo.pack(side=tk.LEFT, padx=5)
        
        # 创建导出设置区域
        export_frame = ttk.LabelFrame(self.root, text="导出设置", padding=(10, 5))
        export_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 输出文件夹设置
        output_folder_frame = tk.Frame(export_frame)
        output_folder_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(output_folder_frame, text="输出文件夹:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.output_folder_var = tk.StringVar(value="")
        tk.Entry(output_folder_frame, textvariable=self.output_folder_var, font=self.font_config['normal'], width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        tk.Button(output_folder_frame, text="浏览", command=self.select_output_folder, font=self.font_config['normal'], width=10).pack(side=tk.RIGHT, padx=5)
        
        # 输出格式设置
        output_format_frame = tk.Frame(export_frame)
        output_format_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(output_format_frame, text="输出格式:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.output_format_var = tk.StringVar(value="JPEG")
        formats = ['JPEG', 'PNG']
        format_combo = ttk.Combobox(output_format_frame, textvariable=self.output_format_var, values=formats, state="readonly", width=15)
        format_combo.pack(side=tk.LEFT, padx=5)
        
        # 命名规则设置
        naming_frame = tk.Frame(export_frame)
        naming_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(naming_frame, text="命名规则:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.naming_var = tk.StringVar(value="suffix")
        tk.Radiobutton(naming_frame, text="保留原名", variable=self.naming_var, value="original", font=self.font_config['normal']).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(naming_frame, text="添加前缀:", variable=self.naming_var, value="prefix", font=self.font_config['normal']).pack(side=tk.LEFT, padx=5)
        self.prefix_var = tk.StringVar(value="wm_")
        tk.Entry(naming_frame, textvariable=self.prefix_var, font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(naming_frame, text="添加后缀:", variable=self.naming_var, value="suffix", font=self.font_config['normal']).pack(side=tk.LEFT, padx=5)
        self.suffix_var = tk.StringVar(value="_watermarked")
        tk.Entry(naming_frame, textvariable=self.suffix_var, font=self.font_config['normal'], width=15).pack(side=tk.LEFT, padx=5)
        
        # 创建图片列表区域
        list_frame = ttk.LabelFrame(self.root, text="已导入图片", padding=(10, 5))
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建滚动区域
        self.canvas = tk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # 进度条
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5, expand=True)
        
        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = tk.Label(self.root, textvariable=self.status_var, font=self.font_config['normal'], bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_drag_and_drop(self):
        # 注意：在tkinter中实现跨平台的文件拖放功能较为复杂
        # 如需完整的拖放支持，建议安装tkinterdnd2库
        # 目前暂时禁用拖放功能，确保应用程序能够正常启动
        print("拖放功能已禁用。如需使用此功能，建议安装tkinterdnd2库。")
    
    def on_drag_enter(self, event):
        # 拖拽进入事件
        self.status_var.set("拖拽图片到此处...")
    
    def on_drag_leave(self, event):
        # 拖拽离开事件
        self.status_var.set("就绪")
    
    def on_drop(self, event):
        # macOS上的拖放事件
        self.status_var.set("就绪")
        try:
            # 获取拖放的文件路径
            if sys.platform == 'darwin':  # macOS
                files = self.root.tk.splitlist(event.data)
                self.add_images(files)
        except Exception as e:
            messagebox.showerror("错误", f"拖放文件失败: {str(e)}")
    
    def on_drop_files(self, event):
        # Windows上的拖放事件
        self.status_var.set("就绪")
        try:
            # 获取拖放的文件路径
            files = self.root.tk.splitlist(event.data)
            self.add_images(files)
        except Exception as e:
            messagebox.showerror("错误", f"拖放文件失败: {str(e)}")
    
    def import_images(self):
        # 导入单张或多张图片
        file_types = [
            ("图片文件", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff;*.gif"),
            ("所有文件", "*.*")
        ]
        file_paths = filedialog.askopenfilenames(title="选择图片文件", filetypes=file_types)
        if file_paths:
            self.add_images(file_paths)
    
    def import_folder(self):
        # 导入整个文件夹
        folder_path = filedialog.askdirectory(title="选择图片文件夹")
        if folder_path:
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
            file_paths = []
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in image_extensions):
                        file_paths.append(os.path.join(root, file))
            if file_paths:
                self.add_images(file_paths)
            else:
                messagebox.showinfo("提示", f"所选文件夹中未找到支持的图片文件")
    
    def add_images(self, file_paths):
        # 添加图片到列表
        for file_path in file_paths:
            if file_path not in self.image_paths:
                self.image_paths.append(file_path)
                self.display_image(file_path)
        self.update_status()
    
    def display_image(self, file_path):
        # 显示图片缩略图
        try:
            # 打开图片并创建缩略图
            img = Image.open(file_path)
            img.thumbnail((100, 100))
            thumbnail = ImageTk.PhotoImage(img)
            
            # 保存缩略图引用
            self.thumbnails.append(thumbnail)
            
            # 创建图片项
            item_frame = tk.Frame(self.scrollable_frame, bd=1, relief=tk.RAISED)
            item_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # 添加缩略图
            img_label = tk.Label(item_frame, image=thumbnail)
            img_label.pack(side=tk.LEFT, padx=5, pady=5)
            
            # 添加文件名和路径
            file_name = os.path.basename(file_path)
            path_label = tk.Label(item_frame, text=file_path, font=self.font_config['normal'], wraplength=600, justify=tk.LEFT)
            path_label.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
            
            # 添加删除按钮
            delete_btn = tk.Button(item_frame, text="删除", command=lambda path=file_path, frame=item_frame: self.remove_image(path, frame), font=self.font_config['normal'], width=8)
            delete_btn.pack(side=tk.RIGHT, padx=5, pady=5)
            
        except Exception as e:
            messagebox.showerror("错误", f"无法显示图片 {file_path}: {str(e)}")
    
    def remove_image(self, file_path, frame):
        # 从列表中删除图片
        if file_path in self.image_paths:
            self.image_paths.remove(file_path)
        frame.destroy()
        self.update_status()
    
    def clear_images(self):
        # 清空所有图片
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.image_paths.clear()
        self.thumbnails.clear()
        self.update_status()
    
    def select_output_folder(self):
        # 选择输出文件夹
        folder_path = filedialog.askdirectory(title="选择输出文件夹")
        if folder_path:
            self.output_folder_var.set(folder_path)
    
    def update_status(self):
        # 更新状态栏信息
        self.status_var.set(f"已导入 {len(self.image_paths)} 张图片")
    
    def start_processing(self):
        # 开始处理图片
        if not self.image_paths:
            messagebox.showinfo("提示", "请先导入图片")
            return
        
        output_folder = self.output_folder_var.get()
        if not output_folder:
            messagebox.showinfo("提示", "请先选择输出文件夹")
            return
        
        # 检查输出文件夹是否是原文件夹的子文件夹
        for img_path in self.image_paths:
            img_dir = os.path.dirname(img_path)
            if os.path.commonpath([img_dir, output_folder]) == img_dir:
                messagebox.showwarning("警告", "输出文件夹不能是原图片所在文件夹的子文件夹，以防止覆盖原图")
                return
        
        # 禁用处理按钮
        self.process_btn.config(state=tk.DISABLED)
        self.status_var.set("正在处理图片...")
        
        # 在新线程中处理图片
        thread = threading.Thread(target=self.process_images)
        thread.daemon = True
        thread.start()
    
    def process_images(self):
        # 处理所有图片
        success_count = 0
        fail_count = 0
        
        for i, img_path in enumerate(self.image_paths):
            try:
                # 处理图片
                success = self.add_watermark_to_image(
                    img_path,
                    self.output_folder_var.get(),
                    self.font_size_var.get(),
                    self.text_color_var.get(),
                    self.bg_color_var.get(),
                    self.position_var.get(),
                    self.output_format_var.get()
                )
                
                if success:
                    success_count += 1
                else:
                    fail_count += 1
                
            except Exception as e:
                fail_count += 1
                print(f"处理图片时出错 {img_path}: {str(e)}")
            
            # 更新进度条
            progress = (i + 1) / len(self.image_paths) * 100
            self.progress_var.set(progress)
            self.root.update_idletasks()
        
        # 处理完成
        self.root.after(0, lambda: self.process_complete(success_count, fail_count))
    
    def process_complete(self, success_count, fail_count):
        # 处理完成后的操作
        self.process_btn.config(state=tk.NORMAL)
        self.status_var.set(f"处理完成: 成功 {success_count} 张，失败 {fail_count} 张")
        
        if success_count > 0:
            if messagebox.askyesno("处理完成", f"成功处理 {success_count} 张图片，失败 {fail_count} 张图片\n是否打开输出文件夹？"):
                # 打开输出文件夹
                if sys.platform == 'win32':
                    os.startfile(self.output_folder_var.get())
                elif sys.platform == 'darwin':  # macOS
                    os.system(f'open "{self.output_folder_var.get()}"')
                else:  # Linux
                    os.system(f'xdg-open "{self.output_folder_var.get()}"')
    
    def get_exif_datetime(self, image_path):
        # 从图片文件中读取EXIF信息中的拍摄时间
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
    
    def parse_color(self, color_str):
        # 解析颜色字符串
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
    
    def add_watermark_to_image(self, image_path, output_dir, font_size=30, text_color='black', bg_color='white', position='bottom-right', output_format='JPEG'):
        # 为图片添加水印并保存
        try:
            # 打开图片
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)
            width, height = img.size
            
            # 获取水印文本（从调用参数获取，已经在process_images中处理过）
            watermark_text = self.get_exif_datetime(image_path)
            if not watermark_text:
                # 如果没有EXIF日期信息，使用文件修改时间
                mtime = os.path.getmtime(image_path)
                dt = datetime.fromtimestamp(mtime)
                watermark_text = dt.strftime('%Y-%m-%d')
            
            # 设置水印字体和大小
            try:
                # 尝试使用系统字体
                font = ImageFont.truetype("arial.ttf", font_size)
            except IOError:
                # 如果没有找到指定字体，使用默认字体
                font = ImageFont.load_default()
            
            # 获取文本大小
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
            elif position == 'top':
                x, y = (width - text_width) // 2, margin
            elif position == 'bottom':
                x, y = (width - text_width) // 2, height - text_height - margin
            elif position == 'left':
                x, y = margin, (height - text_height) // 2
            elif position == 'right':
                x, y = width - text_width - margin, (height - text_height) // 2
            else:
                # 默认右下角
                x, y = width - text_width - margin, height - text_height - margin
            
            # 解析颜色
            text_color_rgba = self.parse_color(text_color)
            bg_color_rgba = self.parse_color(bg_color)
            
            # 添加半透明背景
            draw.rectangle([x-5, y-5, x+text_width+5, y+text_height+5], fill=bg_color_rgba)
            # 添加水印文本
            draw.text((x, y), watermark_text, font=font, fill=text_color_rgba)
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成输出文件名
            filename = os.path.basename(image_path)
            name_without_ext, ext = os.path.splitext(filename)
            
            # 应用命名规则
            naming_rule = self.naming_var.get()
            if naming_rule == 'original':
                output_filename = filename
            elif naming_rule == 'prefix':
                output_filename = f"{self.prefix_var.get()}{filename}"
            else:  # suffix
                output_filename = f"{name_without_ext}{self.suffix_var.get()}{ext}"
            
            # 根据输出格式调整扩展名
            if output_format == 'PNG':
                output_filename = os.path.splitext(output_filename)[0] + '.png'
            else:  # JPEG
                # 保持原图片的扩展名（jpg或jpeg）
                if ext.lower() == '.jpeg':
                    output_filename = os.path.splitext(output_filename)[0] + '.jpeg'
                else:
                    output_filename = os.path.splitext(output_filename)[0] + '.jpg'
            
            # 保存图片
            output_path = os.path.join(output_dir, output_filename)
            
            # 根据输出格式设置保存参数
            if output_format == 'PNG':
                img.save(output_path, format='PNG')
            else:  # JPEG
                # 如果是RGBA图像，转换为RGB
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
                    background.save(output_path, format='JPEG', quality=95)
                else:
                    img.save(output_path, format='JPEG', quality=95)
            
            return True
        except Exception as e:
            print(f"处理图片时出错 {image_path}: {e}")
            return False

if __name__ == "__main__":
    # 创建主窗口
    root = tk.Tk()
    # 创建应用实例
    app = WatermarkApp(root)
    # 启动主循环
    root.mainloop()