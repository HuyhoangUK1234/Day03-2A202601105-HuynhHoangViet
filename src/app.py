"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer)
File chính ghép nối tất cả các thành phần: Tools + Prompts + Test Cases + Logger + Provider.

Chạy:
    python src/app.py              # chạy toàn bộ test cases (Chatbot vs Agent)
    python src/app.py --chat       # chế độ hội thoại tương tác
    python src/app.py --case 3     # chạy đúng 1 test case
    python src/app.py --agent-only # bỏ qua chatbot baseline cho nhanh
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv

# Đảm bảo import các module cùng thư mục src/ hoạt động mượt mà
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from tools import AVAILABLE_TOOLS, TOOL_ARITY
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_SYSTEM_PROMPT,
    REQUIRED_DISCLAIMER,
    SAFE_FALLBACK_MESSAGE,
    ACTION_REGEX,
    FINAL_ANSWER_REGEX,
    THOUGHT_REGEX,
    EXPECTED_TOOLS,
    WRITE_TOOLS,
    ERROR_TEMPLATES,
    MAX_ITERATIONS,
    MAX_REPEATED_ACTIONS,
    MAX_OBSERVATION_CHARS,
    detect_blocked_intent,
)
from providers import get_llm_provider
from logger import TraceLogger

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_test_cases():
    """Đọc bộ test cases từ config/test_cases.json của Role 1"""
    config_path = os.path.join(BASE_DIR, "config", "test_cases.json")
    if not os.path.exists(config_path):
        config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_integration():
    """
    Kiểm tra hợp đồng giữa Role 2 (tools.py) và Role 3 (prompts.py).
    Bắt lệch tên tool ngay lúc khởi động thay vì để Agent gọi hụt giữa chừng.
    """
    declared = set(EXPECTED_TOOLS)
    implemented = set(AVAILABLE_TOOLS)
    thieu = declared - implemented
    thua = implemented - declared
    if thieu:
        print(f"⚠️ LỆCH HỢP ĐỒNG: prompts.py khai báo nhưng tools.py chưa có: {sorted(thieu)}")
    if thua:
        print(f"⚠️ LỆCH HỢP ĐỒNG: tools.py có nhưng prompts.py chưa khai báo: {sorted(thua)}")
    if not thieu and not thua:
        print(f"✅ Hợp đồng Role 2 ⟷ Role 3 khớp: {len(declared)} tool.")
    return not (thieu or thua)


# =============================================================================
# 🔍 PARSER (Hợp đồng định dạng do Role 3 định nghĩa trong prompts.py)
# =============================================================================

def strip_hallucinated_observation(text: str) -> str:
    """
    Cắt output của LLM ngay trước dòng Observation đầu tiên.
    Nguyên tắc bất biến #2: Observation do ỨNG DỤNG chèn, LLM không được tự bịa.
    """
    for marker in ("\nObservation:", "\nObservation :", "Observation:"):
        idx = text.find(marker)
        if idx > 0:
            return text[:idx].rstrip()
    return text


def parse_llm_output(text: str):
    """
    Đọc output của LLM, trả về ('action', tool, args) hoặc ('final', answer) hoặc ('none', lý_do).
    Nếu có cả Action lẫn Final Answer, lấy cái xuất hiện TRƯỚC.
    """
    m_action = ACTION_REGEX.search(text)
    m_final = FINAL_ANSWER_REGEX.search(text)

    if m_action and m_final:
        if m_action.start() < m_final.start():
            return "action", m_action.group(1).strip(), m_action.group(2).strip()
        return "final", m_final.group(1).strip(), None
    if m_action:
        return "action", m_action.group(1).strip(), m_action.group(2).strip()
    if m_final:
        return "final", m_final.group(1).strip(), None
    return "none", None, None


def split_tool_args(tool_name: str, raw_args: str):
    """
    Tách tham số theo số lượng mà tool yêu cầu.

    Quan trọng: tool 1 tham số KHÔNG được tách theo dấu phẩy, vì địa chỉ
    'Cầu Giấy, Hà Nội' bản thân đã chứa dấu phẩy.
    """
    arity = TOOL_ARITY.get(tool_name, 1)
    if arity == 1:
        return [raw_args.strip().strip("'\"")]
    parts = [p.strip().strip("'\"") for p in raw_args.split(",", arity - 1)]
    return parts


# =============================================================================
# 💬 CẤP 2 — CHATBOT BASELINE (không tool)
# =============================================================================

def run_baseline_chatbot(user_query: str, provider, logger: TraceLogger,
                         case_id=None, category=None) -> str:
    """Dựng Chatbot gốc (Baseline) không có công cụ - đúng 1 lần gọi LLM."""
    run = logger.start_run(user_query, mode="chatbot", case_id=case_id, category=category)
    print(f"\n💬 [CHATBOT BASELINE] {user_query}")

    try:
        response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    except Exception as e:
        response = f"[Provider Exception]: {e}"

    print(f"🤖 Chatbot: {response}")
    run.final(response, termination="final")
    run.close()
    return response


