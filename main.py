import os
import json
import re
import socket
from urllib import request
from sys import prefix
from dotenv import load_dotenv
import threading
import subprocess
import platform
import uuid

from dotenv.main import logger
from logging_site import RealtimeLogger
import time

import psutil

def is_public_ip(ip):
    """Kiểm tra xem một IP có phải là IP Public (không thuộc dải Private) hay không"""
    try:
        # Tách các dải IP để kiểm tra
        parts = list(map(int, ip.split('.')))
        if len(parts) != 4:
            return False
        
        # Các dải IP Private chuẩn RFC 1918 và Loopback
        if parts[0] == 10: return False  # 10.0.0.0/8
        if parts[0] == 172 and (16 <= parts[1] <= 31): return False  # 172.16.0.0/12
        if parts[0] == 192 and parts[1] == 168: return False  # 192.168.0.0/16
        if parts[0] == 127: return False  # Loopback 127.0.0.1
        if parts[0] == 169 and parts[1] == 254: return False  # Link-local (APIPA)
        
        return True
    except Exception:
        return False

def get_network_ips():
    """Quét tất cả các card mạng để tìm IP Private và IP Public thực tế"""
    private_ip = "127.0.0.1"
    public_ips = []
    
    try:
        # Lấy danh sách tất cả các card mạng và địa chỉ đi kèm
        interfaces = psutil.net_if_addrs()
        for interface_name, addresses in interfaces.items():
            for addr in addresses:
                # Chỉ lấy IPv4 (AF_INET)
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    if ip == "127.0.0.1":
                        continue
                        
                    if is_public_ip(ip):
                        if ip not in public_ips:
                            public_ips.append(ip)
                    else:
                        # Ưu tiên lấy IP Private từ kết nối đang active (hoặc lấy cái đầu tiên tìm thấy)
                        if private_ip == "127.0.0.1":
                            private_ip = ip
                            
        # Cách backup để lấy IP Private chính xác đang kết nối internet (nếu psutil bị sót)
        if private_ip == "127.0.0.1":
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            private_ip = s.getsockname()[0]
            s.close()
            
    except Exception:
        pass
        
    # Trả về IP Private và IP Public đầu tiên tìm thấy trên card mạng (nếu có)
    return private_ip, (public_ips[0] if public_ips else None)

