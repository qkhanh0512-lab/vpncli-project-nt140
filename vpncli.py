#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".vpncli"
FILES_DIR = CONFIG_DIR / "files"
CONFIG_DB = CONFIG_DIR / "configs.json"


# ================== STORAGE ==================

def init_storage():
    CONFIG_DIR.mkdir(exist_ok=True)
    FILES_DIR.mkdir(exist_ok=True)
    if not CONFIG_DB.exists():
        data = {"configs": {}, "active": None}
        CONFIG_DB.write_text(json.dumps(data, indent=2))


def load_db():
    init_storage()
    return json.loads(CONFIG_DB.read_text())


def save_db(data):
    CONFIG_DB.write_text(json.dumps(data, indent=2))


# ================== QUẢN LÝ CẤU HÌNH ==================

def cmd_add(args):
    db = load_db()
    name = args.name

    if name in db["configs"]:
        print(f"[!] Cấu hình '{name}' đã tồn tại.", file=sys.stderr)
        sys.exit(1)

    src = Path(args.file).expanduser()
    if not src.exists():
        print(f"[!] File không tồn tại: {src}", file=sys.stderr)
        sys.exit(1)

    if src.suffix.lower() != ".conf":
        print("[!] File cấu hình WireGuard nên có đuôi .conf", file=sys.stderr)

    dst = FILES_DIR / f"{name}{src.suffix}"
    shutil.copy2(src, dst)

    db["configs"][name] = {
        "type": "wireguard",
        "file": str(dst),
    }
    save_db(db)

    print(f"[+] Đã thêm cấu hình '{name}' (WireGuard) -> {dst}")


def cmd_list(args):
    db = load_db()
    configs = db["configs"]
    if not configs:
        print("Chưa có cấu hình nào. Dùng: vpncli add <name> <file.conf>")
        return

    print("Danh sách cấu hình WireGuard:")
    for name, info in configs.items():
        mark = ""
        if db.get("active") and db["active"].get("name") == name:
            mark = " (đang dùng)"
        print(f" - {name}{mark} -> {info['file']}")


def cmd_remove(args):
    db = load_db()
    name = args.name

    if name not in db["configs"]:
        print(f"[!] Không tìm thấy cấu hình '{name}'", file=sys.stderr)
        sys.exit(1)

    # Không cho xóa nếu đang active
    if db.get("active") and db["active"].get("name") == name:
        print("[!] Cấu hình này đang được sử dụng. Hãy disconnect trước.", file=sys.stderr)
        sys.exit(1)

    info = db["configs"].pop(name)
    try:
        os.remove(info["file"])
    except FileNotFoundError:
        pass

    save_db(db)
    print(f"[-] Đã xóa cấu hình '{name}'")


# ================== KẾT NỐI / NGẮT KẾT NỐI ==================

def cmd_connect(args):
    db = load_db()
    name = args.name

    if name not in db["configs"]:
        print(f"[!] Không tìm thấy cấu hình '{name}'", file=sys.stderr)
        sys.exit(1)

    if db.get("active"):
        print(f"[!] Đã có kết nối đang hoạt động: {db['active']['name']}. Hãy disconnect trước.", file=sys.stderr)
        sys.exit(1)

    cfg = db["configs"][name]
    file_path = cfg["file"]

    # interface WireGuard: bạn có thể đặt cùng tên với cấu hình
    iface = args.iface or name

    try:
        # Có 2 kiểu gọi: wg-quick up <tên> hoặc wg-quick up <file.conf>
        # Ở đây dùng file.conf cho chắc.
        subprocess.run(["sudo", "wg-quick", "up", file_path], check=True)

        db["active"] = {
            "name": name,
            "type": "wireguard",
            "iface": iface,
        }
        save_db(db)
        print(f"[+] Đã kết nối WireGuard với cấu hình '{name}'")

    except subprocess.CalledProcessError:
        print("[!] Kết nối thất bại, kiểm tra lại quyền sudo và file cấu hình.", file=sys.stderr)
        sys.exit(1)


