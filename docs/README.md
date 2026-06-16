# 🚀 Relay Bypass Server (VLESS Reality + FRP)

> Nhà mạng đã vá phương pháp SNI Spoof. Vui lòng kham khảo thêm [vincentng295/xray_vless_ws_server](https://github.com/vincentng295/xray_vless_ws_server) về cách tận dụng CDN Cloudflare để qua mặt bộ máy tính cước của nhà mạng!

Chào mừng bạn đến với **Relay Bypass Server**. Đây là một giải pháp mã nguồn mở giúp bạn xây dựng một server proxy cá nhân mạnh mẽ, hỗ trợ vượt qua các rào cản kiểm duyệt và tối ưu hóa tốc độ mạng thông qua cơ chế **SNI Bypass**.

Dự án này kết hợp sức mạnh của **Xray-core** (Giao thức VLESS Reality) và **FRP** (Fast Reverse Proxy) để tạo ra một đường truyền bảo mật, khó bị phát hiện bởi các hệ thống tường lửa.

---

## 🧠 Kiến thức: SNI Bypass là gì?

Để hiểu tại sao script này hoạt động, chúng ta cần nói về **SNI (Server Name Indication)**.

### 1. SNI là gì?

Khi bạn truy cập một trang web (ví dụ: `google.com`), trình duyệt sẽ gửi một yêu cầu kết nối. Trong gói tin chào hỏi đầu tiên (TLS Client Hello), tên miền `google.com` sẽ được ghi dưới dạng văn bản thuần túy (chưa mã hóa). Phần này gọi là **SNI**.

### 2. Nhà mạng làm gì với SNI?

Các nhà mạng (ISP) hoặc quản trị viên mạng thường dựa vào SNI để:

* **Chặn truy cập:** Nếu thấy SNI là trang web bị cấm, họ sẽ ngắt kết nối ngay lập tức.
* **Bóp băng thông:** Giới hạn tốc độ nếu SNI là các dịch vụ tốn dung lượng như YouTube/Netflix.
* **Ưu tiên (Zero-rating):** Miễn phí data nếu SNI thuộc danh sách các ứng dụng được khuyến mãi (ví dụ: gói TikTok, Youtube, hoặc các trang báo nội bộ).

### 3. Cơ chế Bypass của Project này

Project sử dụng giao thức **VLESS Reality**. Điểm đặc biệt của Reality là nó thực hiện việc **"mượn danh"** một trang web hợp lệ (như `m.tiktok.com`).

* Khi nhà mạng nhìn vào gói tin của bạn, họ chỉ thấy bạn đang kết nối tới trang web "hợp lệ" kia.
* Thực tế, dữ liệu của bạn đã được mã hóa và "ẩn nấp" bên trong, sau đó được server giải mã và chuyển tiếp tới đích thực sự bạn muốn đến.

---

## ✨ Tính năng nổi bật

* **VLESS Reality:** Giao thức proxy tiên tiến nhất hiện nay, không cần chứng chỉ SSL phức tạp mà vẫn đảm bảo tính bảo mật và ẩn danh cao.
* **Tích hợp FRP:** Cho phép bạn biến máy tính cá nhân hoặc các môi trường không có IP công khai (như GitHub Actions) thành một proxy server thông qua một server relay trung gian.
* **Tự động hóa:** Tự động tải Xray, FRP binaries và cấu hình môi trường chỉ với một lệnh chạy.
* **Hỗ trợ GitHub Actions:** Tích hợp sẵn workflow để chạy server "tạm thời" trên hạ tầng của GitHub.

---

## 🛠 Hướng dẫn cài đặt

### Cách 1: Chạy trực tiếp trên máy (Local)

1. **Cài đặt Python:** Yêu cầu Python 3.10 trở lên.
2. **Cài đặt thư viện:**
```bash
pip install -r requirements.txt

```


3. **Cấu hình:** Chỉnh sửa file `.env` (script sẽ tự tạo nếu chưa có) với các thông số sau:
* `DEST_SNI`: Tên miền muốn mượn danh (mặc định: `m.tiktok.com`).
* `REMOTE_PORT`: Cổng bạn sẽ dùng để kết nối từ xa.


4. **Chạy script:**
```bash
python main.py

```


Script sẽ tự động tải các file thực thi cần thiết và in ra một đường link **VLESS URI**. Bạn chỉ cần Copy link này dán vào các app như V2RayN, Shadowrocket hoặc Nekobox để sử dụng.

### Cách 2: Chạy qua GitHub Actions

1. Fork repository này.
2. Truy cập vào **Settings > Secrets and variables > Actions**.
3. Tạo một Secret mới tên là `ENV_CONFIG` và dán nội dung file `.env` của bạn vào đó.
4. Vào tab **Actions**, chọn workflow **VLESS Reality FRP** và nhấn **Run workflow**.
5. Xem log của workflow để lấy link VLESS URI.

---

## 📂 Cấu trúc dự án

* `main.py`: Script khởi tạo, quản lý cấu hình và chạy dịch vụ.
* `download-xray.py` & `download-service.py`: Tự động tải bản Xray và FRP phù hợp với hệ điều hành (Windows/Linux).
* `github-workflows.py`: Hỗ trợ nạp cấu hình từ GitHub Secrets và quản lý thời gian chạy trên workflow.
* `.env.example`: File mẫu chứa các biến môi trường quan trọng.

---

## ⚠️ Lưu ý quan trọng

* **Mục đích:** Project này được tạo ra vì mục đích nghiên cứu và học tập về giao thức mạng. Vui lòng không sử dụng vào các mục đích vi phạm pháp luật.
* **GitHub Actions:** Việc chạy proxy trên GitHub Actions có thể vi phạm điều khoản sử dụng của GitHub (ToS). Hãy cân nhắc kỹ trước khi sử dụng lâu dài trên tài khoản chính của bạn.

---

**Author:** vincentng295
*Chúc bạn có những trải nghiệm mạng internet tự do và an toàn!*
