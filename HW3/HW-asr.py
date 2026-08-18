import time
import requests
from pathlib import Path
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# --- 1. 定義 LangGraph 的 State (狀態資料結構) ---
class MeetingState(TypedDict):
    audio_path: str
    txt_text: str
    srt_text: str
    detailed_transcript: str
    summary: str
    final_output: str

# --- 2. 設定 API 與 HTTP 認證 ---
BASE = "https://3090api.huannago.com"
CREATE_URL = f"{BASE}/api/v1/subtitle/tasks"
AUTH = ("nutc2504", "nutc2504")

# --- 3. 定義 Node 節點函數 ---

# 節點 1: ASR 語音轉文字 (包含 API 上傳與輪詢下載)
def asr_node(state: MeetingState) -> dict:
    print(r"C:\Users\w10\Downloads\Podcast_EP14_30s.wav")
    wav_path = state["audio_path"]
    
    # 1) 建立任務
    with open(wav_path, "rb") as f:
        r = requests.post(CREATE_URL, files={"audio": f}, timeout=60, auth=AUTH)
    r.raise_for_status()
    task_id = r.json()["id"]
    print(f"Task ID: {task_id}")

    txt_url = f"{BASE}/api/v1/subtitle/tasks/{task_id}/subtitle?type=TXT" 
    srt_url = f"{BASE}/api/v1/subtitle/tasks/{task_id}/subtitle?type=SRT"

    def wait_download(url: str, max_tries=600):
        for _ in range(max_tries):
            try:
                resp = requests.get(url, timeout=(5, 60), auth=AUTH)
                if resp.status_code == 200:
                    return resp.text
            except requests.exceptions.ReadTimeout:
                pass
            time.sleep(2)
        return ""

    txt_text = wait_download(txt_url)
    srt_text = wait_download(srt_url)

    print("=== [Node: ASR] 語音轉錄完成！ ===")
    return {"txt_text": txt_text, "srt_text": srt_text}


# 節點 2: Detailed Minutes Taker (整理詳細逐字稿)
def minutes_taker_node(state: MeetingState) -> dict:
    print("=== [Node: minutes_taker] 整理詳細逐字稿... ===")
    srt_content = state.get("srt_text", "")
    
    # 若有 SRT 則直接使用帶有時間軸的逐字稿，否則退回 txt
    if srt_content:
        transcript = f"【詳細時間軸逐字稿】\n{srt_content}"
    else:
        transcript = f"【逐字稿 (無時間軸)】\n{state.get('txt_text', '')}"
        
    return {"detailed_transcript": transcript}


# 節點 3: Summarizer (重點摘要)
def summarizer_node(state: MeetingState) -> dict:
    print("=== [Node: summarizer] 生成重點摘要... ===")
    txt_content = state.get("txt_text", "")
    
    # 這裡可以用簡意處理或導入 LLM 整理重點
    summary_result = f"【會議重點摘要】\n- 原始文字長度：{len(txt_content)} 字\n- 內容預覽：{txt_content[:150]}..."
    
    return {"summary": summary_result}


# 節點 4: Writer (整合並輸出結果)
def writer_node(state: MeetingState) -> dict:
    print("=== [Node: writer] 結合結果並寫入檔案... ===")
    detailed = state.get("detailed_transcript", "")
    summary = state.get("summary", "")
    
    final_doc = f"{summary}\n\n{'='*40}\n\n{detailed}"
    
    # 寫入 out 資料夾
    out_dir = Path("./out")
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "meeting_minutes_result.txt"
    out_file.write_text(final_doc, encoding="utf-8")
    
    print(f"結果已成功寫入：{out_file}")
    return {"final_output": final_doc}


# --- 4. 建構 LangGraph 圖結構 (Matching the Diagram) ---
workflow = StateGraph(MeetingState)

# 新增 Nodes
workflow.add_node("asr", asr_node)
workflow.add_node("minutes_taker", minutes_taker_node)
workflow.add_node("summarizer", summarizer_node)
workflow.add_node("writer", writer_node)

# 設定 Edges (根據投影片流程圖)
# __start__ -> asr
workflow.add_edge(START, "asr")

# asr 分流到 minutes_taker 與 summarizer (平行處理)
workflow.add_edge("asr", "minutes_taker")
workflow.add_edge("asr", "summarizer")

# minutes_taker 與 summarizer 匯集到 writer
workflow.add_edge("minutes_taker", "writer")
workflow.add_edge("summarizer", "writer")

# writer -> __end__
workflow.add_edge("writer", END)

# 編譯 Graph
app = workflow.compile()

# --- 5. 執行 Graph ---
if __name__ == "__main__":
    init_state = {
        "audio_path": r"C:\Users\w10\Downloads\Podcast_EP14_30s.wav" # 請確保路徑正確
    }
    app.invoke(init_state)