# 📚 NGUỒN DỮ LIỆU (DATA PROVENANCE)

> Ghi chép nguồn cho 3 bộ dữ liệu tiêm chủng trong `config/`.
> **Ngày crawl**: 2026-07-28 · **Phiên bản dữ liệu**: `2026.07`

---

## 1. Bộ dữ liệu sinh ra từ đợt crawl này

| File | Nội dung | Số bản ghi |
| :--- | :--- | :---: |
| `config/vaccine_schedule.json` | Lịch tiêm theo tuổi (0–12 tuổi), danh mục 21 vắc xin | 34 mốc tiêm |
| `config/vaccine_contraindications.json` | Chống chỉ định, tạm hoãn, quy tắc khoảng cách & xung đột vắc xin | 6 chống chỉ định · 9 tạm hoãn · 7 quy tắc khoảng cách · 7 cặp xung đột |
| `config/vaccine_conditions.json` | Khuyến cáo theo bệnh nền + luật định tuyến Agent | 8 nhóm bệnh nền · 6 luật guardrail |

---

## 2. Nguồn pháp quy (ưu tiên cao nhất)

| Văn bản | Ngày | Hiệu lực | Dùng cho | Trạng thái crawl |
| :--- | :--- | :--- | :--- | :--- |
| **Thông tư 52/2025/TT-BYT** — Danh mục bệnh truyền nhiễm, đối tượng và phạm vi phải sử dụng vắc xin, sinh phẩm y tế bắt buộc. Thay thế TT 10/2024/TT-BYT | 31/12/2025 | 15/02/2026 | Lịch tiêm TCMR (12 bệnh) | ⚠️ Gián tiếp — phụ lục gốc dạng PDF |
| **Thông tư 13/2026/TT-BYT** — Bổ sung vắc xin HPV vào TCMR | 2026 | 01/07/2026 | Mũi HPV 11 tuổi | ⚠️ Chỉ qua báo chí, `can_kiem_chung: true` |
| **Quyết định 1575/QĐ-BYT** — Hướng dẫn khám sàng lọc trước tiêm chủng đối với trẻ em. Thay thế QĐ 2470/QĐ-BYT (14/6/2019) | 27/03/2023 | — | Chống chỉ định & tạm hoãn | ⚠️ Gián tiếp — bản gốc bị chặn |
| **Nghị quyết 104/NQ-CP** — Lộ trình tăng số lượng vắc xin trong TCMR | — | — | Lộ trình vắc xin phế cầu (PCV) | ✅ Qua nguồn thứ cấp |

### URL văn bản gốc

- Thông tư 52/2025/TT-BYT — https://tiemchungmorong.vn/document/thong-tu-52-2025-tt-byt-ngay-31-12-2025-cua-bo-y-te-ban-hanh-danh-muc-benh-truyen-nhiem-doi-tuong-va-pham-vi-phai-su-dung-vac-xin-sinh-pham-y-te-bat-buoc
- Thông tư 52/2025/TT-BYT (bản luatvietnam) — https://luatvietnam.vn/y-te/thong-tu-52-2025-tt-byt-danh-muc-benh-truyen-nhiem-va-vac-xin-bat-buoc-422882-d1.html
- Thông tư 52/2025/TT-BYT (bản PDF, BV Đa khoa Bạc Liêu) — https://bvdkbaclieu.gov.vn/van-ban-phap-quy/thong-tu-52-2025-tt-byt-ve-danh-muc-benh-truyen-nhiem-va-vac.html
- Quyết định 1575/QĐ-BYT — https://thuvienphapluat.vn/van-ban/The-thao-Y-te/Quyet-dinh-1575-QD-BYT-2023-Huong-dan-kham-sang-loc-truoc-tiem-chung-tre-em-560859.aspx

---

## 3. Bảng ánh xạ nguồn → trường dữ liệu

