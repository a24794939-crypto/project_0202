import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel
from langchain_openai import ChatOpenAI

# --- 1. 設定模型 (vLLM) ---
model = ChatOpenAI(
    base_url="https://ws-02.wade0426.me/v1",
    api_key="EMPTY",
    model="Qwen/Qwen3-VL-2B-Instruct",
    temperature=0.1,
    max_tokens=256
)

# --- 2. 定義人設分工 (在這裡更換風格) ---

# Branch A: 宮廷太后風格
empress_chain = (
    ChatPromptTemplate.from_template(
        "你是深宮中的太后。請針對主題：{topic}，用優雅、威嚴且帶有宮廷古風口吻（例如哀家、哀家認為）寫一段短評(50字內)。"
    ) | model | StrOutputParser()
)

# Branch B: 動漫熱血主角風格
anime_chain = (
    ChatPromptTemplate.from_template(
        "你是經典少年動漫的熱血男主角。請針對主題：{topic}，用極度熱血、充滿鬥志與羈絆的口吻寫一段短評，包含感嘆號和熱血 Emoji (50字內)。"
    ) | model | StrOutputParser()
)

# --- 3. 優雅組合 (Parallel) ---
# 注意：這裡 key 的名稱 (例如 empress, anime) 可以自由指定，它會決定最後輸出的字典欄位名
combo_chain = RunnableParallel(
    empress=empress_chain,
    anime=anime_chain
)

# ==========================================
#  使用者輸入區
# ==========================================
target_topic = input("輸入主題:")

# --- 模式 1: 體驗 Streaming (流式輸出) ---
print(f"=== [Mode 1: Streaming] 即時生成中... ===")
for chunk in combo_chain.stream({"topic": target_topic}):
    print(chunk) 

# --- 模式 2: 體驗 Batch (批次/完整輸出) ---
print(f"\n\n=== [Mode 2: Batch] 完整執行結果 ===")
start_time = time.time()
results = combo_chain.batch([{"topic": target_topic}])
end_time = time.time()

final_result = results[0]

print(f"耗時: {end_time - start_time:.2f} 秒")
print(f"--------------------------------------------------")
print(f"【太后說】：\n{final_result['empress']}")
print(f"--------------------------------------------------")
print(f"【熱血主角說】：\n{final_result['anime']}")
print(f"--------------------------------------------------")