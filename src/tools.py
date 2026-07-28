"""
🛠️ TOOL REGISTRY & SCHEMAS (Dành cho Role 2: Tool & Spec Engineer)
Nơi khai báo tất cả các "món đồ nghề" mà ReAct Agent có thể gọi.

Chủ đề: TRỢ LÝ TRA CỨU LỊCH TIÊM CHỦNG TRẺ EM & TÌM NHÀ THUỐC LONG CHÂU

Nguồn dữ liệu (thư mục data/):
    - vaccine_schedule.json          : lịch tiêm theo tuổi + danh mục vắc xin
    - vaccine_contraindications.json : chống chỉ định, tạm hoãn, quy tắc khoảng cách
    - vaccine_conditions.json        : khuyến cáo theo bệnh nền
    - pharmacies.json                : chi nhánh Long Châu + tồn kho (MOCK)

HỢP ĐỒNG CHUNG CỦA MỌI TOOL:
    - Luôn trả về str, KHÔNG BAO GIỜ raise exception ra ngoài.
    - Lỗi nghiệp vụ trả chuỗi bắt đầu bằng "LỖI:" hoặc "KHÔNG CÓ DỮ LIỆU:"
      để Agent đọc được và tự đổi hướng.
    - Mọi kết quả y tế đều kèm trường nguồn để Agent trích dẫn.
"""

import json
import os
import unicodedata
from datetime import datetime

# =============================================================================
# 📂 NẠP DỮ LIỆU (DATA LAYER)
# Dùng đường dẫn tính từ vị trí file này, KHÔNG phụ thuộc thư mục hiện hành.
# =============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
APPOINTMENTS_PATH = os.path.join(DATA_DIR, "appointments.json")


def _load(filename: str) -> dict:
    """Nạp một file JSON trong thư mục data/. Trả dict rỗng nếu thiếu file."""
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ CẢNH BÁO: Không tìm thấy {path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"⚠️ CẢNH BÁO: {filename} lỗi cú pháp JSON - {e}")
        return {}


SCHEDULE_DB = _load("vaccine_schedule.json")
CONTRA_DB = _load("vaccine_contraindications.json")
CONDITIONS_DB = _load("vaccine_conditions.json")
PHARMACY_DB = _load("pharmacies.json")

VACCINE_CATALOG = SCHEDULE_DB.get("danh_muc_vaccine", {})
SCHEDULE_ENTRIES = SCHEDULE_DB.get("lich_tiem", [])

MIN_AGE_MONTHS = 0
MAX_AGE_MONTHS = 144  # 12 tuổi - phạm vi bao phủ của bộ dữ liệu


# =============================================================================
# 🔧 TIỆN ÍCH NỘI BỘ
# =============================================================================