| Nguồn | URL | Kết quả crawl | Trích xuất được gì |
| :--- | :--- | :---: | :--- |
| **Sức khỏe & Đời sống** (Bộ Y tế) | https://suckhoedoisong.vn/bo-y-te-quy-dinh-moi-nhat-nhung-benh-truyen-nhiem-doi-tuong-phai-su-dung-vac-xin-sinh-pham-bat-buoc-169260103200321201.htm | ✅ 200 | **Bảng 12 bệnh + lịch tiêm TT 52/2025** — nguồn chính cho `lich_tiem` |
| **Trung tâm Tiêm chủng Long Châu** | https://tiemchunglongchau.com.vn/kien-thuc-tiem-chung/hoi-dap-bac-si-lich-tiem-chung-mo-rong-cho-tre-tu-0-den-24-thang-gom-nhung-mui-nao | ✅ 200 | Bảng TCMR 0–24 tháng dạng bảng — đối chiếu chéo mốc 5 tháng (IPV), 18 tháng (DPT mũi 4 + MR) |
| **BV Nhi Đồng Thành Phố** | https://bvndtp.org.vn/lich-tiem-chung-mo-rong/ | ✅ 200 | Xác nhận mốc IPV 5 tháng, VNNB 12 tháng, MR 18 tháng |
| **VNVC** — lịch 0–24 tháng | https://vnvc.vn/lich-tiem-chung-cho-tre-0-24-thang/ | ✅ 200 | Vắc xin **dịch vụ**: 6in1, PCV, Rota, não mô cầu, cúm, MMR, thủy đậu, VGA, Imojev, RSV |
| **Hello Bacsi** — TCMR 2026 | https://hellobacsi.com/nuoi-day-con/nhi-khoa/tiem-phong-cho-tre/chuong-trinh-tiem-chung-mo-rong-2026/ | ✅ 200 | Danh sách 13 bệnh TCMR 2026, lộ trình HPV & PCV & Rota |
| **eBH** — 14 bệnh bắt buộc | https://ebh.vn/tin-tuc/danh-muc-benh-phai-tiem-chung-bat-buoc | ✅ 200 | TT 13/2026/TT-BYT, mở rộng 10 → 14 mũi bắt buộc |
| **luatvietnam.vn** | https://luatvietnam.vn/y-te/thong-tu-52-2025-tt-byt-danh-muc-benh-truyen-nhiem-va-vac-xin-bat-buoc-422882-d1.html | ✅ 200 | Xác nhận 12 bệnh, hiệu lực 15/02/2026, thay thế TT 10/2024 |
| **BV Sản Nhi Vĩnh Phúc** | https://sannhivinhphuc.vn/danh-cho-khach-hang/tiem-chung/benh-truyen-nhiem/ | ✅ 200 | Đối chiếu danh mục 12 bệnh + đối tượng phụ nữ có thai |
| **bsgdtphcm.vn** (Bác sĩ Gia đình TP.HCM) | https://bsgdtphcm.vn/api/fullcontent.php?id=261 | ✅ 200 | **Chống chỉ định** trẻ >1 tháng & trẻ sơ sinh (QĐ 2470 → 1575) |
| **Cổng TTĐT Bắc Giang** | https://bacgiang.gov.vn/chi-tiet-chinh-sach-moi/.../huong-dan-kham-sang-loc-truoc-tiem-chung-oi-voi-tre-em/pop_up | ✅ 200 | **Tạm hoãn** đầy đủ + ngưỡng bilirubin 7 mg/dL |
| **Vinmec** — chống chỉ định & tạm hoãn | https://www.vinmec.com/vie/bai-viet/cac-truong-hop-chong-chi-dinh-va-tam-hoan-tiem-chung-vac-xin-vi | ✅ 200 | Ngưỡng sốt 37,5°C / 35,5°C, cân nặng 2000g, immunoglobulin 3 tháng, corticoid 14 ngày |
| **Hạnh Phúc Vaccine (hpvc.vn)** | https://hpvc.vn/khoang-cach-toi-thieu-giua-cac-mui-vaccine-cua-tre/ | ✅ 200 | **Quy tắc khoảng cách**: sống–sống 4 tuần, sống–bất hoạt 0, bất hoạt–bất hoạt 0, không tiêm lại từ đầu khi trễ lịch |
| **Long Châu** — tim bẩm sinh | https://tiemchunglongchau.com.vn/kien-thuc-tiem-chung/tre-bi-tim-bam-sinh-co-tiem-phong-duoc-khong-va-can-luu-y-gi | ✅ 200 | `BN_TIM_BAM_SINH`: tiêm được, hoãn khi suy tim cấp, khuyến khích PCV/cúm/Hib/RSV |
| **BV Đại học Y Dược** — tim bẩm sinh | https://bvdaihoc.com.vn/en/health-library/tiem-chung-cho-tre-mac-benh-tim-bam-sinh-nhung-dieu-cha-me-can-biet-p-3001 | 🔍 chỉ qua search | Xác nhận: chống chỉ định tuyệt đối rất hiếm |
| **Vinmec** — trẻ sinh non | https://www.vinmec.com/vie/bai-viet/tiem-vac-xin-cho-tre-sinh-non-nhung-dieu-can-biet-vi | ✅ 200 | `BN_SINH_NON`: ngưỡng 2000g, mẹ HBsAg(+/−), tuổi thai 34 tuần ⚠️ *xem mục 5* |
| **VNVC** — lịch trẻ sinh non | https://vnvc.vn/lich-tiem-chung-cho-tre-sinh-non/ | 🔍 chỉ qua search | **Chốt: tiêm theo TUỔI THỰC, không hiệu chỉnh** (WHO/CDC) |
| **Long Châu** — trẻ sinh non | https://tiemchunglongchau.com.vn/kien-thuc-tiem-chung/hoi-dap-bac-si-lich-tiem-chung-cho-tre-sinh-non-co-gi-khac-tre-du-thang | 🔍 chỉ qua search | Đối chiếu tuổi thực |