def main():
    # =========================================
    # CONFIG SERVER FRP (Thay đổi thông tin ở đây)
    # =========================================

    # XRAY CONFIG
    def init_env_file():
        env_path = ".env"
        # Các giá trị mặc định
        default_configs = {
            "PORT": "8888",
            "XRAY_UUID": str(uuid.uuid4()),
            "DEST_SNI": "m.tiktok.com",
            "PRIVATE_KEY": "sD7SQLbL_Ka6U2Fyu2tMxWAfz5ZFn093LF0ihwl9n24",
            "PUBLIC_KEY": "3u34YvqYDL3DtKfCPWPH9HjEYjnWv1xitfGErFRhDR8",
            "SHORT_ID": "6baad05fed",
            "FRP_SERVER_ADDR": "frp.freefrp.net",
            "FRP_SERVER_PORT": "7000",
            "FRP_TOKEN": "freefrp.net",
            "REMOTE_PORT": "12345",
            "PRIVATE_IP_PORT": "0",
            "PUBLIC_IP_PORT": "0"
        }

        if not os.path.exists(env_path):
            print("[*] File .env không tồn tại. Đang tạo file với cấu hình mặc định...")
            with open(env_path, "w", encoding="utf-8") as f:
                for key, value in default_configs.items():
                    f.write(f"{key}={value}\n")
            print("[+] Đã tạo file .env thành công.")
        else:
            print("[*] Đã tìm thấy file .env.")

    # 1. Khởi tạo file .env nếu chưa có
    init_env_file()

    # 2. Load các biến vào môi trường
    load_dotenv()

    def int_or_zero(value):
        try:
            return int(value)
        except ValueError:
            return 0

    # 3. Đọc biến từ môi trường (ưu tiên biến hệ thống/GitHub Secrets, sau đó mới đến .env)
    PORT = int(os.getenv("PORT", 8888))
    UUID = os.getenv("XRAY_UUID", str(uuid.uuid4()))
    DEST_SNI = os.getenv("DEST_SNI", "m.tiktok.com")
    PRIVATE_KEY = os.getenv("PRIVATE_KEY", "sD7SQLbL_Ka6U2Fyu2tMxWAfz5ZFn093LF0ihwl9n24")
    PUBLIC_KEY = os.getenv("PUBLIC_KEY", "3u34YvqYDL3DtKfCPWPH9HjEYjnWv1xitfGErFRhDR8")
    SHORT_ID = os.getenv("SHORT_ID", "6baad05fed")
    FRP_SERVER_ADDR = os.getenv("FRP_SERVER_ADDR", "frp.freefrp.net")
    FRP_SERVER_PORT = int(os.getenv("FRP_SERVER_PORT", 7000))
    FRP_TOKEN = os.getenv("FRP_TOKEN", "freefrp.net")
    REMOTE_PORT = int(os.getenv("REMOTE_PORT", 12345))
    PRIVATE_IP_PORT = int_or_zero(os.getenv("PRIVATE_IP_PORT", 0)) # Để test trong mạng nội bộ
    PUBLIC_IP_PORT = int_or_zero(os.getenv("PUBLIC_IP_PORT", 0)) # Nếu bạn có IP công khai (thông qua VPS hoặc đã mở port trên modem)

    XRAY_BIN = "./xray.exe" if platform.system().lower() == "windows" else "./xray"
    FRPC_BIN = "./frpc.exe" if platform.system().lower() == "windows" else "./frpc"
    CLF_BIN = "./cloudflared.exe" if platform.system().lower() == "windows" else "./cloudflared"

    # =========================================
    # TẠO FILE CẤU HÌNH
    # =========================================


    private_ip, public_ip = get_network_ips()

    def write_configs():
        # 1. Cấu hình Xray (VLESS Reality)
        xray_config = {
            "log": {"loglevel": "error"},
            "inbounds": [],
            "outbounds": [{"protocol": "freedom", "settings": {"domainStrategy": "UseIP"}}]
        }
        def add_inbound(ip, port):
            xray_config["inbounds"].append({
                "port": port,
                "protocol": "vless",
                "settings": {
                    "clients": [{"id": UUID}],
                    "decryption": "none",
                    "fallbacks": []
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "serverNames": [DEST_SNI],
                        "privateKey": PRIVATE_KEY,
                        "publicKey": PUBLIC_KEY,
                        "shortId": SHORT_ID
                    }
                }
            })
        add_inbound("127.0.0.1", PORT)
        if PRIVATE_IP_PORT: add_inbound(private_ip, PRIVATE_IP_PORT)
        if PUBLIC_IP_PORT: add_inbound(public_ip, PUBLIC_IP_PORT)
        with open("config.json", "w") as f: json.dump(xray_config, f, indent=2)

        # 2. Cấu hình Frp (frpc.toml)
        frp_toml = f"""
serverAddr = "{FRP_SERVER_ADDR}"
serverPort = {FRP_SERVER_PORT}
auth.token = "{FRP_TOKEN}"

[[proxies]]
name = "vless-reality-{UUID[:6]}"
type = "tcp"
localIP = "127.0.0.1"
localPort = {PORT}
remotePort = {REMOTE_PORT}
"""
        with open("frpc.toml", "w") as f: f.write(frp_toml)

    # =========================================
    # CHẠY DỊCH VỤ (Cập nhật để hiện Log)
    # =========================================
    def log_reader(pipe, prefix):
        """Hàm đọc log từ pipe và in ra màn hình"""
        try:
            with pipe:
                for line in iter(pipe.readline, ''):
                    print(f"[{prefix}] {line.strip()}")
        except Exception:
            pass

    def start_services():
        write_configs()
        
        # Khởi chạy Xray
        print(f"[*] Khởi chạy XRAY tại 127.0.0.1:{PORT}")
        xp = subprocess.Popen(
            [XRAY_BIN, "run", "-c", "config.json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Khởi chạy Frp
        print(f"[*] Khởi chạy FRP tại {FRP_SERVER_ADDR}:{REMOTE_PORT}")
        fp = subprocess.Popen(
            [FRPC_BIN, "-c", "frpc.toml"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # Chạy các luồng đọc log song song
        logger = RealtimeLogger(port=9999, password=PRIVATE_KEY if PRIVATE_KEY else None)
        logger_url = logger.start()
        print(f"[*] Logger Web UI đang chạy tại: {logger_url}")
        clp = subprocess.Popen(
            [CLF_BIN, "tunnel", "--url", logger_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        def log_push(pipe, prefix):
            try:
                with pipe:
                    ansi_escape = re.compile(r'\x1b\[[0-9;]*[mK]')
                    for line in iter(pipe.readline, ''):
                        clean_line = ansi_escape.sub('', line)
                        logger.push_log(clean_line.strip(), prefix)
            except Exception as e:
                print(f"Error in log_push for {prefix}: {e}")
                
        threading.Thread(target=log_push, args=(xp.stdout, "XRAY"), daemon=True).start()
        threading.Thread(target=log_push, args=(fp.stdout, "FRP"), daemon=True).start()
        threading.Thread(target=log_reader, args=(clp.stdout, "CLOUDFLARED"), daemon=True).start()

        return xp, fp, clp

    # =========================================
    # LẤY THÔNG TIN IP VÀ PHÁT SINH URI KẾT NỐI
    # =========================================
    
    # Tạo các chuỗi cấu hình URI mẫu dựa trên các IP
    base_query = f"?security=reality&sni={DEST_SNI}&fp=chrome&pbk={PUBLIC_KEY}&sid={SHORT_ID}&type=tcp&flow=xtls-rprx-vision#FRP_Reality"
    
    frp_uri = f"vless://{UUID}@{FRP_SERVER_ADDR}:{REMOTE_PORT}{base_query}"
    private_uri = f"vless://{UUID}@{private_ip}:{PRIVATE_IP_PORT}{base_query}"
    public_uri = f"vless://{UUID}@{public_ip}:{PUBLIC_IP_PORT}{base_query}" if public_ip else "Không lấy được IP Public (Hoặc không có)"

    print("\n" + "="*70)
    print(" DANH SÁCH ĐƯỜNG DẪN KẾT NỐI (VLESS URI)")
    print("="*70)
    print(f"[+] Qua Server FRP (Public): \n    {frp_uri}\n")
    if PRIVATE_IP_PORT:
        print(f"[+] Qua IP Private (Mạng nội bộ) [Port {PRIVATE_IP_PORT}]: \n    {private_uri}\n")
    if public_ip and PUBLIC_IP_PORT:
        print(f"[+] Qua IP Public trực tiếp [Port {PUBLIC_IP_PORT}]: \n    {public_uri}\n")
    print("="*70 + "\n")

    # Lưu tất cả link vào file cấu hình cũ
    with open("frp_info.config", "w", encoding='utf-8') as f:
        f.write(frp_uri)
        f.write("\n")
        f.write(private_uri)
        f.write("\n")
        f.write(public_uri)

    xp, fp, clp = start_services()

    try:
        # Giữ script chạy để xem log
        fp.wait()
    except KeyboardInterrupt:
        print("\n[*] Đang dừng dịch vụ...")
        xp.terminate()
        fp.terminate()
        clp.terminate()

if __name__ == "__main__":
    main()