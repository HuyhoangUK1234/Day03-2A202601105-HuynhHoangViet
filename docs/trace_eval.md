# 📊 BÁO CÁO GIÁM SÁT & ĐÁNH GIÁ (OBSERVABILITY TRACE LOGS)

*Dành cho Role 5: Observability & Reviewer*

## 🎯 1. BẢNG CHẤM ĐIỂM AGENTIC FIT (SCORING MATRIX)

| Tiêu chí                       |  Điểm (1-5)  | Lý do đánh giá                                                                                                                                                                                                    |
| :------------------------------- | :-------------: | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🧠**Multi-step Reasoning** |     `4/5`     | Cần suy luận nhiều bước: xác định tuổi/ngày sinh trẻ → tra mũi tiêm nào đang đến hạn theo phác đồ → kiểm tra lịch sử đã tiêm → mới đề xuất đặt lịch.                             |
| 🛠️**Tool Interaction**   |     `5/5`     | Không thể trả lời chỉ bằng kiến thức LLM — bắt buộc tra cứu dữ liệu thực: phác đồ tiêm chủng theo tuổi, lịch sử tiêm của trẻ, lịch hẹn còn trống tại cơ sở y tế.                    |
| 🔀**Dynamic Decision**     |     `4/5`     | Kết quả bước trước quyết định hành động bước sau — ví dụ: nếu trẻ đã tiêm đủ mũi 1 thì mới kiểm tra lịch mũi 2; nếu không còn slot ngày mong muốn thì phải tìm ngày thay thế. |
| ⏳**Long Horizon**         |     `4/5`     | Quy trình có thể dài hơn 2–3 bước: kiểm tra hồ sơ tiêm → xác định mũi cần tiêm → kiểm tra lịch trống → xác nhận đặt/đổi lịch → (có thể) gửi nhắc lịch.                           |
| **TỔNG ĐIỂM FIT**       | **17/20** | **KẾT LUẬN: BÀI TOÁN RẤT NÊN DÙNG REACT AGENT!**                                                                                                                                                         |

## 🔍 2. SO SÁNH PHẢN HỒI (TEST CASE #3)

**Câu hỏi**: *"Con tôi 3 tuổi còn thiếu những mũi tiêm nào, và đâu là trung tâm tiêm chủng ở Cầu Giấy còn vắc xin đó?"*

### 🤖 Chatbot Baseline:

* **Phản hồi**:  "Xin chào! Đối với trẻ 3 tuổi, thường sẽ cần một số mũi tiêm nhắc lại để bảo vệ sức khỏe. Tuy nhiên, tôi không có thông tin cụ thể về lịch tiêm chủng hiện hành hoặc tình trạng vắc xin tại các trung tâm tiêm chủng. Để biết chính xác con bạn còn thiếu mũi tiêm nào, bạn nên tham khảo ý kiến bác sĩ hoặc đến cơ sở y tế để được tư vấn. Ngoài ra, hãy đưa trẻ đi khám sàng lọc trước tiêm chủng để đảm bảo sức khỏe của bé. Chúc bạn và bé luôn khỏe mạnh!".
* **Nhận xét**: An toàn nhưng không giải quyết được nhu cầu thực tế của người dùng.

### 🧠 ReAct Agent:

* **Thought 1** : Để biết con 3 tuổi còn thiếu những mũi tiêm nào, tôi cần chuyển đổi tuổi thành tháng và tra cứu lịch tiêm chủng.
* **Action 1** : `lookup_vaccine_schedule[36]`
* **Observation 1** : `Không có mũi nào đến hạn đúng tại mốc 36 tháng tuổi. Có 33 mũi lẽ ra đã phải tiêm trước 36 tháng - cần đối chiếu sổ tiêm chủng của bé.`
* **Thought 2** : Tôi cần tìm địa chỉ của các trung tâm tiêm chủng Long Châu gần Cầu Giấy để kiểm tra tồn kho các vắc xin dịch vụ cho trẻ.
* **Action 2** : `find_nearest_pharmacy['Cầu Giấy, Hà Nội']`
* **Observation 2** : `3 chi nhánh Long Châu gần Cầu Giấy: Long Châu - Cầu Giấy (227 Cầu Giấy), Long Châu - Xuân Thủy (89 Xuân Thủy)...`
* **Thought 3** : Tôi cần kiểm tra tồn kho các vắc xin dịch vụ tại Trung tâm Tiêm chủng Long Châu - Cầu Giấy.
* **Action 3** : `check_stock[LC_HN_012, all]`
* **Observation 3** : `Còn hàng (10 loại): 6 trong 1, Cúm mùa, MMR, não mô cầu ACYW/BC, PCV, Rota, VGA, VNNB, VNNB sống...`
* **Final Answer** : *"Con bạn 3 tuổi có thể đã thiếu nhiều mũi tiêm, bao gồm BCG, Rota, bạch hầu-ho gà-uốn ván (mũi nhắc), bại liệt (bất hoạt & uống), 5 trong 1, sởi-rubella... Trung tâm Long Châu - Cầu Giấy (227 Cầu Giấy, Dịch Vọng) hiện còn 10 loại vắc xin dịch vụ: 6 trong 1, Cúm, MMR, não mô cầu ACYW/BC, PCV, Rota, VGA, VNNB, VNNB sống. Căn cứ: Thông tư 52/2025/TT-BYT."*
* **Nhận xét** : Hoàn thành xuất sắc nhiệm vụ nhờ xâu chuỗi 3 tool liên tiếp (tra lịch tiêm → tìm địa điểm → kiểm tra tồn kho), mỗi bước đều có Observation làm bằng chứng, và trích dẫn nguồn pháp lý rõ ràng — thể hiện đúng giá trị cốt lõi của ReAct Agent so với Chatbot chỉ biết từ chối.