**Chú thích cột "Kết quả crawl"**: ✅ 200 = fetch được toàn văn · 🔍 = chỉ lấy được qua kết quả tìm kiếm, chưa fetch trang · ⚠️ = bị chặn, dùng nguồn thay thế

---

## 4. Nguồn bị chặn (crawl thất bại)

| Nguồn | Mã lỗi | Nguồn thay thế đã dùng |
| :--- | :---: | :--- |
| `thuvienphapluat.vn` (toàn văn TT 52/2025 & QĐ 1575) | **403** | suckhoedoisong.vn + luatvietnam.vn + bsgdtphcm.vn |
| `luatminhkhue.vn` (QĐ 1575) | **403** | bacgiang.gov.vn + bsgdtphcm.vn |
| `ksbtdanang.vn` (khám sàng lọc) | **403** | bacgiang.gov.vn |
| `hcdc.vn` (lịch TCMR) | 200 nhưng **bảng đăng dạng ảnh** | bvndtp.org.vn + tiemchunglongchau.com.vn |
| `tiemchungmorong.vn/vi/content/lich-tiem-chung-cho-tre-em-0` | **404** | Trang `/document/` của cùng site |
| `vnvc.vn/lich-tiem-chung-cho-tre-em/` | **404** | `vnvc.vn/lich-tiem-chung-cho-tre-0-24-thang/` |
| `nhathuoclongchau.com.vn/bai-viet/lich-tiem-chung-cho-tre-em` | **404** | `tiemchunglongchau.com.vn` |
| `24h.com.vn` | 200 nhưng **không có bảng** | — |

---

## 5. ⚠️ Xung đột nguồn đã phát hiện & cách xử lý

