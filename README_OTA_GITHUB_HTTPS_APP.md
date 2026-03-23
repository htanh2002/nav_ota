# README OTA qua Git/GitHub + HTTPS + App thật

## 1. Mục tiêu

Tài liệu này tổng hợp luồng OTA hiện tại cho dự án Navigation App ↔ ESP theo hướng đã triển khai thực tế:

- OTA dùng **HTTPS**
- nguồn firmware và metadata OTA đặt trên **Git/GitHub**
- **app mobile thật** là bên kiểm tra bản cập nhật
- app gửi lệnh OTA sang ESP qua **BLE**
- ESP lưu cấu hình OTA, reboot sang `ota_tool`
- `ota_tool` kết nối Wi-Fi và tải firmware qua **HTTPS** để flash vào slot đích

Tài liệu này **không còn dùng luồng test qua UART/console** nữa.

---

## 2. Kiến trúc OTA hiện tại

Có 4 thành phần chính:

1. **Git/GitHub hosting**
   - chứa file firmware `.bin`
   - chứa file `check_update.json`
   - phục vụ qua **HTTPS**

2. **App mobile**
   - kết nối BLE với ESP
   - đọc version hiện tại từ ESP
   - gọi `check_update.json` qua HTTPS
   - so sánh version
   - gửi `CMD_OTA_START` cho ESP khi người dùng bấm update

3. **ESP app chính**
   - nhận metadata OTA từ app qua BLE
   - lưu `fw_url`, `ver`, `target_slot`, cờ `pending`
   - đổi boot partition sang `ota_tool`
   - restart

4. **ota_tool**
   - đọc cấu hình OTA đã lưu
   - kết nối Wi-Fi
   - tải firmware từ `fw_url` qua HTTPS
   - flash vào partition đích (`main_0` hoặc `main_1`)
   - set boot sang firmware mới
   - restart

---

## 3. Vai trò của app trong luồng OTA

App là bên điều phối quá trình update.

App thực hiện các việc sau:

1. kết nối BLE tới ESP
2. lấy version hiện tại của ESP
3. gọi file `check_update.json` trên Git/GitHub qua HTTPS
4. parse metadata OTA
5. so sánh version server với version hiện tại của ESP
6. nếu có bản mới, gửi `CMD_OTA_START` xuống ESP

App **không cần tải firmware về máy rồi gửi sang ESP**.

Trong kiến trúc hiện tại:

- app chỉ làm nhiệm vụ **check update** và **gửi metadata OTA**
- ESP mới là bên **thật sự tải file `.bin`**

---

## 4. Nguồn OTA trên Git/GitHub

Hiện tại có thể dùng GitHub theo 2 cách.

### 4.1. Cách đang dùng để test nhanh

- lưu `check_update.json` ở root repo
- lưu file `.bin` trong repo
- app gọi `raw.githubusercontent.com`

Ví dụ:

- metadata OTA:
  - `https://raw.githubusercontent.com/<user>/<repo>/main/check_update.json`
- firmware:
  - `https://raw.githubusercontent.com/<user>/<repo>/main/releases/download/v1.0.1/nav_tft_s3.bin`

Cách này phù hợp để thử nhanh end-to-end.

### 4.2. Cách khuyến nghị lâu dài

- **GitHub Pages**: host `check_update.json`
- **GitHub Releases**: host file firmware `.bin`

Ví dụ:

- `https://<user>.github.io/<repo>/check_update.json`
- `https://github.com/<user>/<repo>/releases/download/v1.0.3/firmware.bin`

Ưu điểm:

- quản lý version rõ ràng hơn
- phù hợp khi có nhiều bản firmware
- giảm việc commit trực tiếp file `.bin` vào repo chính

---

## 5. Cấu trúc `check_update.json`

Để tương thích nhanh với app hiện tại, file `check_update.json` nên theo cấu trúc:

```json
{
  "code": 2101,
  "message": "New firmware available",
  "firmware": {
    "version": "1.0.1",
    "url": "https://raw.githubusercontent.com/<user>/<repo>/main/releases/download/v1.0.1/nav_tft_s3.bin",
    "name": "nav_tft_s3.bin",
    "sha256": "",
    "size": 1908408
  },
  "timestamp": "2026-03-23T10:00:00Z"
}
```

### Ý nghĩa các trường chính

- `firmware.version`: version mới trên server
- `firmware.url`: URL HTTPS để ESP tải firmware
- `firmware.name`: tên file firmware
- `firmware.sha256`: hash để kiểm tra toàn vẹn, có thể để trống ở giai đoạn đầu
- `firmware.size`: kích thước file theo byte
- `message`: thông điệp mô tả ngắn
- `timestamp`: thời điểm publish metadata

---

## 6. Endpoint app đang dùng

Ở giai đoạn hiện tại, app nên đọc trực tiếp file JSON bằng HTTPS, ví dụ:

```text
https://raw.githubusercontent.com/htanh2002/nav_ota/main/check_update.json
```

App parse:

- `json.firmware.version`
- `json.firmware.url`
- `json.message`

Sau đó so sánh với version hiện tại của ESP.

---

## 7. Luồng OTA chuẩn đang dùng

### Bước 1: App kết nối BLE tới ESP

App connect đúng service/characteristic OTA/control theo protocol BLE hiện tại.

### Bước 2: App đọc version hiện tại của ESP

ESP cần trả về version hiện tại để app có dữ liệu so sánh.

Ví dụ event OTA từ ESP:

