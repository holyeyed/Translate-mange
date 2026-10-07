import base64
import io
import os
import textwrap
import threading
import tkinter as tk
import shutil
from tkinter import ttk  
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk
from PIL import ImageFilter 
from google import genai
from dotenv import load_dotenv
load_dotenv()

API_KEY=os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-3.1-flash-lite"

def get_styled_font(font_size=18, is_bold=False, is_italic=False):
    """Tự động chọn file font tương ứng với Style (Regular, Bold, Italic, Bold-Italic)"""
    font_dir = "C:\\Windows\\Fonts\\"

    if is_bold and is_italic:
        font_files = ["arialbi.ttf", "calibriz.ttf"]
    elif is_bold:
        font_files = ["arialbd.ttf", "calibrib.ttf", "arial.ttf"]
    elif is_italic:
        font_files = ["ariali.ttf", "calibrii.ttf", "arial.ttf"]
    else:
        font_files = ["arial.ttf", "calibri.ttf"]

    for file in font_files:
        try:
            return ImageFont.truetype(font_dir + file, font_size)
        except:
            try:
                return ImageFont.truetype(file, font_size)
            except:
                continue

    return ImageFont.load_default()


class MangaTranslatorApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Manga Translator Pro")
        # ---------------------------------------------------------
        # THANH CÔNG CỤ (TOOLBAR)
        # ---------------------------------------------------------
        panel = tk.Frame(root)
        panel.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        tk.Button(panel, text="📁 Chọn thư mục",font=("Tahoma",11), command=self.load_folder).pack(side=tk.LEFT, padx=5)
        # DROPDOWN CHỌN MODEL
        tk.Label(panel, text=" | 🤖 Model:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=2)
        # Giá trị mặc định ban đầu khi chờ nạp danh sách
        self.cb_model = ttk.Combobox(
            panel, 
            values=["gemini-flash-lite-latest"], 
            state="readonly",
            font=("Tahoma",11),
            width=25
        )
        self.cb_model.set("gemini-flash-lite-latest")
        self.cb_model.pack(side=tk.LEFT, padx=2)
        # Nút để tải/làm mới danh sách models từ API
        tk.Button(panel, text="🔄 Reload Models",font=("Tahoma",11), command=self.fetch_models_async).pack(side=tk.LEFT, padx=2)
        # Nạp danh sách model ngầm ngay khi mở ứng dụng
        self.fetch_models_async()
        # ---------------------------------------------------------
        # CÔNG CỤ CHỌN (RECTANGLE / LASSO)
        # ---------------------------------------------------------
        tk.Label(panel, text=" | Công cụ:", font=("Arial", 9, "bold")).pack(
            side=tk.LEFT, padx=2
        )
        self.tool_mode = tk.StringVar(value="rect")
        rb_rect = tk.Radiobutton(
            panel,
            text="🔲 Chữ nhật",
            variable=self.tool_mode,
            font=("Tahoma",11),
            value="rect",
            indicatoron=0,
            padx=6,
            pady=2,
        )
        rb_rect.pack(side=tk.LEFT, padx=2)

        rb_lasso = tk.Radiobutton(
            panel,
            text="✏️ Lasso",
            variable=self.tool_mode,
            font=("Tahoma",11),
            value="lasso",
            indicatoron=0,
            padx=6,
            pady=2,
        )
        rb_lasso.pack(side=tk.LEFT, padx=2)
        self.is_blurred = tk.BooleanVar(value=False)
        def on_toggle_blur():
            self.show_image() 

        chk_blur = tk.Checkbutton(
            panel,
            text="🔒 Mờ ảnh ảo",
            variable=self.is_blurred,
            font=("Tahoma",11),
            command=on_toggle_blur,
            indicatoron=0,
            padx=8,
            pady=2
        )
        chk_blur.pack(side=tk.LEFT, padx=5)

        # NÚT CHUYỂN TRANG
        self.btn_prev = tk.Button(
            panel,
            text="◀ Ảnh trước",
            font=("Tahoma",11),
            command=self.prev_image,
            state=tk.DISABLED,
        )
        self.btn_prev.pack(side=tk.LEFT, padx=(15, 2))
        self.btn_next = tk.Button(
            panel, text="Ảnh sau ▶",font=("Tahoma",11), command=self.next_image, state=tk.DISABLED
        )
        self.btn_next.pack(side=tk.LEFT, padx=2)

        self.lbl_info = tk.Label(
            panel,
            font=("Tahoma",11),
            text="Chọn công cụ rồi kéo chuột chọn vùng thoại.",
            fg="blue",
        )
        self.lbl_info.pack(side=tk.LEFT, padx=10)

        # Frame chứa Canvas và 2 thanh cuộn
        canvas_frame = tk.Frame(root)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        # Tạo Scrollbar Dọc và Ngang
        self.v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.h_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Kết nối Canvas với Scrollbar
        self.canvas = tk.Canvas(
            canvas_frame,
            cursor="cross",
            yscrollcommand=self.v_scrollbar.set,
            xscrollcommand=self.h_scrollbar.set,
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.v_scrollbar.config(command=self.canvas.yview)
        self.h_scrollbar.config(command=self.canvas.xview)

        # Thêm tính năng cuộn bằng con trỏ chuột (Mousewheel)
        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

        # Biến quản lý trạng thái tự động cuộn
        self.autoscroll_active = False
        self.last_event_x = 0
        self.last_event_y = 0

        # Lắng nghe sự kiện chuột
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        
    def fetch_models_async(self):
        """Khởi chạy thread ngầm để gọi models.list() không làm đơ UI"""
        threading.Thread(target=self._async_get_models, daemon=True).start()

    def _async_get_models(self):
        try:
            # Gọi API lấy toàn bộ danh sách model
            model_list = []
            for m in client.models.list():
                name = m.name.replace("models/", "")
                if "gemini" in name:
                    model_list.append(name)
            
            # Sắp xếp danh sách cho dễ nhìn
            model_list.sort()
            # Cập nhật danh sách lên Combobox ở Main Thread
            if model_list:
                self.root.after(0, lambda: self._update_model_combobox(model_list))

        except Exception as e:
            print(f"Không thể lấy danh sách models: {e}")

    def _update_model_combobox(self, model_list):
        current_selection = self.cb_model.get()
        self.cb_model['values'] = model_list
        
        # Giữ lại lựa chọn cũ nếu nó có trong danh sách mới, nếu không chọn model lite mặc định
        if current_selection in model_list:
            self.cb_model.set(current_selection)
        elif "gemini-flash-lite-latest" in model_list:
            self.cb_model.set("gemini-flash-lite-latest")
        else:
            self.cb_model.set(model_list[0])

    def load_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        valid_exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
        self.image_files = [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith(valid_exts)
        ]
        self.image_files.sort()
        if self.image_files:
            self.current_index = 0
            self.btn_prev.config(state=tk.NORMAL)
            self.btn_next.config(state=tk.NORMAL)
            self.show_image()

    def show_image(self):
        path = self.image_files[self.current_index]
        self.lbl_info.config(
            text=f"Trang {self.current_index + 1}/{len(self.image_files)}: {os.path.basename(path)}"
        )
        self.pil_image = Image.open(path).convert("RGB")
        self.tk_image = ImageTk.PhotoImage(self.pil_image)
        if not self.pil_image:
            return

        # Tạo bản sao từ ảnh gốc để xử lý hiển thị
        display_img = self.pil_image.copy()

        # Nếu đang BẬT chế độ làm mờ
        if hasattr(self, 'is_blurred') and self.is_blurred.get():
            display_img = display_img.filter(ImageFilter.GaussianBlur(radius=2))

        # Chuyển đổi sang PhotoImage để vẽ lên Canvas như bình thường
        self.tk_image = ImageTk.PhotoImage(display_img)
        self.canvas.config(scrollregion=(0, 0, display_img.width, display_img.height))
        
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

    # ---------------------------------------------------------
    # XỬ LÝ SỰ KIỆN KÉO CHUỘT (HỖ TRỢ CẢ RECT DẪN LASSO)
    # ---------------------------------------------------------
    def on_button_press(self, event):
        self.canvas.delete("selection")
        real_x = self.canvas.canvasx(event.x)
        real_y = self.canvas.canvasy(event.y)

        self.start_x = real_x
        self.start_y = real_y

        if self.tool_mode.get() == "lasso":
            self.points = [(real_x, real_y)]

        # Lưu lại sự kiện ban đầu
        self.last_event_x = event.x
        self.last_event_y = event.y

        # Bật cờ Auto-scroll
        if not self.autoscroll_active:
            self.autoscroll_active = True
            self.auto_scroll_loop()

    def on_move_press(self, event):
        # Cập nhật vị trí chuột mới nhất
        self.last_event_x = event.x
        self.last_event_y = event.y

        # Cập nhật hình vẽ nét chọn ngay lập tức
        self.update_selection_draw()

    def auto_scroll_loop(self):
        """Vòng lặp ngầm kiểm tra chuột có sát mép màn hình không để cuộn Canvas"""
        if not self.autoscroll_active:
            return

        margin = 20
        scroll_step = 15  # Tốc độ cuộn

        canv_w = self.canvas.winfo_width()
        canv_h = self.canvas.winfo_height()

        x = self.last_event_x
        y = self.last_event_y

        scrolled = False

        # Kiểm tra và cuộn Dọc (Lên/Xuống)
        if y < margin:
            self.canvas.yview_scroll(-1 * scroll_step, "units")
            scrolled = True
        elif y > canv_h - margin:
            self.canvas.yview_scroll(scroll_step, "units")
            scrolled = True

        # Kiểm tra và cuộn Ngang (Trái/Phải)
        if x < margin:
            self.canvas.xview_scroll(-1 * scroll_step, "units")
            scrolled = True
        elif x > canv_w - margin:
            self.canvas.xview_scroll(scroll_step, "units")
            scrolled = True

        # Nếu có cuộn, vẽ lại ngay đường Lasso/Rect theo tọa độ thực tế mới
        if scrolled:
            self.update_selection_draw()

        # Tiếp tục vòng lặp sau 30ms nếu vẫn đang giữ chuột
        self.root.after(30, self.auto_scroll_loop)

    def update_selection_draw(self):
        """Cập nhật nét vẽ Lasso / Rect dựa trên tọa độ thực mới nhất"""
        cur_x = self.canvas.canvasx(self.last_event_x)
        cur_y = self.canvas.canvasy(self.last_event_y)

        if self.tool_mode.get() == "rect":
            self.canvas.delete("selection")
            self.canvas.create_rectangle(
                self.start_x,
                self.start_y,
                cur_x,
                cur_y,
                outline="red",
                width=2,
                tags="selection",
            )
        else:
            # Thêm điểm mới vào danh sách Lasso nếu khác tọa độ cuối
            if not self.points or (cur_x, cur_y) != self.points[-1]:
                self.points.append((cur_x, cur_y))
                if len(self.points) > 1:
                    self.canvas.create_line(
                        self.points[-2],
                        self.points[-1],
                        fill="red",
                        width=2,
                        tags="selection",
                    )

    def on_button_release(self, event):
        # Tắt vòng lặp Auto-scroll khi thả chuột
        self.autoscroll_active = False

        # Cập nhật vị trí cuối cùng
        self.last_event_x = event.x
        self.last_event_y = event.y

        # Thực hiện các bước xử lý crop & dịch như cũ của bạn
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)

        if self.tool_mode.get() == "rect":
            x1, x2 = min(self.start_x, end_x), max(self.start_x, end_x)
            y1, y2 = min(self.start_y, end_y), max(self.start_y, end_y)

            if (x2 - x1) < 10 or (y2 - y1) < 10:
                self.canvas.delete("selection")
                return

            points = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        else:
            if len(self.points) < 5:
                self.canvas.delete("selection")
                return
            points = list(self.points)

        self.lbl_info.config(text="⏳ Đang gửi request tới Gemini...")
        threading.Thread(
            target=self._async_process_crop, args=(points,), daemon=True
        ).start()
    # ---------------------------------------------------------
    # XỬ LÝ BACKGROUND & EDITOR
    # ---------------------------------------------------------
    def _async_process_crop(self, points):
        # Lấy model đang chọn từ Dropdown
        selected_model = self.cb_model.get()

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)

        cropped_img = self.pil_image.crop((x1, y1, x2, y2))
        prompt = "Dịch chữ trong ảnh sang tiếng Việt mượt mà hợp truyện tranh. Chỉ trả về bản dịch."

        try:
            # Gọi API với model đã chọn
            response = client.models.generate_content(
                model=selected_model, contents=[prompt, cropped_img]
            )
            raw_text = response.text.strip()
        except Exception as e:
            err_msg = str(e)
            # Thông báo gợi ý đổi model nếu gặp 503
            if "503" in err_msg or "UNAVAILABLE" in err_msg:
                self.root.after(
                    0,
                    lambda: messagebox.showwarning(
                        "Server Bận (503)",
                        f"Model '{selected_model}' đang quá tải.\nHãy thử đổi sang model khác trên thanh công cụ!",
                    ),
                )
            else:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Lỗi API", f"Chi tiết: {err_msg}"
                    ),
                )

            self.root.after(0, self.show_image)
            return

        # Mở Popup biên tập ở Main Thread
        self.root.after(
            0, lambda: self.open_custom_editor(raw_text, points, x1, y1, x2, y2)
        )

