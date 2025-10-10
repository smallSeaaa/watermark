import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, colorchooser
from PIL import Image, ImageTk, ImageDraw, ImageFont
import exifread
from datetime import datetime
import re
import threading
import json
import os

# 确保中文显示正常
if sys.platform == 'win32':
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)

class WatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片日期水印工具")
        # 设置窗口尺寸，提供宽敞的操作空间
        self.root.geometry("1600x900")
        self.root.minsize(1200, 800)
        
        # 设置现代配色方案 - 更新为更专业的配色
        self.colors = {
            'primary': '#2563EB',       # 主色调：专业蓝
            'primary_light': '#3B82F6', # 主色调浅色
            'secondary': '#059669',     # 辅助色：深绿
            'accent': '#DB2777',        # 强调色：粉色
            'background': '#F9FAFB',    # 背景色：极浅灰
            'card_bg': '#FFFFFF',       # 卡片背景：白色
            'text': '#1F2937',          # 文本颜色：深灰
            'text_light': '#6B7280',    # 次要文本：中灰
            'border': '#E5E7EB',        # 边框色：浅灰
            'shadow': '#0000001A'       # 阴影色：半透明黑
        }
        
        # 设置中文字体
        self.font_config = {
            'title': ('Microsoft YaHei', 12, 'bold'),
            'normal': ('Microsoft YaHei', 10),
            'small': ('Microsoft YaHei', 9)
        }
        
        # 设置文件路径
        self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')
        
        # 设置窗口背景
        self.root.configure(bg=self.colors['background'])
        
        # 存储导入的图片路径
        self.image_paths = []
        # 存储缩略图
        self.thumbnails = []
        # 当前选中的图片索引用于预览
        self.current_preview_index = -1
        # 预览窗口相关变量
        self.preview_image = None
        self.preview_photo = None
        # 自定义水印位置变量
        self.custom_watermark_position = None  # 存储(x, y)坐标
        self.is_dragging_watermark = False     # 标记是否正在拖动水印
        self.drag_offset_x = 0                 # 拖动时的X偏移量
        self.drag_offset_y = 0                 # 拖动时的Y偏移量
        self.watermark_text_id = None          # 水印文本对象ID
        
        # 窗口过程相关变量
        self.original_wnd_proc = None
        self.new_wnd_proc = None
        self.LRESULT = None
        self.root_handle = None
        
        # 设置现代ttk样式
        self.setup_ttk_styles()
        
        # 创建主容器
        self.main_container = tk.Frame(self.root, bg=self.colors['background'])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 使用grid布局管理器设置列权重
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, minsize=5)
        self.main_container.grid_columnconfigure(2, minsize=600, weight=0)
        self.main_container.grid_rowconfigure(0, weight=1)
        
        # 创建左侧区域（预览和图片列表）
        self.left_frame = tk.Frame(self.main_container, bg=self.colors['background'])
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # 添加分隔条
        self.separator = tk.Frame(self.main_container, bg=self.colors['border'], width=3, cursor="sb_h_double_arrow")
        self.separator.grid(row=0, column=1, sticky="ns")
        
        # 创建右侧区域（设置面板）- 设置足够的宽度
        self.right_frame = tk.Frame(self.main_container, bg=self.colors['background'], width=600)
        self.right_frame.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        
        # 实现分隔条拖动功能
        self.is_dragging = False
        
        def on_separator_click(event):
            self.is_dragging = True
            self.root.config(cursor="sb_h_double_arrow")
        
        def on_separator_drag(event):
            if self.is_dragging:
                # 获取主容器宽度
                container_width = self.main_container.winfo_width()
                # 获取鼠标在主容器中的x坐标
                x = self.main_container.winfo_pointerx() - self.main_container.winfo_rootx()
                # 确保拖动范围合理
                if x > 300 and x < container_width - 400:
                    # 调整列的最小宽度
                    self.main_container.grid_columnconfigure(0, minsize=x)
                    self.main_container.grid_columnconfigure(2, minsize=container_width - x - 3)
                    # 强制重绘
                    self.main_container.update_idletasks()
        
        def on_separator_release(event):
            self.is_dragging = False
            self.root.config(cursor="arrow")
        
        # 绑定分隔条事件
        self.separator.bind("<Button-1>", on_separator_click)
        self.root.bind("<B1-Motion>", on_separator_drag)
        self.root.bind("<ButtonRelease-1>", on_separator_release)
        
        # 在左侧区域创建滚动框架（这就是self.scrollable_frame变量）
        self.left_canvas = tk.Canvas(self.left_frame, bg=self.colors['background'], highlightthickness=0)
        self.left_scrollbar = ttk.Scrollbar(self.left_frame, orient="vertical", command=self.left_canvas.yview)
        self.left_hscrollbar = ttk.Scrollbar(self.left_frame, orient="horizontal", command=self.left_canvas.xview)
        self.scrollable_frame = tk.Frame(self.left_canvas, bg=self.colors['background'])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.left_canvas.configure(
                scrollregion=self.left_canvas.bbox("all")
            )
        )
        
        self.left_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.left_canvas.configure(yscrollcommand=self.left_scrollbar.set, xscrollcommand=self.left_hscrollbar.set)
        
        self.left_hscrollbar.pack(side="bottom", fill="x")
        self.left_scrollbar.pack(side="right", fill="y")
        self.left_canvas.pack(side="left", fill=tk.BOTH, expand=True)
        
        # 鼠标滚轮事件处理函数 - 针对左侧面板
        def _left_mousewheel(event):
            if event.delta > 0:
                self.left_canvas.yview_scroll(-1, "units")
            else:
                self.left_canvas.yview_scroll(1, "units")
            return "break"
        
        self.left_canvas.bind("<MouseWheel>", _left_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", _left_mousewheel)
        

        
        # 创建右侧区域的滚动条
        self.right_canvas = tk.Canvas(self.right_frame, bg=self.colors['background'], highlightthickness=0)
        self.right_scrollbar = ttk.Scrollbar(self.right_frame, orient="vertical", command=self.right_canvas.yview)
        self.right_hscrollbar = ttk.Scrollbar(self.right_frame, orient="horizontal", command=self.right_canvas.xview)
        self.right_scrollable_frame = tk.Frame(self.right_canvas, bg=self.colors['background'])
        
        self.right_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.right_canvas.configure(
                scrollregion=self.right_canvas.bbox("all")
            )
        )
        
        self.right_canvas.create_window((0, 0), window=self.right_scrollable_frame, anchor="nw")
        self.right_canvas.configure(yscrollcommand=self.right_scrollbar.set, xscrollcommand=self.right_hscrollbar.set)
        
        self.right_hscrollbar.pack(side="bottom", fill="x")
        self.right_scrollbar.pack(side="right", fill="y")
        self.right_canvas.pack(side="left", fill=tk.BOTH, expand=True)
        
        # 鼠标滚轮事件处理函数 - 针对右侧面板
        def _right_mousewheel(event):
            if event.delta > 0:
                self.right_canvas.yview_scroll(-1, "units")
            else:
                self.right_canvas.yview_scroll(1, "units")
            return "break"
        
        self.right_canvas.bind("<MouseWheel>", _right_mousewheel)
        self.right_scrollable_frame.bind("<MouseWheel>", _right_mousewheel)
        
        # 水印模板相关
        self.templates = {}  # 存储所有水印模板
        # 创建templates文件夹（如果不存在）
        templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
        if not os.path.exists(templates_dir):
            os.makedirs(templates_dir)
        self.template_file = os.path.join(templates_dir, 'watermark_templates.json')
        self._load_all_templates()  # 加载已保存的模板
        
        # 加载上次关闭时的设置
        self._load_settings()
        
        # 启用拖拽功能
        self.enable_drag_and_drop()
        
        # 创建主布局
        self.create_widgets()
        
        # 绑定窗口关闭事件，确保清理资源
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 为所有设置控件绑定事件，实现实时预览
        self.bind_preview_events()
        
        # 如果有上次保存的设置，应用这些设置
        if hasattr(self, 'last_settings') and self.last_settings:
            self._apply_last_settings()
        
    def setup_ttk_styles(self):
        # 设置ttk组件的样式
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        
        # 设置滚动条样式
        style.configure("Vertical.TScrollbar", 
                       troughcolor=self.colors['background'], 
                       background=self.colors['primary'],
                       arrowcolor=self.colors['primary'])
        
        # 设置标签框架样式
        style.configure("TLabelFrame", 
                       background=self.colors['background'],
                       foreground=self.colors['text'],
                       font=self.font_config['title'])
        
        # 设置组合框样式
        style.configure("TCombobox", 
                       background=self.colors['card_bg'],
                       foreground=self.colors['text'])
        
    def enable_drag_and_drop(self):
        # 启用主窗口接受拖放功能
        try:
            # 添加提示文本，告知用户可以拖拽文件
            self.drag_hint = tk.Label(self.scrollable_frame, text="提示: 您可以直接将图片拖放到窗口中进行导入", 
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
        # 首先，将所有设置相关的UI元素从左侧移到右侧
        self.move_settings_to_right()
        
        # 创建顶部按钮区域
        top_frame = tk.Frame(self.scrollable_frame, bg=self.colors['background'])
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 创建主预览窗口区域
        preview_frame = ttk.LabelFrame(self.scrollable_frame, text="预览窗口", padding=(10, 5))
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建预览画布
        self.preview_canvas = tk.Canvas(preview_frame, bg=self.colors['card_bg'], highlightthickness=1, highlightbackground=self.colors['border'])
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加提示文本
        self.preview_placeholder = self.preview_canvas.create_text(100, 100, text="请导入图片并点击列表中的图片进行预览", 
                                                                  font=self.font_config['normal'], fill=self.colors['text_light'])
        
        # 美化按钮样式
        def create_styled_button(parent, text, command, font, width=15):
            return tk.Button(parent, text=text, command=command, font=font, width=width,
                             bg=self.colors['primary'], fg='white', relief=tk.FLAT,
                             activebackground=self.colors['primary'], activeforeground='white',
                             padx=5, pady=3)
        
        # 左侧按钮组
        left_buttons_frame = tk.Frame(top_frame, bg=self.colors['background'])
        left_buttons_frame.pack(side=tk.LEFT, padx=5)
        
        import_btn = create_styled_button(left_buttons_frame, "导入图片", self.import_images, self.font_config['normal'])
        import_btn.pack(side=tk.LEFT, padx=5)
        
        import_folder_btn = create_styled_button(left_buttons_frame, "导入文件夹", self.import_folder, self.font_config['normal'])
        import_folder_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = create_styled_button(left_buttons_frame, "清空列表", self.clear_images, self.font_config['normal'])
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # 开始处理按钮 - 强调样式
        self.process_btn = tk.Button(top_frame, text="开始处理", command=self.start_processing, font=self.font_config['title'], width=15,
                                   bg=self.colors['accent'], fg='white', relief=tk.FLAT,
                                   activebackground=self.colors['accent'], activeforeground='white',
                                   padx=5, pady=5)
        self.process_btn.pack(side=tk.RIGHT, padx=5)
        

        
    def on_scale_change(self, *args):
        # 根据选择的缩放方式显示或隐藏相应的设置
        if self.scale_var.get() == "original":
            self.percent_frame.pack_forget()
            self.fixed_frame.pack_forget()
        elif self.scale_var.get() == "percent":
            self.percent_frame.pack(fill=tk.X, pady=5)
            self.fixed_frame.pack_forget()
        elif self.scale_var.get() == "fixed":
            self.percent_frame.pack_forget()
            self.fixed_frame.pack(fill=tk.X, pady=5)
        self.update_preview()
    
    def on_naming_change(self, *args):
        # 根据选择的命名方式显示或隐藏相应的设置
        if self.naming_var.get() == "original":
            self.prefix_frame.pack_forget()
            self.suffix_frame.pack_forget()
        elif self.naming_var.get() == "prefix":
            self.prefix_frame.pack(fill=tk.X, pady=5)
            self.suffix_frame.pack_forget()
        elif self.naming_var.get() == "suffix":
            self.prefix_frame.pack_forget()
            self.suffix_frame.pack(fill=tk.X, pady=5)
    
    def on_format_change(self, *args):
        # 根据选择的输出格式显示或隐藏JPEG质量设置
        if self.format_var.get() == "jpg":
            self.quality_frame.pack(fill=tk.X, pady=5)
        else:
            self.quality_frame.pack_forget()
            
    def _apply_last_settings(self):
        # 应用上次保存的设置
        if not self.last_settings:
            return
        
        try:
            settings = self.last_settings
            
            # 应用水印设置
            if 'font_size' in settings: self.font_size_var.set(settings['font_size'])
            if 'font' in settings: self.font_var.set(settings['font'])
            if 'bold' in settings: self.bold_var.set(settings['bold'])
            if 'italic' in settings: self.italic_var.set(settings['italic'])
            if 'has_shadow' in settings: self.shadow_var.set(settings['has_shadow'])
            if 'shadow_color' in settings: self.shadow_color_var.set(settings['shadow_color'])
            if 'shadow_offset' in settings: self.shadow_offset_var.set(settings['shadow_offset'])
            if 'has_stroke' in settings: self.stroke_var.set(settings['has_stroke'])
            if 'stroke_color' in settings: self.stroke_color_var.set(settings['stroke_color'])
            if 'stroke_width' in settings: self.stroke_width_var.set(settings['stroke_width'])
            if 'position' in settings: self.position_var.set(settings['position'])
            if 'text_color' in settings: 
                self.text_color_var.set(settings['text_color'])
                self.color_preview.config(bg=settings['text_color'])
            if 'opacity' in settings: self.opacity_var.set(settings['opacity'])
            if 'text_type' in settings: self.text_type_var.set(settings['text_type'])
            if 'custom_text' in settings: self.custom_text_var.set(settings['custom_text'])
            
            # 应用导出设置
            if 'output_folder' in settings: self.output_folder_var.set(settings['output_folder'])
            if 'format' in settings: self.format_var.set(settings['format'])
            if 'quality' in settings: self.quality_var.set(settings['quality'])
            
            # 应用图片尺寸设置
            if 'scale' in settings: self.scale_var.set(settings['scale'])
            if 'percent' in settings: self.percent_var.set(settings['percent'])
            if 'width' in settings: self.width_var.set(settings['width'])
            if 'height' in settings: self.height_var.set(settings['height'])
            if 'constrain' in settings: self.constrain_var.set(settings['constrain'])
            
            # 应用命名规则
            if 'naming' in settings: self.naming_var.set(settings['naming'])
            if 'prefix' in settings: self.prefix_var.set(settings['prefix'])
            if 'suffix' in settings: self.suffix_var.set(settings['suffix'])
            
            # 更新相关UI状态
            self.on_text_type_change()
            self.on_scale_change()
            self.on_naming_change()
            self.on_format_change()
            
        except Exception as e:
            print(f"应用上次设置时出错: {e}")
    
    def on_text_type_change(self, *args):
        # 根据选择的文本类型启用或禁用自定义文本输入框
        if self.text_type_var.get() == "custom":
            self.custom_text_entry.config(state="normal")
        else:
            self.custom_text_entry.config(state="disabled")
        self.update_preview()
    
    def _load_all_templates(self):
        # 加载所有已保存的水印模板
        try:
            if os.path.exists(self.template_file):
                with open(self.template_file, 'r', encoding='utf-8') as f:
                    self.templates = json.load(f)
        except Exception as e:
            print(f"加载水印模板时出错: {e}")
            self.templates = {}
            
    def _save_settings(self):
        # 保存当前设置
        try:
            # 收集所有设置
            settings = {
                # 水印设置
                'font_size': self.font_size_var.get(),
                'font': self.font_var.get(),
                'bold': self.bold_var.get(),
                'italic': self.italic_var.get(),
                'has_shadow': self.shadow_var.get(),
                'shadow_color': self.shadow_color_var.get(),
                'shadow_offset': self.shadow_offset_var.get(),
                'has_stroke': self.stroke_var.get(),
                'stroke_color': self.stroke_color_var.get(),
                'stroke_width': self.stroke_width_var.get(),
                'position': self.position_var.get(),
                'text_color': self.text_color_var.get(),
                'opacity': self.opacity_var.get(),
                'text_type': self.text_type_var.get(),
                'custom_text': self.custom_text_var.get(),
                
                # 导出设置
                'output_folder': self.output_folder_var.get(),
                'format': self.format_var.get(),
                'quality': self.quality_var.get(),
                
                # 图片尺寸设置
                'scale': self.scale_var.get(),
                'percent': self.percent_var.get(),
                'width': self.width_var.get(),
                'height': self.height_var.get(),
                'constrain': self.constrain_var.get(),
                
                # 命名规则
                'naming': self.naming_var.get(),
                'prefix': self.prefix_var.get(),
                'suffix': self.suffix_var.get()
            }
            
            # 保存设置到文件
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存设置时出错: {e}")
            
    def _load_settings(self):
        # 加载上次保存的设置
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # 应用设置（仅在对应的变量已创建后应用）
                # 注意：由于设置的加载发生在create_widgets之前，
                # 所以这些设置会在界面创建后通过其他方式应用
                # 这里我们只是保存设置到临时存储
                self.last_settings = settings
            else:
                self.last_settings = None
        except Exception as e:
            print(f"加载设置时出错: {e}")
            self.last_settings = None
    
    def _save_all_templates(self):
        # 保存所有水印模板到文件
        try:
            with open(self.template_file, 'w', encoding='utf-8') as f:
                json.dump(self.templates, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存水印模板时出错: {e}")
            messagebox.showerror("错误", f"保存水印模板失败: {e}")
    
    def _update_template_combobox(self):
        # 更新模板下拉列表
        template_names = list(self.templates.keys())
        self.template_combo['values'] = template_names
        if template_names:
            self.template_combo.current(0)
        else:
            self.template_combo.set('')
    
    def save_template(self):
        # 保存当前水印设置为模板
        template_name = self.template_name_var.get().strip()
        if not template_name:
            messagebox.showwarning("警告", "请输入模板名称")
            return
        
        # 收集所有水印参数
        template_params = {
            'font_size': self.font_size_var.get(),
            'font': self.font_var.get(),
            'bold': self.bold_var.get(),
            'italic': self.italic_var.get(),
            'has_shadow': self.shadow_var.get(),
            'shadow_color': self.shadow_color_var.get(),
            'shadow_offset': self.shadow_offset_var.get(),
            'has_stroke': self.stroke_var.get(),
            'stroke_color': self.stroke_color_var.get(),
            'stroke_width': self.stroke_width_var.get(),
            'position': self.position_var.get(),
            'text_color': self.text_color_var.get(),
            'opacity': self.opacity_var.get(),
            'text_type': self.text_type_var.get(),
            'custom_text': self.custom_text_var.get()
        }
        
        # 保存模板
        self.templates[template_name] = template_params
        self._save_all_templates()
        self._update_template_combobox()
        
        messagebox.showinfo("成功", f"模板 '{template_name}' 已保存")
        self.template_name_var.set('')
    
    def load_template(self):
        # 加载选中的模板
        template_name = self.template_combo.get()
        if not template_name or template_name not in self.templates:
            messagebox.showwarning("警告", "请选择有效的模板")
            return
        
        # 获取模板参数
        template_params = self.templates[template_name]
        
        # 应用模板参数
        self.font_size_var.set(template_params['font_size'])
        self.font_var.set(template_params['font'])
        self.bold_var.set(template_params['bold'])
        self.italic_var.set(template_params['italic'])
        self.shadow_var.set(template_params['has_shadow'])
        self.shadow_color_var.set(template_params['shadow_color'])
        self.shadow_offset_var.set(template_params['shadow_offset'])
        self.stroke_var.set(template_params['has_stroke'])
        self.stroke_color_var.set(template_params['stroke_color'])
        self.stroke_width_var.set(template_params['stroke_width'])
        self.position_var.set(template_params['position'])
        self.text_color_var.set(template_params['text_color'])
        self.opacity_var.set(template_params['opacity'])
        self.text_type_var.set(template_params['text_type'])
        self.custom_text_var.set(template_params['custom_text'])
        
        # 更新相关UI状态
        self.on_text_type_change()
        self.update_preview()
        
        messagebox.showinfo("成功", f"已加载模板 '{template_name}'")
    
    def delete_template(self):
        # 删除选中的模板
        template_name = self.template_combo.get()
        if not template_name or template_name not in self.templates:
            messagebox.showwarning("警告", "请选择有效的模板")
            return
        
        # 确认删除
        if messagebox.askyesno("确认", f"确定要删除模板 '{template_name}' 吗？"):
            del self.templates[template_name]
            self._save_all_templates()
            self._update_template_combobox()
            messagebox.showinfo("成功", f"模板 '{template_name}' 已删除")
    
    def move_settings_to_right(self):
        # 创建水印设置区域
        settings_frame = ttk.LabelFrame(self.right_scrollable_frame, text="水印设置", padding=(15, 10))
        settings_frame.pack(fill=tk.X, padx=10, pady=8)
        
        # 水印模板管理
        template_frame = tk.Frame(settings_frame)
        template_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(template_frame, text="模板名称:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.template_name_var = tk.StringVar(value='')
        self.template_name_entry = tk.Entry(template_frame, textvariable=self.template_name_var, font=self.font_config['normal'], width=15)
        self.template_name_entry.pack(side=tk.LEFT, padx=5)
        
        self.save_template_btn = tk.Button(template_frame, text="保存模板", command=self.save_template, font=self.font_config['normal'], width=10)
        self.save_template_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Label(template_frame, text="加载模板:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.template_var = tk.StringVar(value='')
        self.template_combo = ttk.Combobox(template_frame, textvariable=self.template_var, state="readonly", width=15)
        self.template_combo.pack(side=tk.LEFT, padx=5)
        self._update_template_combobox()
        
        self.load_template_btn = tk.Button(template_frame, text="加载", command=self.load_template, font=self.font_config['normal'], width=6)
        self.load_template_btn.pack(side=tk.LEFT, padx=5)
        
        self.delete_template_btn = tk.Button(template_frame, text="删除", command=self.delete_template, font=self.font_config['normal'], width=6)
        self.delete_template_btn.pack(side=tk.LEFT, padx=5)
        
        # 字体大小设置
        font_size_frame = tk.Frame(settings_frame)
        font_size_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(font_size_frame, text="字体大小:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.font_size_var = tk.IntVar(value=30)
        self.font_size_scale = tk.Scale(font_size_frame, from_=10, to=100, orient=tk.HORIZONTAL, variable=self.font_size_var, length=200)
        self.font_size_scale.pack(side=tk.LEFT, padx=5)
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
                # 添加一些常见字体作为备选
                common_fonts = ['Arial', 'Times New Roman', 'Courier New', 'Microsoft YaHei', 'SimSun', 'SimHei']
                for font in common_fonts:
                    if font not in font_names:
                        font_names.append(font)
                # 对字体列表进行排序
                font_names.sort()
            except Exception as e:
                print(f"获取系统字体列表时出错: {e}")
                # 如果出错，使用默认字体列表
                font_names = ['Arial', 'Times New Roman', 'Courier New', 'Microsoft YaHei', 'SimSun', 'SimHei']
        else:
            # 非Windows系统，使用默认字体列表
            font_names = ['Arial', 'Times New Roman', 'Courier New', 'Helvetica', 'Times', 'Courier']
        
        # 创建字体下拉列表
        self.font_combo = ttk.Combobox(font_frame, textvariable=self.font_var, values=font_names, state="readonly", width=25)
        self.font_combo.pack(side=tk.LEFT, padx=5)
        
        # 字体样式设置
        font_style_frame = tk.Frame(settings_frame)
        font_style_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(font_style_frame, text="字体样式:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        
        self.bold_var = tk.BooleanVar(value=False)
        self.italic_var = tk.BooleanVar(value=False)
        
        self.bold_check = tk.Checkbutton(font_style_frame, text="粗体", variable=self.bold_var, font=self.font_config['normal'])
        self.bold_check.pack(side=tk.LEFT, padx=10)
        
        self.italic_check = tk.Checkbutton(font_style_frame, text="斜体", variable=self.italic_var, font=self.font_config['normal'])
        self.italic_check.pack(side=tk.LEFT, padx=10)
        
        # 阴影效果设置
        shadow_frame = tk.Frame(settings_frame)
        shadow_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(shadow_frame, text="阴影效果:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        
        self.shadow_var = tk.BooleanVar(value=False)
        self.shadow_check = tk.Checkbutton(shadow_frame, text="启用阴影", variable=self.shadow_var, font=self.font_config['normal'])
        self.shadow_check.pack(side=tk.LEFT, padx=10)
        
        # 阴影颜色设置
        tk.Label(shadow_frame, text="阴影颜色:", font=self.font_config['normal'], width=8).pack(side=tk.LEFT, padx=5)
        self.shadow_color_var = tk.StringVar(value="black")
        self.shadow_color_combo = ttk.Combobox(shadow_frame, textvariable=self.shadow_color_var, 
                                          values=['black', 'white', 'gray', 'red', 'blue', 'green'], 
                                          state="readonly", width=10)
        self.shadow_color_combo.pack(side=tk.LEFT, padx=5)
        
        # 阴影偏移设置
        tk.Label(shadow_frame, text="偏移:", font=self.font_config['normal'], width=4).pack(side=tk.LEFT, padx=5)
        self.shadow_offset_var = tk.IntVar(value=2)
        self.shadow_offset_scale = tk.Scale(shadow_frame, from_=1, to=10, orient=tk.HORIZONTAL, 
                                      variable=self.shadow_offset_var, length=100)
        self.shadow_offset_scale.pack(side=tk.LEFT, padx=5)
        
        # 描边效果设置
        stroke_frame = tk.Frame(settings_frame)
        stroke_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(stroke_frame, text="描边效果:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        
        self.stroke_var = tk.BooleanVar(value=False)
        self.stroke_check = tk.Checkbutton(stroke_frame, text="启用描边", variable=self.stroke_var, font=self.font_config['normal'])
        self.stroke_check.pack(side=tk.LEFT, padx=10)
        
        # 描边颜色设置
        tk.Label(stroke_frame, text="描边颜色:", font=self.font_config['normal'], width=8).pack(side=tk.LEFT, padx=5)
        self.stroke_color_var = tk.StringVar(value="white")
        self.stroke_color_combo = ttk.Combobox(stroke_frame, textvariable=self.stroke_color_var, 
                                         values=['black', 'white', 'gray', 'red', 'blue', 'green'], 
                                         state="readonly", width=10)
        self.stroke_color_combo.pack(side=tk.LEFT, padx=5)
        
        # 描边宽度设置
        tk.Label(stroke_frame, text="宽度:", font=self.font_config['normal'], width=4).pack(side=tk.LEFT, padx=5)
        self.stroke_width_var = tk.IntVar(value=1)
        self.stroke_width_scale = tk.Scale(stroke_frame, from_=1, to=5, orient=tk.HORIZONTAL, 
                                     variable=self.stroke_width_var, length=100)
        self.stroke_width_scale.pack(side=tk.LEFT, padx=5)
        
        # 水印位置设置
        position_frame = tk.Frame(settings_frame)
        position_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(position_frame, text="水印位置:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.position_var = tk.StringVar(value="bottom-right")
        positions = ['top-left', 'top-right', 'bottom-left', 'bottom-right', 'center', 'top', 'bottom', 'left', 'right', 'custom']
        self.position_combo = ttk.Combobox(position_frame, textvariable=self.position_var, values=positions, state="readonly", width=15)
        self.position_combo.pack(side=tk.LEFT, padx=5)
        
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
                self.update_preview()
                print(f"选择了颜色: {color[1]}")
        
        self.color_btn = tk.Button(text_color_frame, text="选择颜色", command=choose_color, font=self.font_config['normal'], width=10)
        self.color_btn.pack(side=tk.LEFT, padx=5)
        
        # 添加最近使用的颜色下拉列表，保留快速选择功能
        colors = ['black', 'white', 'red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'gray', 'orange', 'purple', 'brown', 'pink']
        self.text_color_combo = ttk.Combobox(text_color_frame, textvariable=self.text_color_var, values=colors, state="readonly", width=15)
        self.text_color_combo.pack(side=tk.LEFT, padx=5)
        
        # 当从下拉列表选择颜色时，更新预览
        def update_color_preview(event):
            self.color_preview.config(bg=self.text_color_var.get())
            self.update_preview()
        
        self.text_color_combo.bind("<<ComboboxSelected>>", update_color_preview)
        
        # 文本透明度设置
        opacity_frame = tk.Frame(settings_frame)
        opacity_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(opacity_frame, text="文本透明度:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.opacity_var = tk.IntVar(value=0)  # 默认完全不透明（透明度为0）
        self.opacity_scale = tk.Scale(opacity_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.opacity_var, length=200)
        self.opacity_scale.pack(side=tk.LEFT, padx=5)
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
        
        self.date_radio = tk.Radiobutton(text_type_options, text="拍摄日期", variable=self.text_type_var, value="date", font=self.font_config['normal'])
        self.date_radio.pack(side=tk.LEFT, padx=5)
        self.custom_radio = tk.Radiobutton(text_type_options, text="自定义文本", variable=self.text_type_var, value="custom", font=self.font_config['normal'])
        self.custom_radio.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 自定义文本输入框
        self.custom_text_var = tk.StringVar(value="")
        self.custom_text_entry = tk.Entry(text_type_frame, textvariable=self.custom_text_var, font=self.font_config['normal'], width=30)
        self.custom_text_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        # 初始状态下禁用自定义文本输入框
        self.custom_text_entry.config(state="disabled")
        
        # 绑定水印类型变化事件
        self.text_type_var.trace_add("write", self.on_text_type_change)
        # 绑定自定义文本变化事件
        self.custom_text_entry.bind("<KeyRelease>", lambda event: self.update_preview())
        
        # 创建导出设置区域
        export_frame = ttk.LabelFrame(self.right_scrollable_frame, text="导出设置", padding=(10, 5))
        export_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 输出文件夹设置
        output_folder_frame = tk.Frame(export_frame)
        output_folder_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(output_folder_frame, text="输出文件夹:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.output_folder_var = tk.StringVar(value="")
        self.output_folder_entry = tk.Entry(output_folder_frame, textvariable=self.output_folder_var, font=self.font_config['normal'], width=30)
        self.output_folder_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.browse_btn = tk.Button(output_folder_frame, text="浏览...", command=self.select_output_folder, font=self.font_config['normal'], width=8)
        self.browse_btn.pack(side=tk.LEFT, padx=5)
        
        # 输出格式设置
        format_frame = tk.Frame(export_frame)
        format_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(format_frame, text="输出格式:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.format_var = tk.StringVar(value="keep")
        format_options = tk.Frame(format_frame)
        format_options.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.keep_format_radio = tk.Radiobutton(format_options, text="保留原格式", variable=self.format_var, value="keep", font=self.font_config['normal'])
        self.keep_format_radio.pack(side=tk.LEFT, padx=5)
        self.jpg_radio = tk.Radiobutton(format_options, text="JPEG", variable=self.format_var, value="jpg", font=self.font_config['normal'])
        self.jpg_radio.pack(side=tk.LEFT, padx=5)
        self.png_radio = tk.Radiobutton(format_options, text="PNG", variable=self.format_var, value="png", font=self.font_config['normal'])
        self.png_radio.pack(side=tk.LEFT, padx=5)
        self.webp_radio = tk.Radiobutton(format_options, text="WebP", variable=self.format_var, value="webp", font=self.font_config['normal'])
        self.webp_radio.pack(side=tk.LEFT, padx=5)
        
        # JPEG质量设置（仅当选择JPEG格式时显示）
        self.quality_frame = tk.Frame(export_frame)
        self.quality_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(self.quality_frame, text="JPEG质量:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.quality_var = tk.IntVar(value=90)
        self.quality_scale = tk.Scale(self.quality_frame, from_=10, to=100, orient=tk.HORIZONTAL, variable=self.quality_var, length=200)
        self.quality_scale.pack(side=tk.LEFT, padx=5)
        tk.Label(self.quality_frame, textvariable=self.quality_var, font=self.font_config['normal'], width=5).pack(side=tk.LEFT, padx=5)
        tk.Label(self.quality_frame, text="%", font=self.font_config['normal']).pack(side=tk.LEFT, padx=5)
        
        # 初始状态下隐藏JPEG质量设置
        self.quality_frame.pack_forget()
        
        # 绑定格式选择变化事件
        self.format_var.trace_add("write", self.on_format_change)
        
        # 图片尺寸设置
        size_frame = ttk.LabelFrame(self.right_scrollable_frame, text="图片尺寸设置", padding=(10, 5))
        size_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 缩放方式设置
        scale_frame = tk.Frame(size_frame)
        scale_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(scale_frame, text="缩放方式:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.scale_var = tk.StringVar(value="original")
        # 缩放方法映射 - 用于处理图片缩放
        self.resize_method_map = {
            'original': 'none',  # 保持原图大小
            'percent': 'percent',  # 按百分比缩放
            'fixed': 'width'  # 固定尺寸时按宽度缩放
        }
        # 让 resize_method_var 引用 scale_var，保持同步
        self.resize_method_var = self.scale_var
        
        scale_options = tk.Frame(scale_frame)
        scale_options.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.original_scale_radio = tk.Radiobutton(scale_options, text="保持原图大小", variable=self.scale_var, value="original", font=self.font_config['normal'])
        self.original_scale_radio.pack(side=tk.LEFT, padx=5)
        self.percent_scale_radio = tk.Radiobutton(scale_options, text="按比例缩放", variable=self.scale_var, value="percent", font=self.font_config['normal'])
        self.percent_scale_radio.pack(side=tk.LEFT, padx=5)
        self.fixed_scale_radio = tk.Radiobutton(scale_options, text="固定尺寸", variable=self.scale_var, value="fixed", font=self.font_config['normal'])
        self.fixed_scale_radio.pack(side=tk.LEFT, padx=5)
        
        # 缩放百分比设置
        self.percent_frame = tk.Frame(size_frame)
        self.percent_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(self.percent_frame, text="缩放比例:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.percent_var = tk.IntVar(value=100)
        self.percent_scale = tk.Scale(self.percent_frame, from_=10, to=200, orient=tk.HORIZONTAL, variable=self.percent_var, length=200)
        self.percent_scale.pack(side=tk.LEFT, padx=5)
        tk.Label(self.percent_frame, textvariable=self.percent_var, font=self.font_config['normal'], width=5).pack(side=tk.LEFT, padx=5)
        tk.Label(self.percent_frame, text="%", font=self.font_config['normal']).pack(side=tk.LEFT, padx=5)
        
        # 固定尺寸设置
        self.fixed_frame = tk.Frame(size_frame)
        self.fixed_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(self.fixed_frame, text="图片尺寸:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        
        width_frame = tk.Frame(self.fixed_frame)
        width_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(width_frame, text="宽:", font=self.font_config['normal']).pack(side=tk.LEFT)
        self.width_var = tk.StringVar(value="")
        self.width_entry = tk.Entry(width_frame, textvariable=self.width_var, font=self.font_config['normal'], width=8)
        self.width_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(width_frame, text="像素", font=self.font_config['normal']).pack(side=tk.LEFT)
        
        height_frame = tk.Frame(self.fixed_frame)
        height_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(height_frame, text="高:", font=self.font_config['normal']).pack(side=tk.LEFT)
        self.height_var = tk.StringVar(value="")
        self.height_entry = tk.Entry(height_frame, textvariable=self.height_var, font=self.font_config['normal'], width=8)
        self.height_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(height_frame, text="像素", font=self.font_config['normal']).pack(side=tk.LEFT)
        
        self.constrain_var = tk.BooleanVar(value=True)
        self.constrain_check = tk.Checkbutton(self.fixed_frame, text="保持比例", variable=self.constrain_var, font=self.font_config['normal'])
        self.constrain_check.pack(side=tk.LEFT, padx=10)
        
        # 初始状态下隐藏缩放比例和固定尺寸设置
        self.percent_frame.pack_forget()
        self.fixed_frame.pack_forget()
        
        # 绑定缩放方式变化事件
        self.scale_var.trace_add("write", self.on_scale_change)
        
        # 命名规则设置
        naming_frame = ttk.LabelFrame(self.right_scrollable_frame, text="命名规则", padding=(10, 5))
        naming_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(naming_frame, text="命名方式:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.naming_var = tk.StringVar(value="original")
        naming_options = tk.Frame(naming_frame)
        naming_options.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.original_name_radio = tk.Radiobutton(naming_options, text="保留原名", variable=self.naming_var, value="original", font=self.font_config['normal'])
        self.original_name_radio.pack(side=tk.LEFT, padx=5)
        self.prefix_radio = tk.Radiobutton(naming_options, text="添加前缀", variable=self.naming_var, value="prefix", font=self.font_config['normal'])
        self.prefix_radio.pack(side=tk.LEFT, padx=5)
        self.suffix_radio = tk.Radiobutton(naming_options, text="添加后缀", variable=self.naming_var, value="suffix", font=self.font_config['normal'])
        self.suffix_radio.pack(side=tk.LEFT, padx=5)
        
        # 前缀输入框
        self.prefix_frame = tk.Frame(naming_frame)
        self.prefix_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(self.prefix_frame, text="前缀文本:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.prefix_var = tk.StringVar(value="watermark_")
        self.prefix_entry = tk.Entry(self.prefix_frame, textvariable=self.prefix_var, font=self.font_config['normal'], width=30)
        self.prefix_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 后缀输入框
        self.suffix_frame = tk.Frame(naming_frame)
        self.suffix_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(self.suffix_frame, text="后缀文本:", font=self.font_config['normal'], width=10).pack(side=tk.LEFT, padx=5)
        self.suffix_var = tk.StringVar(value="_watermark")
        self.suffix_entry = tk.Entry(self.suffix_frame, textvariable=self.suffix_var, font=self.font_config['normal'], width=30)
        self.suffix_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 初始状态下隐藏前缀和后缀输入框
        self.prefix_frame.pack_forget()
        self.suffix_frame.pack_forget()
        
        # 绑定命名方式变化事件
        self.naming_var.trace_add("write", self.on_naming_change)
        
        # 添加实时预览功能的事件绑定
        # 字体大小变化
        self.font_size_scale.bind("<Motion>", lambda event: self.update_preview())
        # 字体选择变化
        self.font_combo.bind("<<ComboboxSelected>>", lambda event: self.update_preview())
        # 字体样式变化
        self.bold_var.trace_add("write", lambda *args: self.update_preview())
        self.italic_var.trace_add("write", lambda *args: self.update_preview())
        # 阴影效果变化
        self.shadow_var.trace_add("write", lambda *args: self.update_preview())
        self.shadow_color_combo.bind("<<ComboboxSelected>>", lambda event: self.update_preview())
        self.shadow_offset_scale.bind("<Motion>", lambda event: self.update_preview())
        # 描边效果变化
        self.stroke_var.trace_add("write", lambda *args: self.update_preview())
        self.stroke_color_combo.bind("<<ComboboxSelected>>", lambda event: self.update_preview())
        self.stroke_width_scale.bind("<Motion>", lambda event: self.update_preview())
        # 水印位置变化
        self.position_combo.bind("<<ComboboxSelected>>", lambda event: self.update_preview())
        # 文本透明度变化
        self.opacity_scale.bind("<Motion>", lambda event: self.update_preview())
        
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
        
        # 创建图片列表区域
        list_frame = ttk.LabelFrame(self.scrollable_frame, text="已导入图片", padding=(10, 5))
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建滚动区域（使用不同的变量名避免覆盖主区域的canvas和scrollable_frame）
        self.list_canvas = tk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.list_canvas.yview)
        hscrollbar = ttk.Scrollbar(list_frame, orient="horizontal", command=self.list_canvas.xview)
        self.list_scrollable_frame = tk.Frame(self.list_canvas)
        
        self.list_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.list_canvas.configure(
                scrollregion=self.list_canvas.bbox("all")
            )
        )
        

        
        self.list_canvas.create_window((0, 0), window=self.list_scrollable_frame, anchor="nw")
        self.list_canvas.configure(yscrollcommand=scrollbar.set, xscrollcommand=hscrollbar.set)
        
        hscrollbar.pack(side="bottom", fill="x")
        scrollbar.pack(side="right", fill="y")
        self.list_canvas.pack(side="left", fill="both", expand=True)
        
        # 进度条
        progress_frame = tk.Frame(self.scrollable_frame)
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
            item_frame = tk.Frame(self.list_scrollable_frame, bd=1, relief=tk.RAISED, cursor="hand2")
            item_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # 为图片项添加点击事件
            img_index = len(self.image_paths) - 1  # 当前图片的索引
            item_frame.bind("<Button-1>", lambda event, index=img_index: self.select_image_for_preview(index))
            
            # 添加缩略图
            img_label = tk.Label(item_frame, image=thumbnail, cursor="hand2")
            img_label.pack(side=tk.LEFT, padx=5, pady=5)
            img_label.bind("<Button-1>", lambda event, index=img_index: self.select_image_for_preview(index))
            
            # 添加文件名和路径
            file_name = os.path.basename(file_path)
            path_label = tk.Label(item_frame, text=file_path, font=self.font_config['normal'], wraplength=600, justify=tk.LEFT, cursor="hand2")
            path_label.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
            path_label.bind("<Button-1>", lambda event, index=img_index: self.select_image_for_preview(index))
            
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
        # 更新预览
        self.update_preview()
        
    def process_images(self):
        # 处理所有图片
        success_count = 0
        fail_count = 0
        
        for i, img_path in enumerate(self.image_paths):
            try:
                # 处理图片
                current_position = self.position_var.get()
                print(f"process_images中获取position_var: {current_position}")
                success = self.add_watermark_to_image(
                    img_path,
                    self.output_folder_var.get(),
                    self.font_size_var.get(),
                    self.text_color_var.get(),
                    'white',  # 背景颜色默认值（不再使用）
                    current_position,
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
        # 保存设置
        self._save_settings()
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
    
    def bind_preview_events(self):
        # 为所有水印设置控件绑定事件，实现实时预览
        # 字体大小变化
        self.font_size_scale.bind("<Motion>", lambda event: self.update_preview())
        self.font_size_scale.bind("<ButtonRelease-1>", lambda event: self.update_preview())
        
        # 字体选择变化
        self.font_combo.bind("<<ComboboxSelected>>", lambda event: self.update_preview())
        
        # 字体样式变化
        self.bold_var.trace_add("write", lambda *args: self.update_preview())
        self.italic_var.trace_add("write", lambda *args: self.update_preview())
        
        # 阴影效果变化
        self.shadow_var.trace_add("write", lambda *args: self.update_preview())
        self.shadow_color_combo.bind("<<ComboboxSelected>>", lambda event: self.update_preview())
        self.shadow_offset_scale.bind("<Motion>", lambda event: self.update_preview())
        self.shadow_offset_scale.bind("<ButtonRelease-1>", lambda event: self.update_preview())
        
        # 描边效果变化
        self.stroke_var.trace_add("write", lambda *args: self.update_preview())
        self.stroke_color_combo.bind("<<ComboboxSelected>>", lambda event: self.update_preview())
        self.stroke_width_scale.bind("<Motion>", lambda event: self.update_preview())
        self.stroke_width_scale.bind("<ButtonRelease-1>", lambda event: self.update_preview())
        
        # 水印位置变化
        self.position_combo.bind("<<ComboboxSelected>>", lambda event: self.update_preview())
        
        # 文本透明度变化
        self.opacity_scale.bind("<Motion>", lambda event: self.update_preview())
        self.opacity_scale.bind("<ButtonRelease-1>", lambda event: self.update_preview())
        
        # 水印类型变化已在on_text_type_change中处理
        # 自定义文本变化已在绑定中处理
    
    def select_image_for_preview(self, index):
        # 选择图片进行预览
        if 0 <= index < len(self.image_paths):
            self.current_preview_index = index
            # 高亮显示选中的图片项
            self.highlight_selected_item(index)
            # 更新预览
            self.update_preview()
    
    def highlight_selected_item(self, index):
        # 高亮显示选中的图片项
        children = self.scrollable_frame.winfo_children()
        for i, child in enumerate(children):
            if i == index:
                # 使用try-except处理ttk组件和普通组件的差异
                try:
                    child.config(bg="#e0e0e0")  # 尝试设置普通tk组件的背景色
                except tk.TclError:
                    # 如果是ttk组件，使用style方法（或其他适合的方式）
                    try:
                        child.state(['selected'])
                    except:
                        pass  # 忽略无法设置选中状态的组件
            else:
                # 未选中状态
                try:
                    child.config(bg=self.scrollable_frame.cget("bg"))  # 普通tk组件
                except tk.TclError:
                    # ttk组件
                    try:
                        child.state(['!selected'])
                    except:
                        pass  # 忽略无法设置状态的组件
    
    def update_preview(self):
        # 更新预览窗口
        if self.current_preview_index < 0 or self.current_preview_index >= len(self.image_paths):
            return
        
        try:
            image_path = self.image_paths[self.current_preview_index]
            # 获取原始图片和水印文本
            img = Image.open(image_path)
            width, height = img.size
            
            # 获取画布尺寸
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            # 如果画布还没有尺寸，使用默认值
            if canvas_width < 100:  # 避免初始宽度为0
                canvas_width = 800
            if canvas_height < 100:  # 避免初始高度为0
                canvas_height = 600
            
            # 计算缩放比例，保持原图比例
            ratio = min(canvas_width / width, canvas_height / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            # 调整图像大小
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            self.preview_photo = ImageTk.PhotoImage(resized_img)
            
            # 清除画布并显示新图像
            self.preview_canvas.delete("all")
            x = (canvas_width - new_width) // 2
            y = (canvas_height - new_height) // 2
            self.preview_canvas.create_image(x, y, image=self.preview_photo, anchor=tk.NW, tags="image")
            
            # 绘制可拖动的水印文本
            self.draw_draggable_watermark(x, y, ratio, width, height)
            
            # 绑定鼠标事件以支持拖动
            self.preview_canvas.bind("<Button-1>", self.on_watermark_click)
            self.preview_canvas.bind("<B1-Motion>", self.on_watermark_drag)
            self.preview_canvas.bind("<ButtonRelease-1>", self.on_watermark_release)
            
        except Exception as e:
            print(f"更新预览时出错: {e}")
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(canvas_width//2 if 'canvas_width' in locals() else 400, 
                                          canvas_height//2 if 'canvas_height' in locals() else 300, 
                                          text=f"预览失败: {str(e)}", 
                                          font=self.font_config['normal'], fill="red")
    
    def draw_draggable_watermark(self, img_x, img_y, ratio, orig_width, orig_height):
        """绘制可拖动的水印文本"""
        try:
            # 获取水印文本
            text_type = self.text_type_var.get()
            if text_type == "custom":
                watermark_text = self.custom_text_var.get().strip()
                if not watermark_text:
                    watermark_text = self.get_exif_datetime(self.image_paths[self.current_preview_index])
                    if not watermark_text:
                        mtime = os.path.getmtime(self.image_paths[self.current_preview_index])
                        dt = datetime.fromtimestamp(mtime)
                        watermark_text = dt.strftime('%Y-%m-%d')
            else:
                watermark_text = self.get_exif_datetime(self.image_paths[self.current_preview_index])
                if not watermark_text:
                    mtime = os.path.getmtime(self.image_paths[self.current_preview_index])
                    dt = datetime.fromtimestamp(mtime)
                    watermark_text = dt.strftime('%Y-%m-%d')
            
            # 计算水印位置
            margin = 10 * ratio
            font_size = int(self.font_size_var.get() * ratio)
            
            # 尝试创建字体
            font = None
            try:
                selected_font = self.font_var.get()
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
                
                if sys.platform.startswith('win'):
                    font_dir = 'C:\\Windows\\Fonts'
                    if selected_font in common_font_paths:
                        font_file = common_font_paths[selected_font]
                        font_path = os.path.join(font_dir, font_file)
                        if os.path.exists(font_path):
                            try:
                                font = ImageFont.truetype(font_path, font_size)
                            except:
                                pass
                    else:
                        if 'Arial' in common_font_paths:
                            font_file = common_font_paths['Arial']
                            font_path = os.path.join(font_dir, font_file)
                            if os.path.exists(font_path):
                                try:
                                    font = ImageFont.truetype(font_path, font_size)
                                except:
                                    pass
                
                if font is None:
                    from PIL import ImageFont
                    font = ImageFont.load_default()
            except:
                font = None
            
            # 获取文本尺寸
            if font:
                bbox = font.getbbox(watermark_text)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                # 估计文本尺寸
                text_width = len(watermark_text) * font_size * 0.6
                text_height = font_size
            
            # 检查位置是否为自定义
            position = self.position_var.get()
            if position == "custom" and self.custom_watermark_position:
                # 使用自定义位置（相对坐标）
                rel_x, rel_y = self.custom_watermark_position
                # 将相对位置转换为绝对位置（水印左上角坐标）
                x = (orig_width * ratio) * rel_x - text_width // 2
                y = (orig_height * ratio) * rel_y - text_height // 2
            else:
                # 根据选择的预设位置计算
                if position == 'top-left':
                    x, y = margin, margin
                elif position == 'top-right':
                    x, y = orig_width * ratio - text_width - margin, margin
                elif position == 'bottom-left':
                    x, y = margin, orig_height * ratio - text_height - margin
                elif position == 'bottom-right':
                    x, y = orig_width * ratio - text_width - margin, orig_height * ratio - text_height - margin
                elif position == 'center':
                    x, y = (orig_width * ratio - text_width) // 2, (orig_height * ratio - text_height) // 2
                elif position == 'top':
                    x, y = (orig_width * ratio - text_width) // 2, margin
                elif position == 'bottom':
                    x, y = (orig_width * ratio - text_width) // 2, orig_height * ratio - text_height - margin
                elif position == 'left':
                    x, y = margin, (orig_height * ratio - text_height) // 2
                elif position == 'right':
                    x, y = orig_width * ratio - text_width - margin, (orig_height * ratio - text_height) // 2
                else:
                    # 默认右下角
                    x, y = orig_width * ratio - text_width - margin, orig_height * ratio - text_height - margin
                
                # 只有在用户明确选择预设位置时才清除自定义位置
                if hasattr(self, 'custom_watermark_position') and position != "custom":
                    self.custom_watermark_position = None
            
            # 应用画布偏移
            x += img_x
            y += img_y
            
            # 设置文本样式
            fill_color = self.text_color_var.get()
            font_style = 'normal'
            if self.bold_var.get():
                font_style = 'bold'
            if self.italic_var.get():
                if font_style == 'bold':
                    font_style = 'bold italic'
                else:
                    font_style = 'italic'
            
            # 创建文本标签
            self.watermark_text_id = self.preview_canvas.create_text(
                x + text_width/2, y + text_height/2, 
                text=watermark_text,
                font=("SimHei", font_size, font_style),
                fill=fill_color,
                tags="watermark"
            )
            
            # 应用透明度效果（通过创建多个半透明图层模拟）
            opacity = self.opacity_var.get()
            if opacity > 0:
                alpha = 1.0 - opacity / 100.0
                for i in range(1, 5):
                    if i * alpha >= 1:
                        break
                    self.preview_canvas.create_text(
                        x + text_width/2, y + text_height/2, 
                        text=watermark_text,
                        font=("SimHei", font_size, font_style),
                        fill=fill_color,
                        stipple="gray{}%" if alpha < 1 else fill_color,
                        tags="watermark_transparent"
                    )
            
        except Exception as e:
            print(f"绘制可拖动水印时出错: {e}")
            
    def on_watermark_click(self, event):
        """处理水印点击事件"""
        # 检查点击是否在水印文本上
        item = self.preview_canvas.find_closest(event.x, event.y)[0]
        if self.watermark_text_id and item == self.watermark_text_id:
            self.is_dragging_watermark = True
            # 记录点击位置与水印中心的偏移量
            x, y = self.preview_canvas.coords(self.watermark_text_id)
            self.drag_offset_x = x - event.x
            self.drag_offset_y = y - event.y
            self.preview_canvas.config(cursor="fleur")
            # 设置位置为自定义
            self.position_var.set("custom")
    
    def on_watermark_drag(self, event):
        """处理水印拖动事件"""
        if self.is_dragging_watermark and self.watermark_text_id:
            # 计算新位置
            new_x = event.x + self.drag_offset_x
            new_y = event.y + self.drag_offset_y
            
            # 获取画布上图像的位置和大小
            img_item = self.preview_canvas.find_withtag("image")
            if img_item:
                # 这里假设图像是第一个创建的对象
                img_bbox = self.preview_canvas.bbox(img_item[0])
                img_x, img_y, img_right, img_bottom = img_bbox
            else:
                # 如果找不到图像，使用画布边界
                img_x, img_y = 0, 0
                img_right = self.preview_canvas.winfo_width()
                img_bottom = self.preview_canvas.winfo_height()
            
            # 限制水印在图像/画布范围内
            # 这里简化处理，仅限制中心位置不超出边界
            new_x = max(img_x + 20, min(img_right - 20, new_x))
            new_y = max(img_y + 20, min(img_bottom - 20, new_y))
            
            # 更新水印位置
            self.preview_canvas.coords(self.watermark_text_id, new_x, new_y)
            # 同时更新所有透明度效果图层
            for item in self.preview_canvas.find_withtag("watermark_transparent"):
                self.preview_canvas.coords(item, new_x, new_y)
    
    def on_watermark_release(self, event):
        """处理水印释放事件"""
        print("触发on_watermark_release事件")
        if self.is_dragging_watermark and self.watermark_text_id:
            print(f"is_dragging_watermark: {self.is_dragging_watermark}, watermark_text_id: {self.watermark_text_id}")
            # 保存自定义位置（相对于原始图像的比例位置）
            # 获取画布上图像的位置和大小
            img_item = self.preview_canvas.find_withtag("image")
            print(f"img_item: {img_item}")
            if img_item:
                print("找到图像项，开始计算位置")
                img_bbox = self.preview_canvas.bbox(img_item[0])
                print(f"img_bbox原始值: {img_bbox}")
                img_x, img_y, img_width, img_height = img_bbox
                img_width -= img_x
                img_height -= img_y
                print(f"图像尺寸: 宽={img_width}, 高={img_height}")
                
                # 获取水印中心位置
                watermark_coords = self.preview_canvas.coords(self.watermark_text_id)
                print(f"水印坐标原始值: {watermark_coords}")
                if len(watermark_coords) >= 2:
                    watermark_x, watermark_y = watermark_coords
                    print(f"水印中心位置: x={watermark_x}, y={watermark_y}")
                    
                    # 转换为相对于原始图像的比例位置
                    rel_x = (watermark_x - img_x) / img_width
                    rel_y = (watermark_y - img_y) / img_height
                    print(f"计算得到的相对位置: rel_x={rel_x}, rel_y={rel_y}")
                    
                    # 保存比例位置，以便在缩放时保持相对位置
                    self.custom_watermark_position = (rel_x, rel_y)
                    print(f"保存自定义位置: {self.custom_watermark_position}")
                    
                    # 设置位置为自定义，确保预览和处理图片时使用此位置
                    self.position_var.set("custom")
                    print(f"设置position_var为: custom")
            
            self.is_dragging_watermark = False
            self.preview_canvas.config(cursor="arrow")
    
    def generate_preview_image(self, image_path):
        # 生成带水印的预览图像
        try:
            # 打开图片
            img = Image.open(image_path)
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
                
                # 预定义常见字体及其文件路径映射
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
                                font = ImageFont.truetype(font_path, self.font_size_var.get())
                            except (IOError, OSError):
                                pass
                    else:
                        # 尝试使用Arial作为默认替代字体
                        if 'Arial' in common_font_paths:
                            font_file = common_font_paths['Arial']
                            font_path = os.path.join(font_dir, font_file)
                            if os.path.exists(font_path):
                                try:
                                    font = ImageFont.truetype(font_path, self.font_size_var.get())
                                except (IOError, OSError):
                                    pass
                
                # 如果前面都失败，使用PIL默认字体
                if font is None:
                    font = ImageFont.load_default()
            except Exception:
                # 出现任何异常，都使用默认字体
                font = ImageFont.load_default()
            
            # 获取文本大小
            bbox = font.getbbox(watermark_text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # 计算水印位置
            margin = 10
            position = self.position_var.get()
            
            # 检查是否为自定义位置
            if position == "custom" and self.custom_watermark_position:
                # 使用自定义位置（相对坐标）
                rel_x, rel_y = self.custom_watermark_position
                # 将相对位置转换为绝对位置（水印左上角坐标）
                x = width * rel_x - text_width // 2
                y = height * rel_y - text_height // 2
            else:
                # 根据选择的预设位置计算
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
            
            # 解析颜色并应用透明度
            text_color_rgba = self.parse_color(self.text_color_var.get(), text_opacity)
            
            # 创建一个透明图层用于绘制水印
            watermark_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
            watermark_draw = ImageDraw.Draw(watermark_layer)
            
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
            
            return img
        except Exception as e:
            print(f"生成预览图像时出错: {e}")
            raise
    
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
            
            # 添加调试信息
            print(f"当前position参数: {position}")
            print(f"当前custom_watermark_position: {self.custom_watermark_position if hasattr(self, 'custom_watermark_position') else '未定义'}")
            print(f"当前position_var值: {self.position_var.get()}")
            
            # 检查是否有自定义位置
            if hasattr(self, 'custom_watermark_position') and self.custom_watermark_position and position == 'custom':
                # 使用用户通过拖拽设置的自定义位置
                rel_x, rel_y = self.custom_watermark_position
                # 将相对位置转换为绝对位置（水印中心坐标）
                center_x = int(width * rel_x)
                center_y = int(height * rel_y)
                # 计算水印左上角位置
                x = center_x - text_width // 2
                y = center_y - text_height // 2
                print(f"使用自定义位置: ({rel_x}, {rel_y}) -> 绝对位置: ({x}, {y})")
            else:
                # 使用预设位置
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
    
    # 绑定画布大小变化事件，更新预览
    def on_canvas_resize(event):
        app.update_preview()
    
    root.bind("<Configure>", on_canvas_resize)
    
    # 启动主循环
    root.mainloop()