def cmd_disconnect(args):
    db = load_db()
    active = db.get("active")

    if not active:
        print("Không có kết nối VPN nào đang hoạt động.")
        return

    if active["type"] != "wireguard":
        print("[!] Loại cấu hình không phải WireGuard (dữ liệu bị lỗi?).", file=sys.stderr)
        sys.exit(1)

    name = active["name"]
    iface = active.get("iface") or name

    try:
        # Với wg-quick, có thể down bằng file hoặc tên interface
        subprocess.run(["sudo", "wg-quick", "down", iface], check=True)
        db["active"] = None
        save_db(db)
        print(f"[-] Đã ngắt kết nối WireGuard '{name}' (iface: {iface})")

    except subprocess.CalledProcessError:
        print("[!] Lỗi khi ngắt kết nối. Có thể interface không tồn tại.", file=sys.stderr)
        sys.exit(1)


# ================== TRẠNG THÁI ==================

def get_ip_for_iface(iface: str):
    """
    Lấy địa chỉ IP v4 của một interface bằng lệnh `ip`.
    """
    try:
        out = subprocess.check_output(["ip", "-4", "addr", "show", iface], text=True)
    except subprocess.CalledProcessError:
        return None

    for line in out.splitlines():
        line = line.strip()
        if line.startswith("inet "):
            # ví dụ: "inet 10.0.0.2/24 ..."
            parts = line.split()
            if len(parts) >= 2:
                return parts[1]  # "10.0.0.2/24"
    return None


def cmd_status(args):
    db = load_db()
    active = db.get("active")

    if not active:
        print("Trạng thái: Không có kết nối VPN nào đang hoạt động.")
        return

    if active["type"] != "wireguard":
        print("Trạng thái: Dữ liệu active không phải WireGuard (có thể hỏng file configs.json).")
        return

    name = active["name"]
    iface = active.get("iface") or name

    print("Trạng thái VPN hiện tại:")
    print(f" - Cấu hình: {name}")
    print(f" - Loại: WireGuard")
    print(f" - Interface: {iface}")

    ip = get_ip_for_iface(iface)
    if ip:
        print(f" - Địa chỉ IP: {ip}")
    else:
        print(" - Không lấy được IP (kiểm tra 'ip addr show')")

    print(" - Lưu lượng: có thể xem chi tiết bằng lệnh 'wg show'.")


# ================== PARSER / MAIN ==================

def build_parser():
    parser = argparse.ArgumentParser(
        prog="vpncli",
        description="VPNCli - tiện ích quản lý kết nối WireGuard (wrapper wg-quick)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="Thêm cấu hình WireGuard (.conf)")
    p_add.add_argument("name", help="Tên cấu hình (do bạn đặt)")
    p_add.add_argument("file", help="Đường dẫn tới file .conf")
    p_add.set_defaults(func=cmd_add)

    # list
    p_list = sub.add_parser("list", help="Liệt kê các cấu hình")
    p_list.set_defaults(func=cmd_list)

    # remove
    p_rm = sub.add_parser("remove", help="Xóa một cấu hình")
    p_rm.add_argument("name", help="Tên cấu hình cần xóa")
    p_rm.set_defaults(func=cmd_remove)

    # connect
    p_conn = sub.add_parser("connect", help="Kết nối VPN với một cấu hình WireGuard")
    p_conn.add_argument("name", help="Tên cấu hình")
    p_conn.add_argument(
        "--iface",
        help="Tên interface WireGuard (mặc định dùng tên cấu hình). "
             "Nên trùng với Interface trong file .conf, vd: wg0"
    )
    p_conn.set_defaults(func=cmd_connect)

    # disconnect
    p_disc = sub.add_parser("disconnect", help="Ngắt kết nối VPN hiện tại")
    p_disc.set_defaults(func=cmd_disconnect)

    # status
    p_status = sub.add_parser("status", help="Hiển thị trạng thái kết nối hiện tại")
    p_status.set_defaults(func=cmd_status)

    return parser


def main():
    init_storage()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