```json
{
  "type": "ota",
  "current": "1.0.0",
  "state": "idle",
  "message": "ready"
}
```

### Bước 3: App gọi `check_update.json`

App gọi HTTPS tới Git/GitHub, ví dụ:

```text
https://raw.githubusercontent.com/htanh2002/nav_ota/main/check_update.json
```

App parse ra:

- version mới
- URL firmware
- metadata khác nếu có

### Bước 4: App so sánh version

Ví dụ:

- ESP hiện tại: `1.0.0`
- server: `1.0.1`

Khi `server > current`, app báo có bản mới và cho phép update.

### Bước 5: App gửi `CMD_OTA_START`

Payload gửi xuống ESP là JSON, ví dụ:

```json
{
  "fw_url": "https://raw.githubusercontent.com/htanh2002/nav_ota/main/releases/download/v1.0.1/nav_tft_s3.bin",
  "ver": "1.0.1"
}
```

### Bước 6: ESP app chính lưu cấu hình OTA

ESP parse payload và lưu các trường:

- `fw_url`
- `ver`
- `pending = 1`
- `target_slot`

Sau đó:

- xác định slot đích
- set boot partition sang `ota_tool`
- restart

### Bước 7: `ota_tool` chạy OTA thật

Sau khi boot vào `ota_tool`:

1. đọc cấu hình OTA đã lưu
2. kết nối Wi-Fi
3. chọn partition đích (`main_0` hoặc `main_1`)
4. tải firmware qua HTTPS
5. ghi firmware vào partition đích
6. set boot sang partition mới
7. restart

### Bước 8: Firmware mới khởi động

Sau khi reboot, thiết bị chạy firmware mới ở slot vừa được flash.

---

## 8. Luồng tổng thể

```text
Git/GitHub (HTTPS)
    |
    | 1. check_update.json
    v
App mobile
    |
    | 2. parse version + fw_url
    | 3. compare với version hiện tại của ESP
    | 4. gửi CMD_OTA_START qua BLE
    v
ESP app chính
    |
    | 5. lưu nav_ota_cfg
    | 6. set boot partition = ota_tool
    | 7. restart
    v
ota_tool
    |
    | 8. connect Wi-Fi
    | 9. tải firmware qua HTTPS
    | 10. flash vào main_0 / main_1
    | 11. set boot partition mới
    | 12. restart
    v
Firmware mới
```

---

## 9. Yêu cầu HTTPS ở `ota_tool`

Vì firmware được tải qua HTTPS, `ota_tool` phải cấu hình xác minh chứng chỉ TLS.

Cách phù hợp hiện tại là dùng certificate bundle:

- include `esp_crt_bundle.h`
- gán `.crt_bundle_attach = esp_crt_bundle_attach` trong `esp_http_client_config_t`
- bật `CONFIG_MBEDTLS_CERTIFICATE_BUNDLE=y`

Ví dụ cấu hình:

```c
esp_http_client_config_t config = {
    .url = url,
    .timeout_ms = OTA_HTTP_TIMEOUT_MS,
    .buffer_size = OTA_BUF_SIZE,
    .keep_alive_enable = true,
    .crt_bundle_attach = esp_crt_bundle_attach,
};
```

Nếu thiếu phần verify này, HTTPS OTA sẽ lỗi ở bước TLS handshake.

---

## 10. Trạng thái triển khai hiện tại

Luồng hiện tại đã đi được đến mức:

- app gửi `CMD_OTA_START` thành công
- ESP app chính lưu được `fw_url`, `ver`, `target_slot`
- ESP reboot sang `ota_tool`
- `ota_tool` kết nối Wi-Fi thành công
- `ota_tool` bắt đầu tải file OTA qua HTTPS

Phần cần đảm bảo khi triển khai hoàn chỉnh:

- URL firmware phải là HTTPS hợp lệ
- `ota_tool` phải bật TLS verification đúng cách
- app phải đọc được version hiện tại từ ESP để so sánh

---

## 11. Checklist triển khai

### Phía Git/GitHub

- [ ] Có file `check_update.json`
- [ ] Có file firmware `.bin`
- [ ] URL truy cập bằng HTTPS hợp lệ
- [ ] Repo/file ở trạng thái public nếu app cần truy cập trực tiếp

### Phía app

- [ ] BLE connect được với ESP
- [ ] Đọc được version hiện tại từ ESP
- [ ] Fetch được `check_update.json`
- [ ] Parse đúng `firmware.version` và `firmware.url`
- [ ] So sánh version đúng
- [ ] Gửi được `CMD_OTA_START`

### Phía ESP app chính

- [ ] Nhận được `CMD_OTA_START`
- [ ] Parse đúng JSON payload
- [ ] Lưu được `nav_ota_cfg`
- [ ] Xác định đúng `target_slot`
- [ ] Set boot partition sang `ota_tool`

### Phía `ota_tool`

- [ ] Đọc được OTA config đã lưu
- [ ] Kết nối Wi-Fi thành công
- [ ] HTTPS download thành công
- [ ] Flash đúng partition đích
- [ ] Set boot sang app mới
- [ ] Restart thành công

---

## 12. Ghi chú

- Giai đoạn hiện tại tập trung vào **OTA firmware app**
- chưa đề cập chi tiết OTA cho filesystem/data partition
- không còn mô tả nhánh **test qua UART**
- tài liệu này phản ánh luồng OTA thực tế đang dùng: **App thật + Git/GitHub + HTTPS + ota_tool**