# =============================================================================
# 🧠 CẤP 3 — REACT AGENT LOOP (Thought -> Action -> Observation)
# =============================================================================

def run_react_agent(user_query: str, provider, logger: TraceLogger,
                    case_id=None, category=None, verbose=True) -> str:
    """
    Vòng lặp ReAct thật: gọi LLM -> parse Action -> thực thi tool ->
    chèn Observation thật -> quay lại LLM, có đầy đủ Guardrails.
    """
    run = logger.start_run(user_query, mode="react", case_id=case_id, category=category)
    if verbose:
        print(f"\n🤖 [REACT AGENT] {user_query}")

    # --- GUARDRAIL ĐẦU VÀO: chặn ý định nguy hiểm trước khi tốn 1 lần gọi LLM ---
    blocked = detect_blocked_intent(user_query)
    if blocked:
        intent, message = blocked
        if verbose:
            print(f"🛡️ GUARDRAIL ĐẦU VÀO [{intent}] - chặn trước khi vào vòng lặp")
            print(f"🏁 {message}")
        run.guardrail(f"blocked_intent:{intent}", "Chặn tại tầng input, không gọi LLM")
        run.final(message, termination="blocked")
        run.close()
        return message

    transcript = f"Question: {user_query}\n"
    action_history = []
    final_answer = None

    for step in range(1, MAX_ITERATIONS + 1):
        if verbose:
            print(f"\n--- 🔄 Vòng lặp ReAct (Step {step}/{MAX_ITERATIONS}) ---")

        # (1) Gọi LLM
        try:
            raw = provider.generate(transcript, system_prompt=REACT_SYSTEM_PROMPT)
        except Exception as e:
            obs = f"LỖI: Provider lỗi ({e})."
            run.observation(obs)
            transcript += f"Observation: {obs}\n"
            continue

        raw = strip_hallucinated_observation(raw or "")

        m_thought = THOUGHT_REGEX.search(raw)
        thought = m_thought.group(1).strip() if m_thought else "(không có Thought)"
        run.thought(thought)
        if verbose:
            print(f"🧠 Thought: {thought}")

        # (2) Parse
        kind, a, b = parse_llm_output(raw)

        if kind == "none":
            reason = ERROR_TEMPLATES["malformed_action"]
            run.parse_error("Không tìm thấy Action hoặc Final Answer", raw)
            if verbose:
                print(f"⚠️ {reason}")
            transcript += f"{raw}\nObservation: {reason}\n"
            continue

        if kind == "final":
            final_answer = a
            if verbose:
                print(f"🏁 Final Answer: {final_answer}")
            run.final(final_answer, termination="final")
            break

        # (3) kind == "action"
        tool_name, raw_args = a, b
        if verbose:
            print(f"🛠️ Action: {tool_name}[{raw_args}]")

        # GUARDRAIL: tool không tồn tại
        if tool_name not in AVAILABLE_TOOLS:
            obs = ERROR_TEMPLATES["unknown_tool"].format(
                tool_name=tool_name, valid_tools=", ".join(sorted(AVAILABLE_TOOLS)))
            run.action(tool_name, raw_args)
            run.observation(obs)
            run.guardrail("unknown_tool", tool_name)
            if verbose:
                print(f"❌ Observation: {obs}")
            transcript += f"{raw}\nObservation: {obs}\n"
            continue

        # GUARDRAIL: lặp lại y hệt Action đã thất bại
        signature = f"{tool_name}[{raw_args}]"
        action_history.append(signature)
        repeats = action_history.count(signature)
        if repeats > MAX_REPEATED_ACTIONS:
            obs = ERROR_TEMPLATES["repeated_action"].format(action=signature, count=repeats)
            run.observation(obs)
            run.guardrail("repeated_action", f"{signature} lặp {repeats} lần")
            if verbose:
                print(f"🛡️ {obs}")
            transcript += f"{raw}\nObservation: {obs}\n"
            continue

        # GUARDRAIL: tool ghi dữ liệu cần người dùng nêu rõ ý định
        if tool_name in WRITE_TOOLS:
            y_dinh = any(k in user_query.lower() for k in
                         ["đặt lịch", "dat lich", "đặt hẹn", "book", "đăng ký tiêm", "hẹn lịch"])
            if not y_dinh:
                obs = (f"LỖI: '{tool_name}' là hành động ghi dữ liệu thật (đặt lịch hẹn). "
                       f"Người dùng chưa nêu rõ ý định đặt lịch nên không được tự ý gọi. "
                       f"Hãy dùng Final Answer để hỏi người dùng có muốn đặt lịch không.")
                run.action(tool_name, raw_args)
                run.observation(obs)
                run.guardrail("unauthorized_write", tool_name)
                if verbose:
                    print(f"🛡️ {obs}")
                transcript += f"{raw}\nObservation: {obs}\n"
                continue

        # (4) Thực thi tool
        run.action(tool_name, raw_args)
        args = split_tool_args(tool_name, raw_args)
        expected = TOOL_ARITY.get(tool_name, 1)

        if len(args) != expected:
            obs = ERROR_TEMPLATES["wrong_arg_count"].format(
                tool_name=tool_name, expected=expected, actual=len(args))
        else:
            try:
                obs = AVAILABLE_TOOLS[tool_name](*args)
            except Exception as e:
                # Tool không được phép crash, nhưng vẫn bọc để agent không chết
                obs = f"LỖI: Công cụ '{tool_name}' gặp sự cố ({type(e).__name__}: {e})."

        if len(obs) > MAX_OBSERVATION_CHARS:
            obs = obs[:MAX_OBSERVATION_CHARS] + "\n...[đã cắt bớt để tiết kiệm ngữ cảnh]"

        run.observation(obs)
        if verbose:
            preview = obs if len(obs) < 400 else obs[:400] + " ...[rút gọn khi in]"
            print(f"👁️ Observation: {preview}")

        transcript += f"{raw}\nObservation: {obs}\n"

    # --- GUARDRAIL CUỐI: chạm trần vòng lặp ---
    if final_answer is None:
        final_answer = SAFE_FALLBACK_MESSAGE.format(max_steps=MAX_ITERATIONS)
        if verbose:
            print(f"\n🛡️ GUARDRAIL TRIGGERED: Đã đạt giới hạn {MAX_ITERATIONS} bước. Ngắt lặp an toàn!")
            print(f"🏁 {final_answer}")
        run.guardrail("max_iterations", f"Chạm trần {MAX_ITERATIONS} bước")
        run.final(final_answer, termination="max_iterations")

    run.close()
    return final_answer


