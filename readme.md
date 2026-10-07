[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/P3A3285YNL)<br/>
## CÔNG CỤ CHUYỂN NGỮ CHO TRUYỆN TRANH<br/>
<br/>
## BƯỚC 1:<br/>
- Đăng ký và tạo 1 project bằng [Google AI Studio](https://aistudio.google.com/prompts/new_chat)
- Sau đó bạn vào thẻ API Keys ở bên trái, tìm đến project vừa tạo để lấy api key<br/>
- Bạn điền API KEY này thay cho chuỗi api trong file trans-mange.py<br/>
   API_KEY=os.getenv("GEMINI_API_KEY")<br/>
thành <br/>
   API_KEY="key api bạn copy được"<br/>
## BƯỚC 2:<br/>
- Cài đặt python cho máy<br/>
- Chạy file "cai-thu-vien.cmd" để cài thư viện cần thiết cho chương trình.<br/>
- Sau khi cài xong thư viện, bạn chạy file "trans-mange.py" để chạy chương trình.<br/>
## BƯỚC 3:<br/>
- Bạn chỉ cần chọn thư mục chứa tranh cần dịch,<br/>
- Chọn model gemini được liệt kê, ưu tiên chọn flash-lite cho tốc độ nhanh như gió.<br/>
- Sau đó khoanh vùng văn bản cần dịch<br/>
- Tiến hành dịch từng trang và bấm nút next ở trên cùng để chuyển trang tiếp theo.<br/>
