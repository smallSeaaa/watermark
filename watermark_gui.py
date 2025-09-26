import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, colorchooser
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
        # 进一步增大窗口尺寸，提供更宽敞的操作空间
        self.root.geometry("1100x900")
        self.root.minsize(1000, 800)
        # 窗口尺寸变化时自动调整布局
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # 设置中文字体
        self.font_config = {
            'title': ('SimHei', 12, 'bold'),
            'normal': ('SimHei', 10)
        }
        
        # 存储导入的图片路径
        self.image_paths = []
        # 存储缩略图
        self.thumbnails = []
        
        # 窗口过程相关变量
        self.original_wnd_proc = None
        self.new_wnd_proc = None
        self.LRESULT = None
        self.root_handle = None
        
        # 启用拖拽功能
        self.enable_drag_and_drop()
        
        # 创建主布局
        self.create_widgets()
        
        # 绑定窗口关闭事件，确保清理资源
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def enable_drag_and_drop(self):
        # 启用主窗口接受拖放功能
        try:
            # 添加提示文本，告知用户可以拖拽文件
            self.drag_hint = tk.Label(self.root, text="提示: 您可以直接将图片拖放到窗口中进行导入", 
                                     font=self.font_config['normal'], fg="gray")
            self.drag_hint.pack(pady=5)
            
            # 在Windows上，当文件被拖放到应用程序窗口时，文件路径会作为命令行参数传递
            # 我们在应用启动时就检查是否有拖放的文件
            self.check_for_dropped_files_at_startup()
            
            # 尝试使用tkinterdnd2库实现拖放功能
            try:
                from tkinterdnd2 import DND_FILES, TkinterDnD
                
                # 在主窗口上注册拖放功能
                if hasattr(self.root, 'drop_target_register'):
                    # 注册接受文件拖放
                    self.root.drop_target_register(DND_FILES)
                    
                    # 绑定拖放事件处理函数
                    def on_dnd_drop(event):
                        try:
                            # 获取拖放的文件路径
                            file_paths = event.data.strip('{}').split()
                            
                            # 检查是否是图片文件
                            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
                            valid_image_paths = []
                            for file_path in file_paths:
                                # 去除可能的引号
                                file_path = file_path.strip('"\'')
                                if os.path.isfile(file_path):
                                    _, ext = os.path.splitext(file_path)
                                    if ext.lower() in image_extensions:
                                        valid_image_paths.append(file_path)
                            
                            # 如果有有效的图片文件，添加到列表
                            if valid_image_paths:
                                self.add_images(valid_image_paths)
                        except Exception as e:
                            print(f"拖放处理错误: {e}")
                            messagebox.showerror("拖放错误", f"处理拖放文件时出错: {str(e)}")
                    
                    # 绑定拖放事件
                    self.root.dnd_bind('<<Drop>>', on_dnd_drop)
                    
                    # 设置光标样式
                    # 注意：tkinterdnd2可能不直接支持DragEnter和DragLeave事件
                    # 我们尝试使用通用的Enter和Leave事件来处理光标样式
                    def on_enter(event):
                        self.root.config(cursor="hand2")
                    
                    def on_leave(event):
                        self.root.config(cursor="arrow")
                    
                    self.root.bind('<Enter>', on_enter)
                    self.root.bind('<Leave>', on_leave)
                    
                    print("拖放功能已启用，使用tkinterdnd2库")
                else:
                    print("当前窗口不支持拖放功能")
                
            except ImportError:
                print("未找到tkinterdnd2库，拖放功能不可用。请运行 'pip install tkinterdnd2' 安装。")
            except Exception as e:
                print(f"启用拖放功能时出错: {e}")
        except Exception as e:
            print(f"启用拖拽功能时出错: {e}")
    
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
        
        # 字体选择设置
        font_frame = tk.Frame(settings_frame)
        font_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(font_frame, text="选择字体:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.font_var = tk.StringVar(value="Arial")
        
        # 获取系统字体列表
        import sys
        import os
        if sys.platform.startswith('win'):
            try:
                import winreg
                # 从Windows注册表获取已安装字体
                font_reg_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, font_reg_path) as key:
                    font_names = []
                    i = 0
                    while True:
                        try:
                            # 获取字体名称和文件名
                            font_name, font_file, _ = winreg.EnumValue(key, i)
                            # 提取字体名称（去掉后面的版本信息）
                            font_base_name = font_name.split(' ')[0]
                            if font_base_name and font_base_name not in font_names:
                                font_names.append(font_base_name)
                            i += 1
                        except OSError:
                            break
                    # 添加一些常见字体作为后备
                    common_fonts = ["Arial", "Times New Roman", "Courier New", "Microsoft YaHei", "SimHei", "SimSun"]
                    for font in common_fonts:
                        if font not in font_names:
                            font_names.append(font)
                    font_names.sort()
            except Exception as e:
                print(f"获取系统字体失败: {e}")
                font_names = ["Arial", "Times New Roman", "Courier New", "Microsoft YaHei", "SimHei", "SimSun"]
        else:
            # 非Windows系统使用一组通用字体
            font_names = ["Arial", "Times New Roman", "Courier New"]
        
        # 创建字体下拉菜单
        font_combo = ttk.Combobox(font_frame, textvariable=self.font_var, values=font_names, state="readonly", width=30)
        font_combo.pack(side=tk.LEFT, padx=5)
        
        # 字体样式设置（粗体和斜体）
        font_style_frame = tk.Frame(settings_frame)
        font_style_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(font_style_frame, text="字体样式:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        
        self.bold_var = tk.BooleanVar(value=False)
        self.italic_var = tk.BooleanVar(value=False)
        
        bold_check = tk.Checkbutton(font_style_frame, text="粗体", variable=self.bold_var, font=self.font_config['normal'])
        bold_check.pack(side=tk.LEFT, padx=10)
        
        italic_check = tk.Checkbutton(font_style_frame, text="斜体", variable=self.italic_var, font=self.font_config['normal'])
        italic_check.pack(side=tk.LEFT, padx=10)
        
        # 阴影效果设置
        shadow_frame = tk.Frame(settings_frame)
        shadow_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(shadow_frame, text="阴影效果:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        
        self.shadow_var = tk.BooleanVar(value=False)
        shadow_check = tk.Checkbutton(shadow_frame, text="启用阴影", variable=self.shadow_var, font=self.font_config['normal'])
        shadow_check.pack(side=tk.LEFT, padx=10)
        
        # 阴影颜色设置
        tk.Label(shadow_frame, text="阴影颜色:", font=self.font_config['normal'], width=8).pack(side=tk.LEFT, padx=5)
        self.shadow_color_var = tk.StringVar(value="black")
        shadow_color_combo = ttk.Combobox(shadow_frame, textvariable=self.shadow_color_var, 
                                         values=['black', 'white', 'gray', 'red', 'blue', 'green'], 
                                         state="readonly", width=10)
        shadow_color_combo.pack(side=tk.LEFT, padx=5)
        
        # 阴影偏移设置
        tk.Label(shadow_frame, text="偏移:", font=self.font_config['normal'], width=4).pack(side=tk.LEFT, padx=5)
        self.shadow_offset_var = tk.IntVar(value=2)
        shadow_offset_scale = tk.Scale(shadow_frame, from_=1, to=10, orient=tk.HORIZONTAL, 
                                      variable=self.shadow_offset_var, length=100)
        shadow_offset_scale.pack(side=tk.LEFT, padx=5)
        
        # 描边效果设置
        stroke_frame = tk.Frame(settings_frame)
        stroke_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(stroke_frame, text="描边效果:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        
        self.stroke_var = tk.BooleanVar(value=False)
        stroke_check = tk.Checkbutton(stroke_frame, text="启用描边", variable=self.stroke_var, font=self.font_config['normal'])
        stroke_check.pack(side=tk.LEFT, padx=10)
        
        # 描边颜色设置
        tk.Label(stroke_frame, text="描边颜色:", font=self.font_config['normal'], width=8).pack(side=tk.LEFT, padx=5)
        self.stroke_color_var = tk.StringVar(value="white")
        stroke_color_combo = ttk.Combobox(stroke_frame, textvariable=self.stroke_color_var, 
                                         values=['black', 'white', 'gray', 'red', 'blue', 'green'], 
                                         state="readonly", width=10)
        stroke_color_combo.pack(side=tk.LEFT, padx=5)
        
        # 描边宽度设置
        tk.Label(stroke_frame, text="宽度:", font=self.font_config['normal'], width=4).pack(side=tk.LEFT, padx=5)
        self.stroke_width_var = tk.IntVar(value=1)
        stroke_width_scale = tk.Scale(stroke_frame, from_=1, to=5, orient=tk.HORIZONTAL, 
                                     variable=self.stroke_width_var, length=100)
        stroke_width_scale.pack(side=tk.LEFT, padx=5)
        
        # 水印位置设置
        position_frame = tk.Frame(settings_frame)
        position_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(position_frame, text="水印位置:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.position_var = tk.StringVar(value="bottom-right")
        positions = ['top-left', 'top-right', 'bottom-left', 'bottom-right', 'center', 'top', 'bottom', 'left', 'right']
        position_combo = ttk.Combobox(position_frame, textvariable=self.position_var, values=positions, state="readonly", width=15)
        position_combo.pack(side=tk.LEFT, padx=5)
        
        # 文本颜色设置 - 使用调色板
        text_color_frame = tk.Frame(settings_frame)
        text_color_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(text_color_frame, text="文本颜色:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.text_color_var = tk.StringVar(value="black")
        
        # 添加颜色预览标签和选择按钮
        self.color_preview = tk.Label(text_color_frame, width=10, height=2, bg=self.text_color_var.get(), relief=tk.RAISED)
        self.color_preview.pack(side=tk.LEFT, padx=5)
        
        # 添加颜色选择按钮，打开调色板
        def choose_color():
            # 打开颜色选择对话框
            color = tk.colorchooser.askcolor(title="选择文本颜色", initialcolor=self.text_color_var.get())
            if color[1]:  # 如果用户选择了颜色而不是取消
                # 更新颜色变量和预览
                self.text_color_var.set(color[1])
                self.color_preview.config(bg=color[1])
                print(f"选择了颜色: {color[1]}")
        
        color_btn = tk.Button(text_color_frame, text="选择颜色", command=choose_color, font=self.font_config['normal'], width=10)
        color_btn.pack(side=tk.LEFT, padx=5)
        
        # 添加最近使用的颜色下拉列表，保留快速选择功能
        colors = ['black', 'white', 'red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'gray', 'orange', 'purple', 'brown', 'pink']
        text_color_combo = ttk.Combobox(text_color_frame, textvariable=self.text_color_var, values=colors, state="readonly", width=15)
        text_color_combo.pack(side=tk.LEFT, padx=5)
        
        # 当从下拉列表选择颜色时，更新预览
        def update_preview(event):
            self.color_preview.config(bg=self.text_color_var.get())
        
        text_color_combo.bind("<<ComboboxSelected>>", update_preview)
        
        # 文本透明度设置
        opacity_frame = tk.Frame(settings_frame)
        opacity_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(opacity_frame, text="文本透明度:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.opacity_var = tk.IntVar(value=0)  # 默认完全不透明（透明度为0）
        tk.Scale(opacity_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.opacity_var, length=200).pack(side=tk.LEFT, padx=5)
        tk.Label(opacity_frame, textvariable=self.opacity_var, font=self.font_config['normal'], width=5).pack(side=tk.LEFT, padx=5)
        tk.Label(opacity_frame, text="%", font=self.font_config['normal']).pack(side=tk.LEFT, padx=5)
        
        # 水印文本类型设置
        text_type_frame = tk.Frame(settings_frame)
        text_type_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(text_type_frame, text="水印类型:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.text_type_var = tk.StringVar(value="date")
        
        # 创建水印类型选项组
        text_type_options = tk.Frame(text_type_frame)
        text_type_options.pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(text_type_options, text="拍摄日期", variable=self.text_type_var, value="date", font=self.font_config['normal']).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(text_type_options, text="自定义文本", variable=self.text_type_var, value="custom", font=self.font_config['normal']).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 自定义文本输入框
        self.custom_text_var = tk.StringVar(value="")
        self.custom_text_entry = tk.Entry(text_type_frame, textvariable=self.custom_text_var, font=self.font_config['normal'], width=30)
        self.custom_text_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        # 初始状态下禁用自定义文本输入框
        self.custom_text_entry.config(state="disabled")
        
        # 绑定水印类型变化事件
        self.text_type_var.trace_add("write", self.on_text_type_change)
        
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
        formats = ['JPEG', 'JPG', 'PNG']
        format_combo = ttk.Combobox(output_format_frame, textvariable=self.output_format_var, values=formats, state="readonly", width=15)
        format_combo.pack(side=tk.LEFT, padx=5)
        
        # 绑定格式变化事件，用于控制质量滑块的可用状态
        format_combo.bind("<<ComboboxSelected>>", self.on_format_change)
        
        # JPEG质量设置
        self.jpeg_quality_var = tk.IntVar(value=95)
        self.quality_frame = tk.Frame(export_frame)
        self.quality_frame.pack(fill=tk.X, pady=5)
        
        self.quality_label = tk.Label(self.quality_frame, text="JPEG质量:", font=self.font_config['normal'], width=10)
        self.quality_label.pack(side=tk.LEFT, padx=5)
        self.quality_scale = tk.Scale(self.quality_frame, from_=1, to=100, orient=tk.HORIZONTAL, 
                                    variable=self.jpeg_quality_var, length=200)
        self.quality_scale.pack(side=tk.LEFT, padx=5)
        self.quality_value_label = tk.Label(self.quality_frame, textvariable=self.jpeg_quality_var, 
                                          font=self.font_config['normal'], width=5)
        self.quality_value_label.pack(side=tk.LEFT, padx=5)
        
        # 初始状态检查，确保只有JPEG/JPG格式时质量控制才可用
        self.update_quality_control_state()
        
        # 图片尺寸设置
        resize_frame = ttk.LabelFrame(export_frame, text="图片尺寸设置", padding=(10, 5))
        resize_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 缩放方式选择 - 优化布局
        resize_control_frame = tk.Frame(resize_frame)
        resize_control_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(resize_control_frame, text="缩放方式:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.resize_method_var = tk.StringVar(value="none")
        resize_options = ["不缩放", "按宽度", "按高度", "按百分比"]
        self.resize_combo = ttk.Combobox(resize_control_frame, textvariable=self.resize_method_var, values=resize_options, state="readonly", width=10)
        self.resize_combo.pack(side=tk.LEFT, padx=5)
        self.resize_combo.bind("<<ComboboxSelected>>", lambda _: self.update_resize_control_state())
        
        # 创建一个字典来映射显示文本和实际值
        self.resize_method_map = {opt: val for opt, val in zip(resize_options, ["none", "width", "height", "percent"])}
        
        # 尺寸输入控件 - 更紧凑的布局
        size_input_frame = tk.Frame(resize_frame)
        size_input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 宽度输入
        width_frame = tk.Frame(size_input_frame)
        width_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        tk.Label(width_frame, text="宽度:", font=self.font_config['normal'], width=5).pack(side=tk.LEFT, padx=5)
        self.width_var = tk.IntVar(value=1920)
        self.width_entry = tk.Entry(width_frame, textvariable=self.width_var, width=8)
        self.width_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(width_frame, text="像素", font=self.font_config['normal']).pack(side=tk.LEFT, padx=5)
        
        # 高度输入
        height_frame = tk.Frame(size_input_frame)
        height_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        tk.Label(height_frame, text="高度:", font=self.font_config['normal'], width=5).pack(side=tk.LEFT, padx=5)
        self.height_var = tk.IntVar(value=1080)
        self.height_entry = tk.Entry(height_frame, textvariable=self.height_var, width=8)
        self.height_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(height_frame, text="像素", font=self.font_config['normal']).pack(side=tk.LEFT, padx=5)
        
        # 百分比输入
        percent_frame = tk.Frame(size_input_frame)
        percent_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        tk.Label(percent_frame, text="缩放百分比:", font=self.font_config['normal'], width=8).pack(side=tk.LEFT, padx=5)
        self.percent_var = tk.IntVar(value=100)
        self.percent_entry = tk.Entry(percent_frame, textvariable=self.percent_var, width=8)
        self.percent_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(percent_frame, text="%", font=self.font_config['normal']).pack(side=tk.LEFT, padx=5)
        
        # 调用更新方法设置初始状态
        self.update_resize_control_state()
        
        # 命名规则设置 - 优化布局
        naming_frame = tk.Frame(export_frame)
        naming_frame.pack(fill=tk.X, pady=5)
        
        # 左侧标签
        tk.Label(naming_frame, text="命名规则:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        
        # 创建选项组
        name_options_frame = tk.Frame(naming_frame)
        name_options_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.naming_var = tk.StringVar(value="suffix")
        tk.Radiobutton(name_options_frame, text="保留原名", variable=self.naming_var, value="original", font=self.font_config['normal']).pack(side=tk.LEFT, padx=5)
        
        # 前缀选项
        prefix_frame = tk.Frame(name_options_frame)
        prefix_frame.pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(prefix_frame, text="添加前缀:", variable=self.naming_var, value="prefix", font=self.font_config['normal']).pack(side=tk.LEFT)
        self.prefix_var = tk.StringVar(value="wm_")
        tk.Entry(prefix_frame, textvariable=self.prefix_var, font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        
        # 后缀选项
        suffix_frame = tk.Frame(name_options_frame)
        suffix_frame.pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(suffix_frame, text="添加后缀:", variable=self.naming_var, value="suffix", font=self.font_config['normal']).pack(side=tk.LEFT)
        self.suffix_var = tk.StringVar(value="_watermarked")
        tk.Entry(suffix_frame, textvariable=self.suffix_var, font=self.font_config['normal'], width=15).pack(side=tk.LEFT, padx=5)
        
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
            # 如果已导入图片，检查输出文件夹是否是原图片所在文件夹
            if self.image_paths:
                is_invalid_folder = False
                for img_path in self.image_paths:
                    img_dir = os.path.dirname(img_path)
                    # 检查是否是同一个文件夹
                    if os.path.normpath(folder_path) == os.path.normpath(img_dir):
                        is_invalid_folder = True
                        break
                    # 检查是否是子文件夹（保留原有的检查逻辑）
                    if os.path.commonpath([img_dir, folder_path]) == img_dir:
                        is_invalid_folder = True
                        break
                
                if is_invalid_folder:
                    messagebox.showwarning("警告", "输出文件夹不能是原图片所在文件夹或其子文件夹，以防止覆盖原图")
                    return
            
            # 所有检查通过，设置输出文件夹
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
    
    def on_format_change(self, event=None):
        # 当输出格式改变时调用，更新质量控制UI的可用状态
        self.update_quality_control_state()
        
    def update_quality_control_state(self):
        # 根据当前选择的输出格式，设置质量控制UI的可用状态
        is_jpeg = self.output_format_var.get() in ['JPEG', 'JPG']
        state = 'normal' if is_jpeg else 'disabled'
        
        # 更新UI元素状态
        self.quality_label.config(state=state)
        self.quality_scale.config(state=state)
        self.quality_value_label.config(state=state)
        
    def update_resize_control_state(self):
        # 根据当前选择的缩放方式，设置尺寸控制UI的可用状态
        resize_method = self.resize_method_map.get(self.resize_method_var.get(), "none")
        
        # 根据缩放方式启用或禁用相应的控件
        width_state = "normal" if resize_method == "width" else "disabled"
        height_state = "normal" if resize_method == "height" else "disabled"
        percent_state = "normal" if resize_method == "percent" else "disabled"
        
        self.width_entry.config(state=width_state)
        self.height_entry.config(state=height_state)
        self.percent_entry.config(state=percent_state)
        
    def on_text_type_change(self, *args):
        # 根据选择的水印类型启用或禁用自定义文本输入框
        text_type = self.text_type_var.get()
        if text_type == "custom":
            self.custom_text_entry.config(state="normal")
        else:
            self.custom_text_entry.config(state="disabled")
        
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
                    'white',  # 背景颜色默认值（不再使用）
                    self.position_var.get(),
                    self.output_format_var.get(),
                    self.jpeg_quality_var.get(),
                    self.resize_method_map.get(self.resize_method_var.get(), "none"),
                    self.width_var.get(),
                    self.height_var.get(),
                    self.percent_var.get()
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
    
    def check_for_dropped_files_at_startup(self):
        # 检查启动时是否有文件被拖放到应用程序
        # 在Windows上，拖放的文件会作为命令行参数传递
        import sys
        
        # 检查是否有命令行参数（第一个参数是脚本本身）
        if len(sys.argv) > 1:
            # 过滤出图片文件
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
            valid_image_paths = []
            
            for file_path in sys.argv[1:]:
                # 检查文件是否存在且为图片文件
                if os.path.isfile(file_path):
                    _, ext = os.path.splitext(file_path)
                    if ext.lower() in image_extensions:
                        valid_image_paths.append(file_path)
            
            # 如果有有效的图片文件，添加到列表
            if valid_image_paths:
                self.add_images(valid_image_paths)
                
    def on_closing(self):
        # 销毁窗口
        self.root.destroy()
            
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
    
    def parse_color(self, color_str, opacity=100):
        # 解析颜色字符串，opacity参数控制透明度(0-100%)
        # 注意：opacity值越大，透明度越高
        print(f"解析颜色: '{color_str}', 透明度设置: {opacity}%")
        
        # 预定义颜色映射 - 增加更多常见颜色
        color_map = {
            'black': (0, 0, 0, 255),
            'white': (255, 255, 255, 255),
            'red': (255, 0, 0, 255),
            'green': (0, 255, 0, 255),
            'blue': (0, 0, 255, 255),
            'yellow': (255, 255, 0, 255),
            'cyan': (0, 255, 255, 255),
            'magenta': (255, 0, 255, 255),
            'gray': (128, 128, 128, 255),
            'grey': (128, 128, 128, 255),
            'orange': (255, 165, 0, 255),
            'purple': (128, 0, 128, 255),
            'brown': (165, 42, 42, 255),
            'pink': (255, 192, 203, 255)
        }
        
        # 检查是否为预定义颜色
        if color_str.lower() in color_map:
            r, g, b, a = color_map[color_str.lower()]
            # 应用透明度：opacity值越大，透明度越高
            a = int(a * (100 - opacity) / 100)
            print(f"使用预定义颜色: {color_str} -> RGBA: ({r}, {g}, {b}, {a})")
            return (r, g, b, a)
        
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
            # 应用透明度：opacity值越大，透明度越高
            a = int(a * (100 - opacity) / 100)
            print(f"使用十六进制颜色: {color_str} -> RGBA: ({r}, {g}, {b}, {a})")
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
            # 应用透明度：opacity值越大，透明度越高
            a = int(a * (100 - opacity) / 100)
            print(f"使用RGB元组颜色: {color_str} -> RGBA: ({r}, {g}, {b}, {a})")
            return (r, g, b, a)
        
        # 默认返回黑色，但使用与前面一致的透明度计算方式
        print(f"警告: 无法解析颜色 '{color_str}'，使用默认黑色")
        # 统一透明度计算方式
        return (0, 0, 0, int(255 * (100 - opacity) / 100))
    
    def add_watermark_to_image(self, image_path, output_dir, font_size=30, text_color='black', bg_color='white', position='bottom-right', output_format='JPEG', quality=95, resize_method='none', target_width=1920, target_height=1080, scale_percent=100):
        # 为图片添加水印并保存
        try:
            print(f"\n=== 开始处理图片: {os.path.basename(image_path)} ===")
            # 打开图片
            img = Image.open(image_path)
            width, height = img.size
            
            # 根据调整方式调整图片尺寸
            if resize_method == 'width':
                # 按宽度缩放
                ratio = target_width / width
                new_height = int(height * ratio)
                img = img.resize((target_width, new_height), Image.LANCZOS)
                width, height = img.size
            elif resize_method == 'height':
                # 按高度缩放
                ratio = target_height / height
                new_width = int(width * ratio)
                img = img.resize((new_width, target_height), Image.LANCZOS)
                width, height = img.size
            elif resize_method == 'percent':
                # 按百分比缩放
                new_width = int(width * scale_percent / 100)
                new_height = int(height * scale_percent / 100)
                img = img.resize((new_width, new_height), Image.LANCZOS)
                width, height = img.size
                
            # 确保图像支持透明度
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # 创建绘制对象
            draw = ImageDraw.Draw(img)
            
            # 根据水印类型获取水印文本
            text_type = self.text_type_var.get()
            if text_type == "custom":
                # 使用自定义文本
                watermark_text = self.custom_text_var.get().strip()
                # 如果自定义文本为空，使用日期作为默认值
                if not watermark_text:
                    watermark_text = self.get_exif_datetime(image_path)
                    if not watermark_text:
                        # 如果没有EXIF日期信息，使用文件修改时间
                        mtime = os.path.getmtime(image_path)
                        dt = datetime.fromtimestamp(mtime)
                        watermark_text = dt.strftime('%Y-%m-%d')
            else:
                # 使用日期水印
                watermark_text = self.get_exif_datetime(image_path)
                if not watermark_text:
                    # 如果没有EXIF日期信息，使用文件修改时间
                    mtime = os.path.getmtime(image_path)
                    dt = datetime.fromtimestamp(mtime)
                    watermark_text = dt.strftime('%Y-%m-%d')
            
            # 设置水印字体和大小
            font = None
            try:
                # 获取用户选择的字体、大小
                selected_font = self.font_var.get()
                print(f"=== 尝试加载字体: {selected_font}, 大小: {font_size} ===")
                
                # 预定义常见字体及其文件路径映射（根据测试结果，这是最可靠的方法）
                common_font_paths = {
                    'Microsoft YaHei': 'msyh.ttc',
                    'SimHei': 'simhei.ttf',
                    'SimSun': 'simsun.ttc',
                    'Arial': 'arial.ttf',
                    'Times New Roman': 'times.ttf',
                    'Courier New': 'cour.ttf',
                    'KaiTi': 'simkai.ttf',
                    'FangSong': 'simsun.ttc'
                }
                
                # 首先尝试使用Windows系统字体目录的绝对路径
                if sys.platform.startswith('win'):
                    font_dir = 'C:\\Windows\\Fonts'
                    
                    # 检查字体是否在预定义列表中
                    if selected_font in common_font_paths:
                        font_file = common_font_paths[selected_font]
                        font_path = os.path.join(font_dir, font_file)
                        
                        if os.path.exists(font_path):
                            try:
                                font = ImageFont.truetype(font_path, font_size)
                                print(f"✓ 成功从预定义路径加载字体: {font_path}")
                            except (IOError, OSError) as e:
                                print(f"✗ 无法从预定义路径加载字体: {font_path}, 错误: {str(e)}")
                    else:
                        # 如果不在预定义列表中，尝试映射到最接近的字体
                        print(f"✗ 字体 '{selected_font}' 不在预定义列表中，尝试使用替代字体")
                        # 尝试使用Arial作为默认替代字体
                        if 'Arial' in common_font_paths:
                            font_file = common_font_paths['Arial']
                            font_path = os.path.join(font_dir, font_file)
                            if os.path.exists(font_path):
                                try:
                                    font = ImageFont.truetype(font_path, font_size)
                                    print(f"✓ 成功加载替代字体: {font_path}")
                                except (IOError, OSError) as e:
                                    print(f"✗ 无法加载替代字体: {font_path}, 错误: {str(e)}")
                
                # 如果预定义路径加载失败，尝试搜索系统字体目录的所有字体文件
                if font is None and sys.platform.startswith('win'):
                    font_dir = 'C:\\Windows\\Fonts'
                    if os.path.exists(font_dir):
                        print(f"✗ 预定义路径加载失败，尝试搜索系统字体目录")
                        # 搜索常见的字体文件格式
                        font_extensions = ['.ttf', '.ttc', '.otf']
                        # 优先搜索的常见字体文件
                        priority_files = ['arial.ttf', 'simhei.ttf', 'msyh.ttc', 'simsun.ttc', 'times.ttf', 'cour.ttf']
                        
                        # 先尝试优先级列表中的字体
                        for font_file in priority_files:
                            font_path = os.path.join(font_dir, font_file)
                            if os.path.exists(font_path):
                                try:
                                    font = ImageFont.truetype(font_path, font_size)
                                    print(f"✓ 成功从系统目录加载优先字体: {font_path}")
                                    break
                                except (IOError, OSError):
                                    continue
                        
                        # 如果优先级列表中的字体都失败，尝试搜索所有字体文件
                        if font is None:
                            for file in os.listdir(font_dir):
                                if any(file.lower().endswith(ext) for ext in font_extensions):
                                    font_path = os.path.join(font_dir, file)
                                    try:
                                        font = ImageFont.truetype(font_path, font_size)
                                        print(f"✓ 成功从系统目录加载字体: {font_path}")
                                        break
                                    except (IOError, OSError):
                                        continue
                
                # 如果前面都失败，使用PIL默认字体作为最后的后备选项
                if font is None:
                    print(f"✗ 无法加载任何字体，使用PIL默认字体")
                    font = ImageFont.load_default()
            except Exception as e:
                print(f"✗ 字体加载异常: {str(e)}")
                # 出现任何异常，都使用默认字体
                font = ImageFont.load_default()
            
            print(f"最终使用字体: {'默认字体' if font is ImageFont.load_default() else '成功加载的字体'}")
            
            # 获取文本大小
            bbox = font.getbbox(watermark_text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            print(f"水印文本: '{watermark_text}', 文本尺寸: {text_width}x{text_height}")
            
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
            
            # 获取透明度设置
            text_opacity = self.opacity_var.get()
            print(f"水印设置: 文本='{watermark_text}', 字体='{selected_font}', 大小={font_size}, 颜色={text_color}, 不透明度={text_opacity}%")
            
            # 解析颜色并应用透明度
            text_color_rgba = self.parse_color(text_color, text_opacity)
            print(f"应用的颜色RGBA值: {text_color_rgba}")
            # 不再使用背景颜色 - 移除背景绘制
            
            # 创建一个透明图层用于绘制水印
            watermark_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
            watermark_draw = ImageDraw.Draw(watermark_layer)
            
            print(f"绘制水印: 位置({x}, {y}), 颜色{text_color_rgba}")
            
            # 在透明图层上绘制水印文本
            # 先绘制描边（如果启用）
            if self.stroke_var.get():
                stroke_width = self.stroke_width_var.get()
                stroke_color_rgba = self.parse_color(self.stroke_color_var.get(), text_opacity)
                # 使用循环在不同方向上绘制描边
                for offset_x in range(-stroke_width, stroke_width + 1):
                    for offset_y in range(-stroke_width, stroke_width + 1):
                        if offset_x != 0 or offset_y != 0:
                            watermark_draw.text((x + offset_x, y + offset_y), 
                                              watermark_text, font=font, fill=stroke_color_rgba)
            
            # 再绘制阴影（如果启用）
            if self.shadow_var.get():
                shadow_offset = self.shadow_offset_var.get()
                shadow_color_rgba = self.parse_color(self.shadow_color_var.get(), text_opacity)
                watermark_draw.text((x + shadow_offset, y + shadow_offset), 
                                  watermark_text, font=font, fill=shadow_color_rgba)
            
            # 最后绘制主要文本
            watermark_draw.text((x, y), watermark_text, font=font, fill=text_color_rgba)
            

            
            # 将水印图层合并到原图上
            img = Image.alpha_composite(img, watermark_layer)
            
            # 不再需要背景颜色设置 - 代码中已移除背景绘制
            
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
            elif output_format == 'JPG':
                output_filename = os.path.splitext(output_filename)[0] + '.jpg'
            else:  # JPEG
                output_filename = os.path.splitext(output_filename)[0] + '.jpeg'
            
            # 保存图片
            output_path = os.path.join(output_dir, output_filename)
            
            # 根据输出格式设置保存参数
            if output_format == 'PNG':
                # 对于PNG格式，直接保存以保留透明度
                img.save(output_path, format='PNG')
                print(f"已保存带透明背景的PNG图片: {output_path}")
            else:  # JPEG or JPG
                # 统一使用JPEG格式保存，因为JPG是JPEG的一种常见扩展名
                # 由于JPEG不支持透明背景，创建白色背景并使用alpha通道作为蒙版
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
                background.save(output_path, format='JPEG', quality=quality)
                print(f"已保存JPEG图片 (透明背景转换为白色): {output_path}")
            
            return True
        except Exception as e:
            print(f"处理图片时出错 {image_path}: {e}")
            return False

if __name__ == "__main__":
    try:
        from tkinterdnd2 import TkinterDnD
        # 创建支持拖放的主窗口
        root = TkinterDnD.Tk()
    except ImportError:
        # 如果tkinterdnd2不可用，回退到标准Tk窗口
        print("tkinterdnd2库不可用，使用标准窗口")
        root = tk.Tk()
    
    # 创建应用实例
    app = WatermarkApp(root)
    # 启动主循环
    root.mainloop()