def _strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt để so khớp chuỗi dễ hơn (Cầu Giấy == cau giay)."""
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").lower()


def _norm(text: str) -> str:
    """Chuẩn hoá chuỗi để so khớp: bỏ dấu, thường hoá, gộp khoảng trắng."""
    return " ".join(_strip_accents(str(text)).split())


def _vaccine_name(vaccine_id: str) -> str:
    """Lấy tên hiển thị của vắc xin từ id, fallback về chính id."""
    return VACCINE_CATALOG.get(vaccine_id, {}).get("ten", vaccine_id)


def _resolve_vaccine_id(query: str):
    """
    Tìm vaccine_id từ chuỗi người dùng/LLM nhập.
    Chấp nhận: id chính xác, tên đầy đủ, tên thương mại, hoặc tên bệnh.
    Trả về vaccine_id hoặc None.
    """
    if not query:
        return None
    q = _norm(query)

    # 1. Khớp id chính xác (không phân biệt hoa thường)
    for vid in VACCINE_CATALOG:
        if _norm(vid) == q:
            return vid

    # 2. Khớp tên đầy đủ hoặc tên thương mại
    for vid, info in VACCINE_CATALOG.items():
        if q in _norm(info.get("ten", "")):
            return vid
        for tm in info.get("ten_thuong_mai", []):
            if q in _norm(tm) or _norm(tm) in q:
                return vid

    # 3. Khớp theo tên bệnh phòng ngừa
    for vid, info in VACCINE_CATALOG.items():
        for benh in info.get("phong_benh", []):
            if q in _norm(benh) or _norm(benh) in q:
                return vid

    return None


def _parse_age(raw) -> int:
    """
    Ép tham số tuổi về int tháng. Ném ValueError nếu không hợp lệ.
    Chấp nhận: "2", "2 tháng", "36".
    """
    text = str(raw).strip().lower()
    for suffix in ["tháng tuổi", "thang tuoi", "tháng", "thang", "months", "month"]:
        text = text.replace(suffix, "")
    return int(text.strip())


# =============================================================================
# 🧰 TOOL 1: TÍNH TUỔI THEO THÁNG TỪ NGÀY SINH
# =============================================================================

def calculate_age_months(birth_date: str) -> str:
    """
    Đổi ngày sinh của trẻ sang số tháng tuổi.

    Args:
        birth_date (str): Ngày sinh. Chấp nhận các định dạng:
                          'dd/mm/yyyy', 'yyyy-mm-dd', 'dd-mm-yyyy'.

    Returns:
        str: Số tháng tuổi kèm diễn giải, hoặc chuỗi 'LỖI: ...' nếu sai định dạng.

    Ví dụ:
        calculate_age_months('01/05/2023') -> 'Trẻ sinh 01/05/2023, hiện 38 tháng tuổi...'
    """
    raw = str(birth_date).strip().strip("'\"")
    parsed = None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            parsed = datetime.strptime(raw, fmt)
            break
        except ValueError:
            continue

    if parsed is None:
        return (
            f"LỖI: Không đọc được ngày sinh '{birth_date}'. "
            f"Định dạng hợp lệ: dd/mm/yyyy (ví dụ 01/05/2023) hoặc yyyy-mm-dd."
        )

    today = datetime.now()
    if parsed > today:
        return f"LỖI: Ngày sinh '{raw}' nằm ở tương lai, không hợp lệ."

    months = (today.year - parsed.year) * 12 + (today.month - parsed.month)
    if today.day < parsed.day:
        months -= 1

    if months > MAX_AGE_MONTHS:
        return (
            f"Trẻ sinh {raw} hiện {months} tháng tuổi ({months // 12} tuổi). "
            f"KHÔNG CÓ DỮ LIỆU: vượt phạm vi bộ dữ liệu (tối đa {MAX_AGE_MONTHS} tháng = 12 tuổi)."
        )

    return (
        f"Trẻ sinh ngày {raw}, tính đến {today.strftime('%d/%m/%Y')} là {months} tháng tuổi "
        f"({months // 12} tuổi {months % 12} tháng). Dùng age_months={months} để tra lịch tiêm."
    )


# =============================================================================
# 🧰 TOOL 2: TRA LỊCH TIÊM THEO TUỔI
# =============================================================================

def lookup_vaccine_schedule(age_months) -> str:
    """
    Tra các mũi tiêm theo tuổi của trẻ: mũi đến hạn ngay tại mốc này,
    các mũi lẽ ra đã phải tiêm trước đó, và mũi kế tiếp sắp tới.

    Args:
        age_months (int | str): Tuổi của trẻ tính bằng THÁNG (0 - 144).

    Returns:
        str: Danh sách mũi tiêm kèm nguồn trích dẫn,
             hoặc 'LỖI: ...' nếu tuổi ngoài phạm vi dữ liệu.

    Ví dụ:
        lookup_vaccine_schedule(2) -> các mũi đến hạn lúc 2 tháng tuổi.
    """
    try:
        age = _parse_age(age_months)
    except (ValueError, TypeError):
        return (
            f"LỖI: Tuổi '{age_months}' không phải số hợp lệ. "
            f"Cần truyền số tháng tuổi dạng số nguyên, ví dụ lookup_vaccine_schedule[2]."
        )

    if not (MIN_AGE_MONTHS <= age <= MAX_AGE_MONTHS):
        return (
            f"LỖI: Tuổi {age} tháng nằm ngoài phạm vi dữ liệu "
            f"({MIN_AGE_MONTHS}-{MAX_AGE_MONTHS} tháng, tức 0-12 tuổi). "
            f"Không được ngoại suy - hãy dùng Final Answer báo người dùng không có dữ liệu."
        )

    if not SCHEDULE_ENTRIES:
        return "LỖI: Chưa nạp được dữ liệu lịch tiêm từ data/vaccine_schedule.json."

    dung_han = [e for e in SCHEDULE_ENTRIES if e["tuoi_thang"] == age]
    da_qua = [e for e in SCHEDULE_ENTRIES if e["tuoi_thang"] < age]
    sap_toi = [e for e in SCHEDULE_ENTRIES if e["tuoi_thang"] > age]

    def _fmt(entry):
        vid = entry["vaccine_id"]
        info = VACCINE_CATALOG.get(vid, {})
        loai = "BẮT BUỘC (TCMR miễn phí)" if entry.get("bat_buoc") else "Dịch vụ (tự nguyện)"
        line = (
            f"  - [{vid}] {info.get('ten', vid)} | mũi {entry['mui']} | {loai}\n"
            f"    Phòng: {', '.join(info.get('phong_benh', []))}\n"
            f"    Mốc: {entry['tuoi_hien_thi']} | Nguồn: {entry.get('nguon', 'n/a')}"
        )
        if entry.get("ghi_chu"):
            line += f"\n    Ghi chú: {entry['ghi_chu']}"
        if entry.get("can_kiem_chung"):
            line += "\n    ⚠️ Bản ghi cần kiểm chứng lại văn bản gốc."
        return line

    out = [f"=== TRA CỨU LỊCH TIÊM CHO TRẺ {age} THÁNG TUỔI ({age // 12} tuổi {age % 12} tháng) ==="]

    if dung_han:
        out.append(f"\n[A] ĐẾN HẠN ĐÚNG MỐC {age} THÁNG ({len(dung_han)} mũi):")
        out.extend(_fmt(e) for e in dung_han)
    else:
        out.append(f"\n[A] Không có mũi nào đến hạn đúng tại mốc {age} tháng tuổi.")

    if da_qua:
        out.append(
            f"\n[B] CÁC MŨI LẼ RA ĐÃ PHẢI TIÊM TRƯỚC {age} THÁNG ({len(da_qua)} mũi) "
            f"- cần đối chiếu sổ tiêm chủng của bé xem còn thiếu mũi nào."
        )
        # Tách theo nơi tiêm: TCMR tiêm miễn phí ở trạm y tế, dịch vụ mới có ở Long Châu.
        # Không tách thì Agent sẽ đi hỏi tồn kho những vắc xin Long Châu không bán.
        tcmr = sorted({_vaccine_name(e["vaccine_id"]) for e in da_qua if e.get("bat_buoc")})
        dv_ids = sorted({e["vaccine_id"] for e in da_qua
                         if not e.get("bat_buoc")
                         and VACCINE_CATALOG.get(e["vaccine_id"], {}).get("loai_vaccine")
                         != "khang_the_don_dong"})
        if tcmr:
            out.append(f"  • Nhóm TCMR (MIỄN PHÍ tại trạm y tế phường/xã, KHÔNG bán tại Long Châu): "
                       f"{'; '.join(tcmr)}")
        if dv_ids:
            out.append(f"  • Nhóm DỊCH VỤ (có thể mua/tiêm tại Long Châu) - dùng đúng các mã này khi "
                       f"gọi check_stock: {', '.join(dv_ids)}")
        out.append("  ➡️ Khi tra tồn kho tại Long Châu, CHỈ dùng mã ở nhóm DỊCH VỤ.")

    if sap_toi:
        moc_ke = min(e["tuoi_thang"] for e in sap_toi)
        ke_tiep = [e for e in sap_toi if e["tuoi_thang"] == moc_ke]
        out.append(f"\n[C] MŨI KẾ TIẾP - mốc {moc_ke} tháng tuổi:")
        out.extend(_fmt(e) for e in ke_tiep)

    out.append(
        "\nCăn cứ: Thông tư 52/2025/TT-BYT (hiệu lực 15/02/2026). "
        "Bắt buộc khám sàng lọc trước tiêm theo Quyết định 1575/QĐ-BYT."
    )
    return "\n".join(out)


# =============================================================================
# 🧰 TOOL 3: THÔNG TIN CHI TIẾT MỘT VẮC XIN
# =============================================================================

def get_vaccine_info(vaccine_id: str) -> str:
    """
    Tra thông tin chi tiết một loại vắc xin.

    Args:
        vaccine_id (str): Mã vắc xin (VD 'DPT_VGB_Hib'), tên đầy đủ,
                          tên thương mại, hoặc tên bệnh cần phòng.

    Returns:
        str: Thông tin vắc xin và các mốc tiêm, hoặc 'KHÔNG CÓ DỮ LIỆU: ...'.

    Ví dụ:
        get_vaccine_info('Thuy_dau') / get_vaccine_info('thủy đậu')
    """
    vid = _resolve_vaccine_id(vaccine_id)
    if vid is None:
        return (
            f"KHÔNG CÓ DỮ LIỆU: Không tìm thấy vắc xin '{vaccine_id}'. "
            f"Các mã hợp lệ: {', '.join(sorted(VACCINE_CATALOG.keys()))}"
        )

    info = VACCINE_CATALOG[vid]
    moc = [e for e in SCHEDULE_ENTRIES if e["vaccine_id"] == vid]

    loai_map = {
        "song_giam_doc_luc": "Sống giảm độc lực (áp dụng quy tắc cách 4 tuần với vắc xin sống tiêm khác)",
        "bat_hoat": "Bất hoạt",
        "giai_doc_to": "Giải độc tố",
        "tai_to_hop": "Tái tổ hợp",
        "cong_hop": "Cộng hợp",
        "khang_the_don_dong": "Kháng thể đơn dòng (không phải vắc xin)",
    }

    out = [
        f"=== VẮC XIN: {info.get('ten')} (mã: {vid}) ===",
        f"Tên thương mại : {', '.join(info.get('ten_thuong_mai', [])) or 'n/a'}",
        f"Loại           : {loai_map.get(info.get('loai_vaccine'), info.get('loai_vaccine'))}",
        f"Đường dùng     : {info.get('duong_dung', 'n/a')}",
        f"Phòng bệnh     : {', '.join(info.get('phong_benh', []))}",
        f"Chương trình   : {info.get('chuong_trinh', 'n/a')}",
    ]
    if info.get("ghi_chu"):
        out.append(f"Ghi chú        : {info['ghi_chu']}")

    if moc:
        out.append(f"\nCÁC MỐC TIÊM ({len(moc)} mũi):")
        for e in sorted(moc, key=lambda x: (x["tuoi_thang"], x["mui"])):
            dong = f"  - Mũi {e['mui']}: {e['tuoi_hien_thi']}"
            if e.get("khoang_cach_toi_thieu_tu_mui_truoc_tuan"):
                dong += f" (cách mũi trước tối thiểu {e['khoang_cach_toi_thieu_tu_mui_truoc_tuan']} tuần)"
            out.append(dong)
        out.append(f"Nguồn: {moc[0].get('nguon', 'n/a')}")
    else:
        out.append("\nKhông có mốc tiêm cố định theo tuổi trong bộ dữ liệu.")

    return "\n".join(out)


# =============================================================================
# 🧰 TOOL 4: TRA CHỐNG CHỈ ĐỊNH / TẠM HOÃN THEO TÌNH TRẠNG SỨC KHỎE
# =============================================================================

def check_contraindications(keywords: str) -> str:
    """
    Tra chống chỉ định, trường hợp tạm hoãn và khuyến cáo theo bệnh nền của trẻ.

    Args:
        keywords (str): Từ khoá tình trạng sức khoẻ.
                        VD 'tim bẩm sinh', 'sinh non', 'suy giảm miễn dịch', 'sốt', 'dị ứng'.

    Returns:
        str: Các cảnh báo tìm được + chuyên khoa cần khám,
             hoặc 'KHÔNG CÓ DỮ LIỆU: ...' nếu không khớp.

    LƯU Ý: Tool này CHỈ liệt kê cảnh báo. Không bao giờ kết luận trẻ tiêm được hay không.
    """
    q = _norm(keywords)
    if not q:
        return "LỖI: Cần truyền từ khoá tình trạng sức khoẻ, ví dụ check_contraindications[tim bẩm sinh]."

    hits = []

    # (1) Quét bảng bệnh nền
    for bn in CONDITIONS_DB.get("benh_nen", []):
        matched = any(_norm(tk) in q or q in _norm(tk) for tk in bn.get("tu_khoa", []))
        if not matched:
            continue
        block = [f"\n▸ BỆNH NỀN: {bn['ten']} (mã {bn['ma']}, mức rủi ro: {bn.get('muc_do_rui_ro', 'n/a')})"]
        if bn.get("ket_luan_chung"):
            block.append(f"  Tổng quan: {bn['ket_luan_chung']}")
        if bn.get("vaccine_chong_chi_dinh"):
            ten = [_vaccine_name(v) for v in bn["vaccine_chong_chi_dinh"]]
            block.append(f"  ⛔ CHỐNG CHỈ ĐỊNH: {', '.join(ten)}")
            if bn.get("ly_do_chong_chi_dinh"):
                block.append(f"     Lý do: {bn['ly_do_chong_chi_dinh']}")
        for qt in bn.get("quy_tac_dac_biet", []):
            block.append(f"  • Nếu {qt['dieu_kien']}: {qt['xu_ly']}")
            if qt.get("ngoai_le"):
                block.append(f"     Ngoại lệ: {qt['ngoai_le']}")
        if bn.get("dieu_kien_tam_hoan"):
            block.append(f"  ⏸️ TẠM HOÃN khi: {'; '.join(bn['dieu_kien_tam_hoan'])}")
        if bn.get("vaccine_khuyen_khich_them"):
            ten = [_vaccine_name(v) for v in bn["vaccine_khuyen_khich_them"]]
            block.append(f"  ➕ Khuyến khích tiêm thêm: {', '.join(ten)}")
        block.append(f"  🏥 CHUYÊN KHOA CẦN KHÁM: {bn.get('chuyen_khoa_can_kham', 'Nhi khoa')}")
        block.append(f"  Nguồn: {bn.get('nguon', 'n/a')}")
        hits.append("\n".join(block))

    # (2) Quét bảng chống chỉ định pháp quy
    ccd = CONTRA_DB.get("chong_chi_dinh", {})
    for nhom in ("tre_tren_1_thang_tuoi", "tre_so_sinh"):
        for item in ccd.get(nhom, []):
            if q in _norm(item["noi_dung"]) or any(q in _norm(d) for d in item.get("chi_tiet", [])):
                hits.append(
                    f"\n▸ CHỐNG CHỈ ĐỊNH ({item['ma']}): {item['noi_dung']}\n"
                    f"  Phạm vi: {item.get('pham_vi', 'n/a')} | Nguồn: {item.get('nguon', 'n/a')}"
                )

    # (3) Quét bảng tạm hoãn
    for item in CONTRA_DB.get("tam_hoan", {}).get("danh_muc", []):
        if q in _norm(item["noi_dung"]):
            hits.append(
                f"\n▸ TẠM HOÃN ({item['ma']}): {item['noi_dung']}\n"
                f"  Tiêm lại khi: {item.get('dieu_kien_tiem_lai', 'sức khoẻ ổn định')} "
                f"| Nguồn: {item.get('nguon', 'n/a')}"
            )

    if not hits:
        ten_benh = [bn["ten"] for bn in CONDITIONS_DB.get("benh_nen", [])]
        return (
            f"KHÔNG CÓ DỮ LIỆU: Không tìm thấy cảnh báo nào khớp với '{keywords}'. "
            f"Các nhóm bệnh nền có trong dữ liệu: {', '.join(ten_benh)}. "
            f"Không được suy đoán - hãy khuyên phụ huynh đưa bé đi khám sàng lọc."
        )

    return (
        f"=== CẢNH BÁO TIÊM CHỦNG CHO TÌNH TRẠNG: '{keywords}' ===" + "".join(hits) +
        "\n\n⚠️ BẮT BUỘC: Chỉ bác sĩ khám sàng lọc mới được kết luận trẻ có tiêm được hay không "
        "(Quyết định 1575/QĐ-BYT). Tool này chỉ liệt kê cảnh báo."
    )


# =============================================================================
# 🧰 TOOL 5: KIỂM TRA XUNG ĐỘT GIỮA HAI VẮC XIN
# =============================================================================

def check_vaccine_conflict(vaccine_a: str, vaccine_b: str = None) -> str:
    """
    Kiểm tra hai vắc xin có xung đột không và cần cách nhau tối thiểu bao lâu.

    Args:
        vaccine_a (str): Vắc xin thứ nhất (mã, tên, hoặc tên bệnh).
        vaccine_b (str): Vắc xin thứ hai.

    Returns:
        str: Kết luận xung đột + khoảng cách tối thiểu + căn cứ,
             hoặc 'LỖI: ...' nếu thiếu tham số / không nhận diện được vắc xin.

    Ví dụ:
        check_vaccine_conflict('MMR', 'Thuy_dau')
    """
    if not vaccine_b:
        return (
            "LỖI: Tool này cần ĐÚNG 2 tham số. "
            "Cú pháp: check_vaccine_conflict[vaccine_a, vaccine_b]"
        )

    va, vb = _resolve_vaccine_id(vaccine_a), _resolve_vaccine_id(vaccine_b)
    khong_ro = [raw for raw, rid in ((vaccine_a, va), (vaccine_b, vb)) if rid is None]
    if khong_ro:
        return (
            f"KHÔNG CÓ DỮ LIỆU: Không nhận diện được vắc xin {khong_ro}. "
            f"Các mã hợp lệ: {', '.join(sorted(VACCINE_CATALOG.keys()))}"
        )

    if va == vb:
        return (
            f"Hai tham số cùng trỏ tới một vắc xin ({_vaccine_name(va)}). "
            f"Quy tắc KC_01: hai liều của CÙNG một loại vắc xin cách nhau tối thiểu 4 tuần, "
            f"trừ khi phác đồ nhà sản xuất quy định khác."
        )

    kc = CONTRA_DB.get("quy_tac_khoang_cach", {})

    # (1) Tra bảng cặp xung đột đã liệt kê sẵn (ưu tiên cao nhất)
    for cap in kc.get("cap_vaccine_khong_nen_tiem_cung", []):
        if {cap["vaccine_a"], cap["vaccine_b"]} == {va, vb}:
            icon = "⛔ CHẶN" if cap["muc_do"] == "chan" else "⚠️ CẢNH BÁO"
            return (
                f"=== XUNG ĐỘT: {_vaccine_name(va)} ⟷ {_vaccine_name(vb)} ===\n"
                f"{icon} | Loại xung đột: {cap['loai_xung_dot']}\n"
                f"Xử lý: {cap['xu_ly']}\n"
                f"Nguồn: Quyết định 1575/QĐ-BYT và hướng dẫn nhà sản xuất."
            )

    # (2) Suy ra từ loại vắc xin theo quy tắc KC_02 / KC_03 / KC_04
    la = VACCINE_CATALOG[va].get("loai_vaccine")
    lb = VACCINE_CATALOG[vb].get("loai_vaccine")
    da = VACCINE_CATALOG[va].get("duong_dung", "")
    db = VACCINE_CATALOG[vb].get("duong_dung", "")

    song_tiem_a = la == "song_giam_doc_luc" and da.startswith("tiem")
    song_tiem_b = lb == "song_giam_doc_luc" and db.startswith("tiem")

    if song_tiem_a and song_tiem_b:
        return (
            f"=== XUNG ĐỘT: {_vaccine_name(va)} ⟷ {_vaccine_name(vb)} ===\n"
            f"⚠️ CẢNH BÁO | Cả hai đều là vắc xin SỐNG GIẢM ĐỘC LỰC dạng TIÊM.\n"
            f"Quy tắc KC_02: tiêm CÙNG một buổi ở HAI VỊ TRÍ KHÁC NHAU, "
            f"HOẶC cách nhau TỐI THIỂU 4 TUẦN. Không được tiêm cách nhau 1-3 tuần.\n"
            f"Nguồn: hướng dẫn khoảng cách tiêm chủng (xem data/data_sources.md)."
        )

    quy_tac = "KC_03 (hai vắc xin bất hoạt)" if "song_giam_doc_luc" not in (la, lb) \
        else "KC_04 (một sống + một bất hoạt)"
    return (
        f"=== KIỂM TRA: {_vaccine_name(va)} ⟷ {_vaccine_name(vb)} ===\n"
        f"✅ KHÔNG XUNG ĐỘT | Quy tắc {quy_tac}: không cần khoảng cách tối thiểu, "
        f"có thể tiêm cùng buổi ở hai vị trí khác nhau.\n"
        f"Loại: {_vaccine_name(va)} = {la} | {_vaccine_name(vb)} = {lb}\n"
        f"Vẫn cần bác sĩ khám sàng lọc quyết định cuối cùng."
    )


# =============================================================================
# 🧰 TOOL 6: TÌM CHI NHÁNH LONG CHÂU GẦN NHẤT
# =============================================================================

def find_nearest_pharmacy(address: str) -> str:
    """
    Tìm các chi nhánh Trung tâm Tiêm chủng Long Châu theo địa chỉ / quận / thành phố.

    Args:
        address (str): Địa chỉ hoặc tên quận/thành phố. VD 'Cầu Giấy, Hà Nội'.

    Returns:
        str: Tối đa 3 chi nhánh khớp nhất kèm store_id, giờ mở cửa,
             hoặc 'KHÔNG CÓ DỮ LIỆU: ...'.

    LƯU Ý: Dữ liệu chi nhánh là MOCK phục vụ bài Lab (xem data/pharmacies.json).
    """
    q = _norm(address)
    if not q:
        return "LỖI: Cần truyền địa chỉ, ví dụ find_nearest_pharmacy[Cầu Giấy, Hà Nội]."

    stores = PHARMACY_DB.get("chi_nhanh", [])
    if not stores:
        return "LỖI: Chưa nạp được dữ liệu chi nhánh từ data/pharmacies.json."

    tokens = [t for t in q.replace(",", " ").split() if len(t) > 1]

    def score(s):
        hay = _norm(f"{s['ten']} {s['dia_chi']} {s['quan']} {s['thanh_pho']}")
        pts = sum(1 for t in tokens if t in hay)
        if _norm(s["quan"]) in q:
            pts += 5   # khớp đúng quận thì ưu tiên mạnh
        if _norm(s["thanh_pho"]) in q:
            pts += 2
        return pts

    ranked = sorted(stores, key=score, reverse=True)
    matched = [s for s in ranked if score(s) > 0][:3]

    if not matched:
        tp = sorted({s["thanh_pho"] for s in stores})
        return (
            f"KHÔNG CÓ DỮ LIỆU: Không tìm thấy chi nhánh Long Châu nào khớp với '{address}'. "
            f"Dữ liệu hiện chỉ có tại: {', '.join(tp)}. Không được bịa địa chỉ."
        )

    out = [f"=== {len(matched)} CHI NHÁNH LONG CHÂU GẦN '{address}' ==="]
    for i, s in enumerate(matched, 1):
        out.append(
            f"\n{i}. {s['ten']}\n"
            f"   store_id  : {s['store_id']}\n"
            f"   Địa chỉ   : {s['dia_chi']}\n"
            f"   Giờ mở cửa: {s['gio_mo_cua']} | Hotline: {s['hotline']}"
        )
    out.append(
        "\n⚠️ Dữ liệu chi nhánh là MOCK phục vụ bài Lab. "
        "Vắc xin thuộc Chương trình TCMR được tiêm MIỄN PHÍ tại trạm y tế phường/xã."
    )
    return "\n".join(out)


# =============================================================================
# 🧰 TOOL 7: KIỂM TRA TỒN KHO VẮC XIN TẠI CHI NHÁNH
# =============================================================================

def check_stock(store_id: str, vaccine_id: str = None) -> str:
    """
    Kiểm tra tồn kho một vắc xin tại một chi nhánh Long Châu.

    Args:
        store_id (str): Mã chi nhánh, VD 'LC_HN_012' (lấy từ find_nearest_pharmacy).
        vaccine_id (str): Mã hoặc tên vắc xin cần kiểm tra.

    Returns:
        str: Tình trạng còn/hết hàng, số lượng, giá tham khảo,
             hoặc 'LỖI: ...' / 'KHÔNG CÓ DỮ LIỆU: ...'.

    LƯU Ý: Tồn kho là DỮ LIỆU MOCK. Long Châu không công khai tồn kho qua API.
    """
    if not vaccine_id:
        return "LỖI: Tool này cần ĐÚNG 2 tham số. Cú pháp: check_stock[store_id, vaccine_id]"

    sid = str(store_id).strip().strip("'\"").upper()
    store = next((s for s in PHARMACY_DB.get("chi_nhanh", []) if s["store_id"].upper() == sid), None)
    if store is None:
        hop_le = [s["store_id"] for s in PHARMACY_DB.get("chi_nhanh", [])]
        return (
            f"LỖI: Không tồn tại chi nhánh '{store_id}'. "
            f"Hãy gọi find_nearest_pharmacy trước để lấy store_id. Mã hợp lệ: {', '.join(hop_le)}"
        )

    kho = PHARMACY_DB.get("ton_kho", {}).get(store["store_id"], {})

    # Cho phép lấy TOÀN BỘ kho trong 1 lần gọi, tránh Agent phải hỏi từng vắc xin
    # một và đốt hết ngân sách vòng lặp.
    if _norm(vaccine_id) in ("all", "tat ca", "toan bo", "*"):
        if not kho:
            return f"KHÔNG CÓ DỮ LIỆU: {store['ten']} chưa có dữ liệu tồn kho."
        con = [f"{_vaccine_name(v)} [{v}]: còn {d['so_luong']} liều, {d['gia_vnd']:,} VNĐ"
               for v, d in sorted(kho.items()) if d["con_hang"]]
        het = [f"{_vaccine_name(v)} [{v}]" for v, d in sorted(kho.items()) if not d["con_hang"]]
        return (
            f"=== TOÀN BỘ TỒN KHO tại {store['ten']} ===\n"
            f"Địa chỉ: {store['dia_chi']} | Giờ mở cửa: {store['gio_mo_cua']}\n\n"
            f"✅ CÒN HÀNG ({len(con)}):\n  - " + "\n  - ".join(con) +
            (f"\n\n❌ HẾT HÀNG ({len(het)}): {', '.join(het)}" if het else "") +
            "\n\nLưu ý: vắc xin thuộc Chương trình TCMR được tiêm MIỄN PHÍ tại trạm y tế "
            "phường/xã nên không có trong bảng này.\n"
            "⚠️ Tồn kho và giá là DỮ LIỆU MOCK phục vụ bài Lab."
        )

    vid = _resolve_vaccine_id(vaccine_id)
    if vid is None:
        return (
            f"KHÔNG CÓ DỮ LIỆU: Không nhận diện được vắc xin '{vaccine_id}'. "
            f"Các mã hợp lệ: {', '.join(sorted(VACCINE_CATALOG.keys()))}"
        )

    item = kho.get(vid)

    if item is None:
        chuong_trinh = VACCINE_CATALOG[vid].get("chuong_trinh", "")
        if chuong_trinh == "TCMR":
            return (
                f"KHÔNG CÓ DỮ LIỆU: {_vaccine_name(vid)} thuộc Chương trình Tiêm chủng mở rộng, "
                f"được tiêm MIỄN PHÍ tại trạm y tế phường/xã nên không bán tại {store['ten']}. "
                f"Phụ huynh liên hệ trạm y tế nơi cư trú."
            )
        return (
            f"KHÔNG CÓ DỮ LIỆU: {store['ten']} không kinh doanh {_vaccine_name(vid)}. "
            f"Các vắc xin có tại đây: {', '.join(sorted(kho.keys()))}"
        )

    trang_thai = "✅ CÒN HÀNG" if item["con_hang"] else "❌ HẾT HÀNG"
    out = (
        f"=== TỒN KHO: {_vaccine_name(vid)} tại {store['ten']} ===\n"
        f"Trạng thái: {trang_thai} (còn {item['so_luong']} liều)\n"
        f"Giá tham khảo: {item['gia_vnd']:,} VNĐ/liều\n"
        f"Địa chỉ: {store['dia_chi']} | Giờ mở cửa: {store['gio_mo_cua']}"
    )
    if not item["con_hang"]:
        out += "\n➡️ Gợi ý: gọi find_nearest_pharmacy để tìm chi nhánh khác còn hàng."
    out += "\n⚠️ Tồn kho và giá là DỮ LIỆU MOCK phục vụ bài Lab, cần gọi hotline 1800 6928 để xác nhận."
    return out


# =============================================================================
# 🧰 TOOL 8: ĐẶT LỊCH TIÊM (WRITE - CÓ TÁC DỤNG PHỤ)
# =============================================================================

def book_appointment(store_id: str, vaccine_id: str = None, datetime_str: str = None) -> str:
    """
    Đặt lịch hẹn tiêm chủng tại một chi nhánh. ĐÂY LÀ TOOL GHI DỮ LIỆU (side effect).

    Args:
        store_id (str): Mã chi nhánh, VD 'LC_HN_012'.
        vaccine_id (str): Mã hoặc tên vắc xin cần tiêm.
        datetime_str (str): Thời gian hẹn, VD '2026-08-05 09:00'.

    Returns:
        str: Mã đặt lịch nếu thành công, hoặc 'LỖI: ...' nếu tham số sai / hết hàng.

    LƯU Ý: Ghi vào data/appointments.json. Chỉ gọi khi người dùng ĐÃ nêu rõ ý định đặt lịch.
    """
    if not vaccine_id or not datetime_str:
        return (
            "LỖI: Tool này cần ĐÚNG 3 tham số. "
            "Cú pháp: book_appointment[store_id, vaccine_id, YYYY-MM-DD HH:MM]"
        )

    sid = str(store_id).strip().strip("'\"").upper()
    store = next((s for s in PHARMACY_DB.get("chi_nhanh", []) if s["store_id"].upper() == sid), None)
    if store is None:
        return f"LỖI: Không tồn tại chi nhánh '{store_id}'. Gọi find_nearest_pharmacy trước để lấy store_id."

    vid = _resolve_vaccine_id(vaccine_id)
    if vid is None:
        return f"KHÔNG CÓ DỮ LIỆU: Không nhận diện được vắc xin '{vaccine_id}'."

    hen = None
    for fmt in ("%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            hen = datetime.strptime(str(datetime_str).strip().strip("'\""), fmt)
            break
        except ValueError:
            continue
    if hen is None:
        return (
            f"LỖI: Không đọc được thời gian '{datetime_str}'. "
            f"Định dạng hợp lệ: 'YYYY-MM-DD HH:MM' (VD 2026-08-05 09:00)."
        )
    if hen < datetime.now():
        return f"LỖI: Thời gian hẹn '{datetime_str}' nằm ở quá khứ. Hãy chọn thời điểm trong tương lai."

    item = PHARMACY_DB.get("ton_kho", {}).get(store["store_id"], {}).get(vid)
    if item is None:
        return (
            f"LỖI: {store['ten']} không kinh doanh {_vaccine_name(vid)}. "
            f"Không thể đặt lịch. Hãy gọi check_stock để kiểm tra trước."
        )
    if not item["con_hang"]:
        return (
            f"LỖI: {_vaccine_name(vid)} đang HẾT HÀNG tại {store['ten']}. "
            f"Không đặt được lịch. Hãy tìm chi nhánh khác bằng find_nearest_pharmacy."
        )

    ma_dat = f"LC{hen.strftime('%y%m%d')}-{store['store_id'][-3:]}-{abs(hash(vid + datetime_str)) % 10000:04d}"
    ban_ghi = {
        "ma_dat_lich": ma_dat,
        "store_id": store["store_id"],
        "ten_chi_nhanh": store["ten"],
        "dia_chi": store["dia_chi"],
        "vaccine_id": vid,
        "ten_vaccine": _vaccine_name(vid),
        "thoi_gian_hen": hen.strftime("%Y-%m-%d %H:%M"),
        "gia_vnd": item["gia_vnd"],
        "tao_luc": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trang_thai": "da_dat",
    }

    try:
        ds = []
        if os.path.exists(APPOINTMENTS_PATH):
            with open(APPOINTMENTS_PATH, "r", encoding="utf-8") as f:
                ds = json.load(f)
        ds.append(ban_ghi)
        with open(APPOINTMENTS_PATH, "w", encoding="utf-8") as f:
            json.dump(ds, f, ensure_ascii=False, indent=2)
    except OSError as e:
        return f"LỖI: Không ghi được lịch hẹn vào file ({e}). Vui lòng gọi hotline 1800 6928 để đặt trực tiếp."

    return (
        f"=== ĐẶT LỊCH THÀNH CÔNG ===\n"
        f"Mã đặt lịch : {ma_dat}\n"
        f"Vắc xin     : {_vaccine_name(vid)}\n"
        f"Cơ sở       : {store['ten']}\n"
        f"Địa chỉ     : {store['dia_chi']}\n"
        f"Thời gian   : {hen.strftime('%H:%M ngày %d/%m/%Y')}\n"
        f"Giá tham khảo: {item['gia_vnd']:,} VNĐ\n"
        f"⚠️ Phụ huynh mang theo sổ tiêm chủng của bé và đến sớm 15 phút để khám sàng lọc trước tiêm."
    )


# =============================================================================
# 📋 ĐĂNG KÝ TOOL CHO AGENT
# Tên key PHẢI khớp EXPECTED_TOOLS trong src/prompts.py (Role 3).
# =============================================================================

AVAILABLE_TOOLS = {
    "calculate_age_months": calculate_age_months,
    "lookup_vaccine_schedule": lookup_vaccine_schedule,
    "get_vaccine_info": get_vaccine_info,
    "check_contraindications": check_contraindications,
    "check_vaccine_conflict": check_vaccine_conflict,
    "find_nearest_pharmacy": find_nearest_pharmacy,
    "check_stock": check_stock,
    "book_appointment": book_appointment,
}

# Số tham số mà mỗi tool yêu cầu - Role 4 dùng để validate trước khi gọi.
TOOL_ARITY = {
    "calculate_age_months": 1,
    "lookup_vaccine_schedule": 1,
    "get_vaccine_info": 1,
    "check_contraindications": 1,
    "check_vaccine_conflict": 2,
    "find_nearest_pharmacy": 1,
    "check_stock": 2,
    "book_appointment": 3,
}


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=== KIỂM THỬ ĐỘC LẬP CÁC TOOL (ROLE 2) ===")
    print(f"Đã nạp: {len(VACCINE_CATALOG)} vắc xin | {len(SCHEDULE_ENTRIES)} mốc tiêm | "
          f"{len(PHARMACY_DB.get('chi_nhanh', []))} chi nhánh\n")

    cases = [
        ("calculate_age_months", ("01/05/2023",)),
        ("lookup_vaccine_schedule", (2,)),
        ("lookup_vaccine_schedule", (500,)),          # bẫy: ngoài phạm vi
        ("get_vaccine_info", ("thủy đậu",)),
        ("check_contraindications", ("tim bẩm sinh",)),
        ("check_vaccine_conflict", ("MMR", "Thuy_dau")),
        ("find_nearest_pharmacy", ("Cầu Giấy, Hà Nội",)),
        ("check_stock", ("LC_HN_012", "Thuy_dau")),   # bẫy: hết hàng
        ("check_stock", ("LC_XXX_999", "MMR")),       # bẫy: sai store_id
    ]
    for name, args in cases:
        print(f"\n{'=' * 70}\n▶ {name}{args}\n{'-' * 70}")
        print(AVAILABLE_TOOLS[name](*args))