# --- HÀM TÍNH NGẮT DÒNG THEO PIXEL THỰC TẾ ---
    def wrap_text_by_pixels(self, text, font, max_w):
        """Chia dòng chính xác dựa trên chiều rộng pixel thực tế của từng từ"""
        lines = []
        for paragraph in text.split("\n"):
            words = paragraph.split(" ")
            if not words or words == [""]:
                lines.append("")
                continue

            current_line = []
            for word in words:
                test_line = (
                    " ".join(current_line + [word]) if current_line else word
                )
                bbox = font.getbbox(test_line)
                line_w = bbox[2] - bbox[0]

                if line_w <= max_w:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(" ".join(current_line))
                        current_line = [word]
                    else:
                        lines.append(word)
            if current_line:
                lines.append(" ".join(current_line))
        return lines

    # --- POPUP BIÊN TẬP KÈM KHUNG XEM TRƯỚC (PREVIEW) ---
    def open_custom_editor(self, initial_text, points, x1, y1, x2, y2):
        top = tk.Toplevel(self.root)
        top.title("Biên tập & Xem trước thoại")

        window_width = 880
        window_height = 520
        self.root.update_idletasks()
        rx, ry = self.root.winfo_x(), self.root.winfo_y()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        cx = rx + max(0, (rw - window_width) // 2)
        cy = ry + max(0, (rh - window_height) // 2)
        top.geometry(f"{window_width}x{window_height}+{cx}+{cy}")
        top.transient(self.root)
        top.grab_set()

        left_frame = tk.Frame(top, width=400)
        left_frame.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10
        )

        right_frame = tk.LabelFrame(
            top, text="🔍 Xem trước thực tế", font=("Arial", 10, "bold")
        )
        right_frame.pack(
            side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=10, pady=10
        )

        tk.Label(
            left_frame, text="Nội dung thoại:", font=("Arial", 10, "bold")
        ).pack(anchor="w")

        txt_box = tk.Text(left_frame, wrap=tk.WORD, font=("Arial", 11), height=6)
        txt_box.pack(fill=tk.BOTH, expand=True, pady=(2, 5))
        txt_box.insert("1.0", initial_text)

        # ---------------------------------------------------------
        # KHU VỰC ĐỊNH DẠNG FONT (SIZE, BOLD, ITALIC)
        # ---------------------------------------------------------
        style_frame = tk.LabelFrame(
            left_frame, text=" Định dạng Font", font=("Arial", 9, "bold")
        )
        style_frame.pack(fill=tk.X, pady=2, ipadx=5, ipady=2)

        self.var_bold = tk.BooleanVar(value=False)
        self.var_italic = tk.BooleanVar(value=False)

        chk_bold = tk.Checkbutton(
            style_frame,
            text="B (In đậm)",
            variable=self.var_bold,
            font=("Arial", 9, "bold"),
        )
        chk_bold.pack(side=tk.LEFT, padx=2)

        chk_italic = tk.Checkbutton(
            style_frame,
            text="I (In nghiêng)",
            variable=self.var_italic,
            font=("Arial", 9, "italic"),
        )
        chk_italic.pack(side=tk.LEFT, padx=2)

        font_scale = tk.Scale(
            style_frame,
            from_=8,
            to=40,
            orient=tk.HORIZONTAL,
            label="Cỡ chữ:",
        )
        font_scale.set(16)
        font_scale.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)

        # ---------------------------------------------------------
        # KHU VỰC CĂN CHỈNH VỊ TRÍ CHỮ DỌC (Y-OFFSET)
        # ---------------------------------------------------------
        pos_frame = tk.LabelFrame(
            left_frame,
            text=" 🎯 Vị trí & Dịch chuyển dọc",
            font=("Arial", 9, "bold"),
        )
        pos_frame.pack(fill=tk.X, pady=5, ipadx=5, ipady=2)

        # Slider tinh chỉnh nhích lên / nhích xuống (-30px đến +30px)
        y_offset_scale = tk.Scale(
            pos_frame,
            from_=-50,
            to=50,
            orient=tk.HORIZONTAL,
            label="Nhích chữ (Âm: Lên ⬆️ | Dương: Xuống ⬇️):",
        )
        y_offset_scale.set(0)  # Mặc định ở giữa
        y_offset_scale.pack(fill=tk.X, expand=True, padx=5)
        # Slider tinh chỉnh nhích trái / nhích phải (-30px đến +30px)
        x_offset_scale = tk.Scale(
            pos_frame,
            from_=-50,
            to=50,
            orient=tk.HORIZONTAL,
            label="Nhích chữ (Âm: Trái ⬅️ | Dương: Phải ➡ ):",
        )
        x_offset_scale.set(0)  # Mặc định ở giữa
        x_offset_scale.pack(fill=tk.X, expand=True, padx=5)

        # --- PREVIEW CANVAS ---
        # Cắt ảnh rộng ra 20% xung quanh chỉ để xem trước dễ hơn
        crop_w, crop_h = (x2 - x1), (y2 - y1)  #
        pad_x = int(crop_w * 0.2)  # Mở rộng 20% chiều ngang
        pad_y = int(crop_h * 0.2)  # Mở rộng 20% chiều dọc

        # Cắt vùng xem trước mở rộng (Preview Crop)
        preview_crop = self.pil_image.crop(
            (x1 - pad_x, y1 - pad_y, x2 + pad_x, y2 + pad_y)
        )  #
        preview_w, preview_h = preview_crop.size

        preview_canvas = tk.Canvas(
            right_frame,
            width=preview_w,
            height=preview_h,
            bg="gray",
            highlightthickness=1,
            highlightbackground="#ccc",
        )  ##[cite: 1]
        preview_canvas.pack(padx=10, pady=10)  ##[cite: 1]

        self.preview_tk_img = None
        # 1. Thêm Slider tinh chỉnh độ mờ viền vào pos_frame
        blur_offset_scale = tk.Scale(
            pos_frame,
            from_=0,
            to=20,
            orient=tk.HORIZONTAL,
            label="Độ mờ viền xóa (Feather / Blur):",
        )
        blur_offset_scale.set(3)  # Mặc định 6px mờ rìa tự nhiên
        blur_offset_scale.pack(fill=tk.X, expand=True, padx=5)

        def update_preview(*args):
            text = txt_box.get("1.0", tk.END).strip()#[cite: 1]
            current_size = font_scale.get()#[cite: 1]
            is_b = self.var_bold.get()#[cite: 1]
            is_i = self.var_italic.get()#[cite: 1]
            y_shift = y_offset_scale.get()#[cite: 1]
            x_shift = x_offset_scale.get()#[cite: 1]
            blur_radius = blur_offset_scale.get()  # Lấy giá trị blur

            img_copy = preview_crop.copy()#[cite: 1]

            # 2. XỬ LÝ XÓA NỀN MỜ VIỀN TRÊN PREVIEW (FEATHER EDGE)
            rel_points = [
                (px - x1 + pad_x, py - y1 + pad_y) for px, py in points
            ]#[cite: 1]

            # Tạo Mask xám cùng kích thước với preview_crop
            mask = Image.new("L", (preview_w, preview_h), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.polygon(rel_points, fill=255)

            # Làm mờ viền Mask nếu blur_radius > 0
            if blur_radius > 0:
                mask = mask.filter(
                    ImageFilter.GaussianBlur(radius=blur_radius)
                )

            # Phủ lớp màu trắng đè lên preview_crop thông qua Mask mờ viền
            white_bg = Image.new("RGB", (preview_w, preview_h), (255, 255, 255))
            img_copy = Image.composite(white_bg, img_copy, mask)

            # 3. VẼ CHỮ LÊN TRÊN (Tọa độ không đổi)
            draw = ImageDraw.Draw(img_copy)#[cite: 1]
            font = get_styled_font(
                font_size=current_size, is_bold=is_b, is_italic=is_i
            )#[cite: 1]
            box_w, box_h = crop_w - 8, crop_h - 8##[cite: 1]

            if box_w > 0 and box_h > 0 and text:
                lines = self.wrap_text_by_pixels(
                    text, font, box_w
                )#[cite: 1]
                line_height = font.getbbox("A")[3] + 2#[cite: 1]
                total_h = len(lines) * line_height#[cite: 1]

                base_start_y = pad_y + 4 + max(0, (box_h - total_h) // 2)##[cite: 1]
                start_y = base_start_y + y_shift#[cite: 1]

                cur_y = start_y#[cite: 1]
                for line in lines:
                    bbox = font.getbbox(line)#[cite: 1]
                    line_w = bbox[2] - bbox[0]#[cite: 1]

                    start_x = (
                        pad_x + 4 + max(0, (box_w - line_w) // 2) + x_shift
                    )#[cite: 1]

                    draw.text((start_x, cur_y), line, fill="black", font=font)##[cite: 1]
                    cur_y += line_height#[cite: 1]

            self.preview_tk_img = ImageTk.PhotoImage(img_copy)##[cite: 1]
            preview_canvas.config(width=preview_w, height=preview_h)##[cite: 1]
            preview_canvas.create_image(
                0, 0, anchor=tk.NW, image=self.preview_tk_img
            )#[cite: 1]

        # Đăng ký sự kiện thay đổi cho Slider Blur
        blur_offset_scale.config(command=update_preview)

        # 4. TRUYỀN GIÁ TRỊ BLUR VÀO HÀM LƯU LẠI
        def save_and_close():
            user_text = txt_box.get("1.0", tk.END).strip()#[cite: 1]
            chosen_size = font_scale.get()#[cite: 1]
            is_b = self.var_bold.get()#[cite: 1]
            is_i = self.var_italic.get()#[cite: 1]
            y_shift = y_offset_scale.get()#[cite: 1]
            x_shift = x_offset_scale.get()#[cite: 1]
            blur_radius = blur_offset_scale.get()

            top.destroy()
            if user_text:
                self.draw_mask_and_text_custom(
                    user_text,
                    chosen_size,
                    is_b,
                    is_i,
                    y_shift,
                    x_shift,
                    blur_radius,  # Thêm tham số blur_radius
                    points,
                    x1,
                    y1,
                    x2,
                    y2,
                )
            else:
                self.show_image()#[cite: 1]

        # Lắng nghe các sự kiện thay đổi
        txt_box.bind("<KeyRelease>", update_preview)
        font_scale.config(command=update_preview)
        chk_bold.config(command=update_preview)
        chk_italic.config(command=update_preview)
        y_offset_scale.config(command=update_preview)  # Lắng nghe Slider nhích chữ
        x_offset_scale.config(command=update_preview)
        blur_offset_scale.config(command=update_preview)
        update_preview()

        # Nút bấm Lưu / Hủy
        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        tk.Button(
            btn_frame,
            text="✅ Hoàn tất & Chèn",
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            command=save_and_close,
        ).pack(side=tk.RIGHT, padx=5)
        tk.Button(
            btn_frame,
            text="❌ Hủy",
            command=lambda: (top.destroy(), self.show_image()),
        ).pack(side=tk.RIGHT)

    # ---------------------------------------------------------
    # HÀM VẼ CHỮ LÊN ẢNH GỐC CÓ TÍNH VỊ TRÍ DỊCH CHUYỂN
    # ---------------------------------------------------------
    def draw_mask_and_text_custom(
        self,
        text,
        font_size,
        is_bold,
        is_italic,
        y_shift,
        x_shift,
        blur_radius,  # Sắp xếp blur_radius trước points
        points,
        x1,
        y1,
        x2,
        y2,
    ):
        current_filepath = self.image_files[self.current_index]  #[cite: 1]

        # 1. Tự động sao lưu ảnh...
        folder_dir, filename = os.path.split(current_filepath)  #[cite: 1]
        backup_dir = os.path.join(folder_dir, "_backups")  #[cite: 1]
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)  #[cite: 1]
        backup_filepath = os.path.join(backup_dir, filename)  #[cite: 1]
        if not os.path.exists(backup_filepath):
            shutil.copy2(current_filepath, backup_filepath)  #[cite: 1]

        # 2. XÓA NỀN BẰNG MASK MỜ RÌA
        w, h = self.pil_image.size

        mask = Image.new("L", (w, h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.polygon(points, fill=255)

        if blur_radius > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        white_overlay = Image.new("RGB", (w, h), (255, 255, 255))
        self.pil_image = Image.composite(white_overlay, self.pil_image, mask)

        # 3. CHÈN CHỮ TIẾNG VIỆT
        draw = ImageDraw.Draw(self.pil_image)  #[cite: 1]
        box_w = x2 - x1 - 8  #[cite: 1]
        box_h = y2 - y1 - 8  #[cite: 1]

        if box_w > 0 and box_h > 0:
            font = get_styled_font(
                font_size=font_size, is_bold=is_bold, is_italic=is_italic
            )  #[cite: 1]
            lines = self.wrap_text_by_pixels(text, font, box_w)  #[cite: 1]
            line_height = font.getbbox("A")[3] + 2  #[cite: 1]
            total_text_h = len(lines) * line_height  #[cite: 1]

            base_start_y = y1 + 4 + max(0, (box_h - total_text_h) // 2)  #[cite: 1]
            start_y = base_start_y + y_shift  #[cite: 1]

            current_y = start_y  #[cite: 1]
            for line in lines:
                bbox = font.getbbox(line)  #[cite: 1]
                line_w = bbox[2] - bbox[0]  #[cite: 1]

                start_x = (
                    x1 + 4 + max(0, (box_w - line_w) // 2) + x_shift
                )  #[cite: 1]

                draw.text((start_x, current_y), line, fill="black", font=font)  #[cite: 1]
                current_y += line_height  #[cite: 1]

        # 4. LƯU VÀ CẬP NHẬT GIAO DIỆN
        ext = os.path.splitext(current_filepath)[1].lower()  #[cite: 1]
        if ext in [".jpg", ".jpeg"]:
            self.pil_image.save(current_filepath, quality=100, subsampling=0)  #[cite: 1]
        else:
            self.pil_image.save(current_filepath)  #[cite: 1]

        self.show_image()  #[cite: 1]
        self.lbl_info.config(
            text="✅ Đã xóa mờ viền & chèn chữ thành công!"
        )

    
    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_image()

    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.show_image()


if __name__ == "__main__":
    root = tk.Tk()
    app = MangaTranslatorApp(root)
    root.mainloop()
