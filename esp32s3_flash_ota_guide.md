# Hướng dẫn Build, Flash và OTA ESP32-S3

Project: `nav_tft_s3`  
Port: `COM6`  
Baudrate: `921600`  
Target chip: `esp32s3`

> Lưu ý: Các lệnh bên dưới dùng đường dẫn tương đối từ thư mục:
>
> ```powershell
> D:\ME\Project\Map_TFT\nav_tft_s3
> ```
>
> Thư mục `nav_ota` nằm cùng cấp với `nav_tft_s3`.

---

## 0. Build và Monitor bằng ESP-IDF

Build project:

```powershell
idf.py build
```

Mở monitor:

```powershell
idf.py -p COM6 monitor
```

---

## 1. Flash OTA Agent

Flash `ota_agent_main.bin` vào địa chỉ `0xB00000`:

```powershell
python -m esptool --chip esp32s3 --port COM6 --baud 921600 write_flash 0xB00000 "..\nav_ota\releases\download\v0.0.0\ota_agent_main.bin"
```

---

## 2. Flash BEGIN

Flash bootloader, partition table và app chính:

```powershell
python -m esptool --chip esp32s3 --port COM6 --baud 921600 write_flash 0x0 "..\nav_ota\releases\download\v0.0.0\bootloader.bin" 0x8000 "..\nav_ota\releases\download\v0.0.0\partition-table.bin" 0x100000 "..\nav_ota\releases\download\v0.0.0\nav_tft_s3.bin"
```

Trong đó:

| Thành phần | Offset | File |
|---|---:|---|
| Bootloader | `0x0` | `bootloader.bin` |
| Partition table | `0x8000` | `partition-table.bin` |
| Main app | `0x100000` | `nav_tft_s3.bin` |

---

## 3. Flash MAIN

### app_0

Flash app chính vào partition `app_0` tại địa chỉ `0x100000`:

```powershell
python -m esptool --chip esp32s3 --port COM6 --baud 921600 write_flash 0x100000 "..\nav_ota\releases\download\v0.0.0\nav_tft_s3.bin"
```

### app_1

Flash app chính vào partition `app_1` tại địa chỉ `0x600000`:

```powershell
python -m esptool --chip esp32s3 --port COM6 --baud 921600 write_flash 0x600000 "..\nav_ota\releases\download\v0.0.0\nav_tft_s3.bin"
```

---

## 4. Generate Check Update

Tạo thông tin kiểm tra cập nhật OTA cho version `0.0.0`:

```powershell
python gen_check_update.py --version 0.0.0 --raw-base https://raw.githubusercontent.com/htanh2002/nav_ota/main/releases/download/v0.0.0
```

---

## Gợi ý quy trình nạp sạch

Khi cần nạp lại từ đầu, nên xóa flash trước:

```powershell
python -m esptool --chip esp32s3 --port COM6 --baud 921600 erase_flash
```

Sau đó chạy lệnh **Flash BEGIN** ở mục 2.

---

## Ghi chú

- Với ESP32-S3, bootloader được flash tại offset `0x0`.
- Offset app `0x100000` và `0x600000` phải khớp với `partition-table.bin`.
- Nếu thay đổi partition table, nên build lại và flash lại cả `bootloader.bin`, `partition-table.bin` và app.