| # | Xung đột | Nguồn A | Nguồn B | Quyết định |
| :---: | :--- | :--- | :--- | :--- |
| 1 | **Trẻ sinh non tính tuổi nào?** | Vinmec: "tuổi hiệu chỉnh" (tuổi thực trừ số tuần sinh non) | VNVC / Long Châu / WHO / CDC: **tuổi thực** | Dùng **tuổi thực**. Đã ghi cờ `canh_bao_du_lieu` trong `BN_SINH_NON`. Bản tóm tắt Vinmec nhiều khả năng sai/diễn đạt nhầm |
| 2 | **Phế cầu (PCV) mũi 2 lúc mấy tháng?** | TT 52/2025: mũi 2 cách mũi 1 **2 tháng** → 4 tháng tuổi | VNVC/Long Châu (dịch vụ): phác đồ **2–3–4 tháng** | Giữ **cả hai** bản ghi, phân biệt bằng trường `chuong_trinh` (`TCMR_lo_trinh` vs `dich_vu`). Bản ghi dịch vụ gắn `can_kiem_chung: true` |
| 3 | **Số bệnh bắt buộc: 12, 13 hay 14?** | TT 52/2025: **12** bệnh | Hello Bacsi: **13**; eBH: **14** mũi | TT 52/2025 = 12 bệnh (hiệu lực 15/02/2026). TT 13/2026 bổ sung HPV (hiệu lực 01/07/2026). Chênh lệch do đếm *bệnh* vs đếm *mũi* và do mốc thời gian khác nhau. Đã ghi rõ trong `meta.can_cu_phap_ly` |
| 4 | **Mũi sởi thứ 2 lúc 18 tháng là "Rubella" hay "Sởi–Rubella"?** | suckhoedoisong.vn liệt kê dòng "Rubella — 18 tháng" | bvndtp / Long Châu: vắc xin **MR (sởi–rubella)** | Dùng **MR**, vì TCMR Việt Nam dùng vắc xin phối hợp MRVAC. Dòng "Rubella" của nguồn A là cách liệt kê theo *bệnh*, không theo *vắc xin* |
| 5 | **IPV mũi 1 lúc 5 tháng** | bvndtp.org.vn + tiemchunglongchau.com.vn có mốc này | Bảng TT 52/2025 (bản suckhoedoisong) không nêu rõ | Giữ bản ghi, gắn `can_kiem_chung: true` |

---

## 6. Trường siêu dữ liệu dùng trong JSON

| Trường | Ý nghĩa |
| :--- | :--- |
| `nguon` | Nguồn gốc của bản ghi — Agent **bắt buộc** trích dẫn trường này trong Final Answer |
| `can_kiem_chung: true` | Bản ghi chưa đối chiếu được văn bản gốc. Không dùng ngoài phạm vi bài Lab |
| `chuong_trinh` | `TCMR` (miễn phí, bắt buộc) · `TCMR_lo_trinh` (đang mở rộng theo NQ 104) · `dich_vu` (trả phí) |
| `bat_buoc` | Có nằm trong danh mục tiêm chủng bắt buộc theo thông tư hay không |
| `muc_do` (cặp xung đột) | `chan` = không được dùng song song · `canh_bao` = cần cách khoảng hoặc lưu ý |

---

## 7. Giới hạn của bộ dữ liệu

1. **Không phải văn bản pháp quy.** Đây là snapshot thứ cấp phục vụ bài Lab. Trước khi dùng ngoài lớp học, phải đối chiếu bản PDF gốc của Thông tư 52/2025/TT-BYT và Quyết định 1575/QĐ-BYT.
2. **Không có dữ liệu tồn kho vắc xin.** Tồn kho theo từng chi nhánh Long Châu không công khai. Tool `check_stock` sẽ là **mock**, phải khai báo rõ trong docstring.
3. **Không có giá.** Giá vắc xin dịch vụ thay đổi liên tục, không snapshot.
4. **Không thay thế khám sàng lọc.** Mọi bản ghi đều gắn disclaimer. Guardrail trong `vaccine_conditions.json > quy_tac_dinh_tuyen_agent` là bắt buộc, không phải tùy chọn.
5. **Chỉ phạm vi 0–12 tuổi.** Ngoài khoảng này Agent phải trả lời "không có dữ liệu", cấm ngoại suy.

---

## 8. Quy trình cập nhật lại

Khi cần refresh dữ liệu:

1. Kiểm tra `tiemchungmorong.vn/document` xem có thông tư mới thay thế TT 52/2025 không.
2. Fetch lại các URL ở **mục 3** đang có ✅.
3. Cập nhật `meta.phien_ban` và `meta.ngay_crawl` trong cả 3 file JSON.
4. Chạy lại bảng xung đột ở **mục 5** — nếu nguồn nào đã sửa, gỡ cờ `can_kiem_chung`.
