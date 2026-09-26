import os
import re
import json
import base64
from io import BytesIO
from PIL import Image
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse

PORT = 8081
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POLAROID_DIR = os.path.join(BASE_DIR, 'polaroid')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')
DATA_FILE = os.path.join(BASE_DIR, 'memories.json')
INDEX_FILE = os.path.join(BASE_DIR, 'index.html')

os.makedirs(IMAGES_DIR, exist_ok=True)

def get_polaroid_images():
    valid_exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
    if not os.path.exists(POLAROID_DIR):
        return []
    files = [f for f in os.listdir(POLAROID_DIR) if f.lower().endswith(valid_exts) and not f.startswith('.')]
    files.sort()
    return files

def load_memories():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_memories(memories):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)

def update_index_html(memories):
    if not os.path.exists(INDEX_FILE):
        return False, "Không tìm thấy file index.html"
    
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Tạo HTML cho timeline items
    stickers = ['🌸', '🎀', '🧸', '🎈', '🍓', '✨', '💖', '☕', '🐾', '🧁', '💫', '🍧']
    dots = ['🌷', '💖', '✈️', '🎂', '🧸', '🍧', '🌙', '🧣', '😸', '💍', '🌸', '✨']
    
    items_html = []
    # Sắp xếp theo ngày tháng thời gian
    items = list(memories.values())
    from datetime import datetime

    def parse_date(item):
        d_str = item.get('date', '').strip()
        if 'first date' in item.get('title', '').lower() and '2026' in d_str:
            return datetime(2023, 5, 26)
        try:
            parts = [int(p) for p in d_str.split('/')]
            if len(parts) == 3:
                return datetime(parts[2], parts[1], parts[0])
        except Exception:
            pass
        return datetime(2099, 1, 1)

    sorted_items = sorted(items, key=parse_date)
    
    for idx, item in enumerate(sorted_items):
        item_num = idx + 1
        sticker = stickers[(item_num - 1) % len(stickers)]
        dot = dots[(item_num - 1) % len(dots)]
        
        date_str = item.get('date', '').strip()
        title_str = item.get('title', '').strip()
        note_str = item.get('note', '').strip()
        img_name = item.get('cropped_image', '')
        
        # Nhận diện tỉ lệ ảnh 1:1 hay 4:3
        ratio_class = 'ratio-4x3'
        img_path = os.path.join(IMAGES_DIR, img_name)
        if os.path.exists(img_path):
            try:
                im = Image.open(img_path)
                w, h = im.size
                if abs(w / h - 1.0) < 0.12:
                    ratio_class = 'ratio-1x1'
            except Exception:
                pass

        # Tiêu đề hiển thị
        header_display = f"✨ {title_str}"
        if date_str:
            header_display += f' • <span style="font-weight:400;font-size:0.85rem;color:var(--text-soft)">{date_str}</span>'
            
        entry_block = f'''            <!-- ENTRY {item_num} ({ratio_class.upper()}) -->
            <div class="timeline-item">
                <div class="timeline-dot">{dot}</div>
                <div class="polaroid-card {ratio_class}">
                    <div class="washi-tape"></div>
                    <div class="timeline-photo">
                        <!-- THAY ẢNH {item_num} -->
                        <img src="images/{img_name}" alt="{title_str}">
                    </div>
                    <div class="timeline-date">{header_display}</div>
                    <p class="timeline-caption">{note_str}</p>
                    <div class="card-sticker">{sticker}</div>
                </div>
            </div>'''
        items_html.append(entry_block)

    timeline_replacement = "\n\n" + "\n\n".join(items_html) + "\n\n        "

    # Thay thế phần bên trong <div class="timeline-container"> ... </div>
    pattern = r'(<div class="timeline-container">)(.*?)(</div>\s*</section>)'
    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(
            pattern,
            rf'\g<1>{timeline_replacement}\g<3>',
            content,
            flags=re.DOTALL
        )
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True, "Cập nhật index.html thành công!"
    else:
        return False, "Không tìm thấy timeline-container trong index.html"