# =============================================================================
# 🖥️ CHẾ ĐỘ HỘI THOẠI TƯƠNG TÁC
# =============================================================================

def interactive_chat(provider, logger: TraceLogger):
    """Chế độ hỏi đáp liên tục trên terminal."""
    print("\n" + "=" * 60)
    print("💬 CHẾ ĐỘ HỘI THOẠI - gõ 'exit' để thoát, 'report' để xem bảng chấm điểm")
    print("=" * 60)
    while True:
        try:
            q = input("\n👤 Bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q.lower() in ("exit", "quit", "thoat", "thoát"):
            break
        if q.lower() == "report":
            print("\n" + logger.build_scorecard())
            continue
        answer = run_react_agent(q, provider, logger)
        print(f"\n🤖 Trợ lý: {answer}")


# =============================================================================
# 🚀 ĐIỂM VÀO
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Lab 3 - Chatbot vs ReAct Agent (Tiêm chủng)")
    parser.add_argument("--chat", action="store_true", help="Chế độ hội thoại tương tác")
    parser.add_argument("--case", type=int, help="Chỉ chạy 1 test case theo id")
    parser.add_argument("--agent-only", action="store_true", help="Bỏ qua Chatbot baseline")
    args = parser.parse_args()

    print("=" * 60)
    print("🏫 ĐẠI HỌC VINUNI - BÀI LAB 3: CHATBOT VS REACT AGENT")
    print("   Chủ đề: Trợ lý tra cứu lịch tiêm chủng trẻ em & nhà thuốc Long Châu")
    print("=" * 60)

    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(f"🔌 LLM Provider: {provider.__class__.__name__} (Model: {model_name})")
    check_integration()

    logger = TraceLogger()

    if args.chat:
        interactive_chat(provider, logger)
    else:
        tests = load_test_cases()
        if args.case:
            tests = [t for t in tests if t["id"] == args.case]
            if not tests:
                print(f"❌ Không có test case id={args.case}")
                return
        print(f"✅ Đã tải {len(tests)} Test Cases từ config/test_cases.json")

        for tc in tests:
            print("\n" + "=" * 60)
            print(f"📝 TEST CASE #{tc['id']} — {tc['category']}")
            print("=" * 60)
            if not args.agent_only:
                run_baseline_chatbot(tc["question"], provider, logger,
                                     case_id=tc["id"], category=tc["category"])
            run_react_agent(tc["question"], provider, logger,
                            case_id=tc["id"], category=tc["category"])

    logger.close()
    print("\n" + "=" * 60)
    print(logger.build_scorecard())
    path = logger.save_report()
    if path:
        print(f"\n✅ Báo cáo đầy đủ (trace + scorecard): {os.path.relpath(path, BASE_DIR)}")
    print(f"\n{REQUIRED_DISCLAIMER}")


if __name__ == "__main__":
    main()
