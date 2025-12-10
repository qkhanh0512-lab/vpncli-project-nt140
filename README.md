# VPNCli – Client VPN dòng lệnh cho WireGuard

## 1. Tầm nhìn & Mục đích

VPNCli **không tự triển khai giao thức VPN**, mà là một **công cụ dòng lệnh (wrapper)** giúp:
- Quản lý các file cấu hình WireGuard (`.conf`).
- Thực hiện kết nối / ngắt kết nối bằng lệnh hệ thống:
  - `wg-quick up`
  - `wg-quick down`
- Hiển thị trạng thái kết nối hiện tại (tên cấu hình, interface, địa chỉ IP).

Mục tiêu: Đơn giản hóa việc sử dụng WireGuard cho người dùng qua một lệnh duy nhất `vpncli`.

## 2. Yêu cầu hệ thống

- Hệ điều hành: Linux
- Đã cài:
  - Python 3
  - WireGuard (`wg-quick`, `wg`)
  - Lệnh `ip` (thường có sẵn trong `iproute2`)
- Có quyền `sudo` để thiết lập kết nối VPN.

## 3. Cài đặt

```bash
git clone <link_repo>
cd vpncli
chmod +x vpncli.py