HTML_PAGE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌸 Trình Cắt Ảnh & Biên Tập Kỷ Niệm Polaroid ✨</title>
    <!-- Cropper.js CDN -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&family=Quicksand:wght@500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --pink-main: #ff6584;
            --pink-deep: #ff477e;
            --pink-light: #ffe5ec;
            --pink-pastel: #fff0f5;
            --text-dark: #4a2835;
            --bg-card: #ffffff;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Quicksand', sans-serif;
            background: linear-gradient(135deg, #fff2f6 0%, #ffeaf1 100%);
            color: var(--text-dark);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* Header */
        header {
            background: #ffffff;
            padding: 1rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 15px rgba(255, 101, 132, 0.1);
            border-bottom: 2px solid var(--pink-light);
        }

        .logo {
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--pink-deep);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .header-actions {
            display: flex;
            gap: 12px;
            align-items: center;
        }

        .btn-view-web {
            background: linear-gradient(135deg, #ff6584, #ff477e);
            color: white;
            text-decoration: none;
            padding: 9px 18px;
            border-radius: 30px;
            font-weight: 700;
            font-size: 0.95rem;
            box-shadow: 0 4px 12px rgba(255, 71, 126, 0.3);
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .btn-view-web:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 18px rgba(255, 71, 126, 0.4);
        }

        /* Main Workspace */
        .container {
            display: flex;
            flex: 1;
            padding: 1.5rem;
            gap: 1.5rem;
            max-width: 1400px;
            margin: 0 auto;
            width: 100%;
        }

        /* Cột bên trái: Danh sách thumbnails */
        .sidebar {
            width: 260px;
            background: #ffffff;
            border-radius: 16px;
            padding: 1.2rem;
            box-shadow: 0 8px 25px rgba(255, 101, 132, 0.08);
            border: 1px solid #ffd0de;
            display: flex;
            flex-direction: column;
            max-height: calc(100vh - 120px);
        }

        .sidebar-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--pink-deep);
            margin-bottom: 0.8rem;
            padding-bottom: 0.5rem;
            border-bottom: 1.5px dashed var(--pink-light);
            display: flex;
            justify-content: space-between;
        }

        .img-list {
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding-right: 4px;
        }

        .img-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 10px;
            border-radius: 12px;
            cursor: pointer;
            border: 2px solid transparent;
            background: #fff8fa;
            transition: all 0.2s;
        }

        .img-item:hover {
            background: #ffeef3;
        }

        .img-item.active {
            border-color: var(--pink-main);
            background: #ffeaf1;
            box-shadow: 0 4px 10px rgba(255, 101, 132, 0.15);
        }

        .img-item.saved {
            border-left: 4px solid #2ecc71;
        }

        .img-thumb {
            width: 48px;
            height: 48px;
            border-radius: 8px;
            object-fit: cover;
            border: 1px solid #ffd5e2;
        }

        .img-info {
            flex: 1;
            overflow: hidden;
        }

        .img-name {
            font-size: 0.85rem;
            font-weight: 600;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .img-status {
            font-size: 0.75rem;
            color: #888;
        }

        .img-status.done {
            color: #27ae60;
            font-weight: 700;
        }

        /* Cột giữa & phải: Workspace */
        .workspace {
            flex: 1;
            display: flex;
            gap: 1.5rem;
        }

        /* Vùng cắt ảnh Cropper */
        .crop-area {
            flex: 1.2;
            background: #ffffff;
            border-radius: 16px;
            padding: 1.2rem;
            box-shadow: 0 8px 25px rgba(255, 101, 132, 0.08);
            border: 1px solid #ffd0de;
            display: flex;
            flex-direction: column;
        }

        .crop-toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            flex-wrap: wrap;
            gap: 8px;
        }

        .toolbar-group {
            display: flex;
            gap: 6px;
        }

        .tool-btn {
            background: #fff0f5;
            border: 1.5px solid #ffccd5;
            color: var(--text-dark);
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .tool-btn:hover, .tool-btn.active {
            background: var(--pink-main);
            color: white;
            border-color: var(--pink-main);
        }

        .img-container {
            flex: 1;
            min-height: 420px;
            max-height: 520px;
            background: #2a2a2a;
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .img-container img {
            max-width: 100%;
            max-height: 100%;
            display: block;
        }

        /* Cột nhập thông tin */
        .form-area {
            width: 380px;
            background: #ffffff;
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 8px 25px rgba(255, 101, 132, 0.08);
            border: 1px solid #ffd0de;
            display: flex;
            flex-direction: column;
        }

        .form-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--pink-deep);
            margin-bottom: 1.2rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .form-group {
            margin-bottom: 1.2rem;
        }

        label {
            display: block;
            font-weight: 700;
            font-size: 0.9rem;
            margin-bottom: 0.4rem;
            color: var(--text-dark);
        }

        input[type="text"], textarea {
            width: 100%;
            padding: 10px 14px;
            border-radius: 10px;
            border: 1.5px solid #ffccd5;
            background: #fffbfc;
            font-family: inherit;
            font-size: 0.95rem;
            color: var(--text-dark);
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        input[type="text"]:focus, textarea:focus {
            border-color: var(--pink-main);
            box-shadow: 0 0 0 3px rgba(255, 101, 132, 0.15);
            background: #ffffff;
        }

        textarea {
            resize: vertical;
            min-height: 100px;
            line-height: 1.5;
        }

        .form-actions {
            margin-top: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .btn-save {
            background: linear-gradient(135deg, #ff6584, #ff477e);
            color: white;
            border: none;
            padding: 13px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 1.05rem;
            cursor: pointer;
            box-shadow: 0 6px 18px rgba(255, 71, 126, 0.3);
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn-save:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 22px rgba(255, 71, 126, 0.4);
        }

        .nav-buttons {
            display: flex;
            gap: 10px;
        }

        .btn-nav {
            flex: 1;
            background: #fff0f5;
            border: 1px solid #ffccd5;
            padding: 9px;
            border-radius: 10px;
            font-weight: 600;
            color: var(--text-dark);
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-nav:hover {
            background: #ffe3ec;
        }

        /* Toast thông báo */
        .toast {
            position: fixed;
            bottom: 25px;
            right: 25px;
            background: #2ecc71;
            color: white;
            padding: 12px 24px;
            border-radius: 50px;
            font-weight: 700;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
            display: flex;
            align-items: center;
            gap: 8px;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s ease;
            z-index: 1000;
        }

        .toast.show {
            opacity: 1;
            transform: translateY(0);
        }

        @media (max-width: 1024px) {
            .container { flex-direction: column; }
            .sidebar { width: 100%; max-height: 180px; }
            .img-list { flex-direction: row; }
            .img-item { min-width: 160px; }
            .workspace { flex-direction: column; }
            .form-area { width: 100%; }
        }
    </style>
</head>
<body>

    <header>
        <div class="logo">
            <span>🌸</span>
            <span>Trình Cắt Ảnh & Soạn Kỷ Niệm Polaroid</span>
        </div>
        <div class="header-actions">
            <a href="http://localhost:8080" target="_blank" class="btn-view-web">
                <span>🎉 Xem Trang Web Sinh Nhật</span>
                <span>↗</span>
            </a>
        </div>
    </header>

    <div class="container">
        <!-- Sidebar danh sách ảnh -->
        <div class="sidebar">
            <div class="sidebar-title">
                <span>📁 Thư mục Polaroid</span>
                <span id="progress-text">0/0</span>
            </div>
            <div class="img-list" id="img-list">
                <!-- Danh sách thumbnails do JS render -->
            </div>
        </div>

        <!-- Workspace chính -->
        <div class="workspace">
            <!-- Vùng cắt ảnh Cropper -->
            <div class="crop-area">
                <div class="crop-toolbar">
                    <div class="toolbar-group">
                        <span style="font-weight:700;font-size:0.85rem;align-self:center;margin-right:4px;">Tỉ lệ cắt:</span>
                        <button class="tool-btn active" onclick="setAspectRatio(4/3, this)">📷 Chữ nhật (4:3)</button>
                        <button class="tool-btn" onclick="setAspectRatio(1, this)">⬜ Vuông (1:1)</button>
                        <button class="tool-btn" onclick="setAspectRatio(NaN, this)">🔲 Tự do</button>
                    </div>
                    <div class="toolbar-group">
                        <button class="tool-btn" onclick="rotateImage(90)">🔄 Xoay</button>
                        <button class="tool-btn" onclick="resetCrop()">↩️ Đặt lại</button>
                    </div>
                </div>

                <div class="img-container">
                    <img id="image-to-crop" src="" alt="Cắt ảnh">
                </div>
            </div>

            <!-- Form điền thông tin -->
            <div class="form-area">
                <div class="form-title">
                    <span>📝</span>
                    <span id="current-img-title">Thông tin kỷ niệm</span>
                </div>

                <div class="form-group">
                    <label for="input-date">🕒 1. Thời gian ảnh (Ngày / Năm)</label>
                    <input type="text" id="input-date" placeholder="Ví dụ: 15/01/2023 hoặc Mùa thu 2023...">
                </div>

                <div class="form-group">
                    <label for="input-title">🏷️ 2. Tiêu đề kỷ niệm (Title)</label>
                    <input type="text" id="input-title" placeholder="Ví dụ: Lần đầu gặp gỡ, Nắm tay đầu tiên...">
                </div>

                <div class="form-group">
                    <label for="input-note">💖 3. Lời nhắn / Ghi chú về ảnh</label>
                    <textarea id="input-note" placeholder="Viết vài dòng cảm xúc hoặc câu chuyện dễ thương về bức ảnh này..."></textarea>
                </div>

                <div class="form-actions">
                    <button class="btn-save" onclick="saveCurrentItem()">
                        <span>💾 Lưu & Cập Nhật Vào Web</span>
                    </button>
                    <div class="nav-buttons">
                        <button class="btn-nav" onclick="prevImage()">← Ảnh trước</button>
                        <button class="btn-nav" onclick="nextImage()">Ảnh tiếp theo →</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Toast -->
    <div class="toast" id="toast">
        <span>✅</span>
        <span id="toast-msg">Đã lưu và cập nhật web thành công!</span>
    </div>

    <!-- Cropper.js CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.js"></script>
    <script>
        let imageList = [];
        let memories = {};
        let currentIndex = 0;
        let cropper = null;

        const imgElement = document.getElementById('image-to-crop');
        const inputDate = document.getElementById('input-date');
        const inputTitle = document.getElementById('input-title');
        const inputNote = document.getElementById('input-note');
        const currentTitleDisplay = document.getElementById('current-img-title');
        const progressText = document.getElementById('progress-text');
        const toast = document.getElementById('toast');

        // Khởi tạo tải dữ liệu
        async function init() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                imageList = data.images;
                memories = data.memories;
                
                renderSidebar();
                if (imageList.length > 0) {
                    loadImage(0);
                }
            } catch (err) {
                console.error("Lỗi tải dữ liệu:", err);
            }
        }

        // Render danh sách ảnh ở Sidebar
        function renderSidebar() {
            const listEl = document.getElementById('img-list');
            listEl.innerHTML = '';
            
            let savedCount = 0;
            imageList.forEach((fname, idx) => {
                const isSaved = !!memories[fname];
                if (isSaved) savedCount++;

                const itemEl = document.createElement('div');
                itemEl.className = `img-item ${idx === currentIndex ? 'active' : ''} ${isSaved ? 'saved' : ''}`;
                itemEl.onclick = () => loadImage(idx);
                
                itemEl.innerHTML = `
                    <img class="img-thumb" src="/polaroid/${encodeURIComponent(fname)}" alt="${fname}">
                    <div class="img-info">
                        <div class="img-name">Ảnh ${idx + 1}: ${fname}</div>
                        <div class="img-status ${isSaved ? 'done' : ''}">${isSaved ? '✅ Đã lưu' : '⏳ Chưa soạn'}</div>
                    </div>
                `;
                listEl.appendChild(itemEl);
            });

            progressText.innerText = `${savedCount}/${imageList.length}`;
        }

        // Tải ảnh vào Cropper và load dữ liệu form
        function loadImage(index) {
            if (index < 0 || index >= imageList.length) return;
            currentIndex = index;
            const fname = imageList[currentIndex];

            // Cập nhật form
            currentTitleDisplay.innerText = `Ảnh ${currentIndex + 1}/${imageList.length}: ${fname}`;
            const itemData = memories[fname] || {};
            inputDate.value = itemData.date || '';
            inputTitle.value = itemData.title || `Kỷ niệm ${currentIndex + 1}`;
            inputNote.value = itemData.note || '';

            // Cập nhật Cropper
            if (cropper) {
                cropper.destroy();
                cropper = null;
            }

            imgElement.src = `/polaroid/${encodeURIComponent(fname)}`;
            imgElement.onload = () => {
                cropper = new Cropper(imgElement, {
                    aspectRatio: 4 / 3, // Mặc định 4:3 chữ nhật polaroid
                    viewMode: 1,
                    autoCropArea: 0.9,
                    responsive: true,
                });
            };

            renderSidebar();
        }

        // Đổi tỉ lệ cắt
        function setAspectRatio(ratio, btn) {
            if (!cropper) return;
            cropper.setAspectRatio(ratio);
            document.querySelectorAll('.toolbar-group .tool-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
        }

        function rotateImage(deg) {
            if (cropper) cropper.rotate(deg);
        }

        function resetCrop() {
            if (cropper) cropper.reset();
        }

        // Lưu ảnh đã cắt & thông tin
        async function saveCurrentItem() {
            if (!cropper) return;
            const fname = imageList[currentIndex];

            // Lấy canvas đã crop với chất lượng cao
            const canvas = cropper.getCroppedCanvas({
                maxWidth: 1200,
                maxHeight: 1200,
                imageSmoothingEnabled: true,
                imageSmoothingQuality: 'high'
            });

            const croppedBase64 = canvas.toDataURL('image/jpeg', 0.9);

            const payload = {
                original_filename: fname,
                index: currentIndex + 1,
                cropped_base64: croppedBase64,
                date: inputDate.value,
                title: inputTitle.value,
                note: inputNote.value
            };

            try {
                const res = await fetch('/api/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await res.json();
                
                if (result.success) {
                    showToast(`✅ Đã lưu Ảnh ${currentIndex + 1} và cập nhật vào web!`);
                    memories[fname] = result.item;
                    renderSidebar();
                    
                    // Tự động chuyển sang ảnh tiếp theo nếu còn
                    if (currentIndex < imageList.length - 1) {
                        setTimeout(() => loadImage(currentIndex + 1), 600);
                    }
                } else {
                    alert("Lỗi: " + result.message);
                }
            } catch (err) {
                alert("Lỗi khi lưu: " + err);
            }
        }

        function prevImage() {
            if (currentIndex > 0) loadImage(currentIndex - 1);
        }

        function nextImage() {
            if (currentIndex < imageList.length - 1) loadImage(currentIndex + 1);
        }

        function showToast(msg) {
            document.getElementById('toast-msg').innerText = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }

        init();
    </script>
</body>
</html>
"""

class CustomHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Override translate_path để trỏ đúng thư mục gốc BASE_DIR
        parsed = urllib.parse.urlparse(path)
        clean_path = parsed.path
        if clean_path.startswith('/polaroid/'):
            fname = clean_path[len('/polaroid/'):]
            return os.path.join(POLAROID_DIR, urllib.parse.unquote(fname))
        elif clean_path.startswith('/images/'):
            fname = clean_path[len('/images/'):]
            return os.path.join(IMAGES_DIR, urllib.parse.unquote(fname))
        return super().translate_path(path)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == '/' or parsed.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
            return

        elif parsed.path == '/api/data':
            images = get_polaroid_images()
            memories = load_memories()
            data = {
                'images': images,
                'memories': memories
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            return

        elif parsed.path.startswith('/polaroid/'):
            fname = urllib.parse.unquote(parsed.path[len('/polaroid/'):])
            fpath = os.path.join(POLAROID_DIR, fname)
            if os.path.exists(fpath):
                self.send_response(200)
                if fname.lower().endswith(('.jpg', '.jpeg')):
                    self.send_header('Content-Type', 'image/jpeg')
                elif fname.lower().endswith('.png'):
                    self.send_header('Content-Type', 'image/png')
                elif fname.lower().endswith('.webp'):
                    self.send_header('Content-Type', 'image/webp')
                self.end_headers()
                with open(fpath, 'rb') as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "File not found")
                return

        return super().do_GET()

    def do_POST(self):
        if self.path == '/api/save':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                fname = data.get('original_filename')
                idx = data.get('index', 1)
                b64_img = data.get('cropped_base64', '')
                date_val = data.get('date', '')
                title_val = data.get('title', '')
                note_val = data.get('note', '')

                # Giải mã base64 và lưu ảnh vào thư mục images/
                if ',' in b64_img:
                    b64_img = b64_img.split(',', 1)[1]
                img_bytes = base64.b64decode(b64_img)
                
                cropped_filename = f"memory_{idx}.jpg"
                cropped_path = os.path.join(IMAGES_DIR, cropped_filename)
                
                with open(cropped_path, 'wb') as f:
                    f.write(img_bytes)

                # Lưu vào memories.json
                memories = load_memories()
                item_data = {
                    'original_filename': fname,
                    'index': idx,
                    'cropped_image': cropped_filename,
                    'date': date_val,
                    'title': title_val,
                    'note': note_val
                }
                memories[fname] = item_data
                save_memories(memories)

                # Tự động cập nhật thẳng vào index.html
                ok, msg = update_index_html(memories)

                resp = {
                    'success': True,
                    'message': msg,
                    'item': item_data
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
                return

            except Exception as e:
                resp = {'success': False, 'message': str(e)}
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
                return

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, CustomHandler)
    print(f"🌸 Tool Cắt Ảnh & Soạn Kỷ Niệm đang chạy tại: http://localhost:{PORT}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
