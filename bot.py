from quart import Quart, request
import asyncio
import re
import logging
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import openai
import config

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# OpenAI API設定
openai.api_key = config.OPENAI_API_KEY
bot = Bot(token=config.TELEGRAM_TOKEN)

# Web サーバー設定
app = Quart(__name__)

# ユーザー履歴の保存
user_histories = {}

def extract_links_with_titles(text):
    """
    テキストからタイトル付きリンクを抽出します。

    Args:
        text: リンクを抽出するテキスト。

    Returns:
        (タイトル, リンク) のタプルのリスト。
    """
    pattern = r'\[(.+?)\]\((https?://\S+?)\)'
    return re.findall(pattern, text)

async def chat_with_gpt(history):
    """
    OpenAIのGPTモデルを使用して、チャットの応答を生成します。

    Args:
        history: チャット履歴 ({"role": "user" or "assistant", "content": メッセージ内容}) のリスト。

    Returns:
        GPTモデルからの応答メッセージ。
    """
    try:
        response = await asyncio.to_thread(
            openai.ChatCompletion.create,
            model="o1-mini-2024-09-12",  # 利用可能なモデルに変更してください
            messages=history,
            max_tokens=1400,
            temperature=0.7
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"GPTエラー: {e}")
        return "申し訳ありません。一時的な通信エラーが発生しました。"

@app.route("/", methods=["GET"])
async def health_check():
    """
    ヘルスチェック用エンドポイント。
    """
    return "Health Check OK", 200

@app.route("/webhook", methods=["POST"])
async def webhook():
    """
    Telegram Bot Webhookのエンドポイント。
    """
    try:
        update = await request.get_json()
        if "message" in update:
            chat_id = update["message"]["chat"]["id"]
            user_message = update["message"].get("text", "")

            # /startコマンドまたは新規ユーザーの処理
            if user_message.startswith("/start") or chat_id not in user_histories:
              if user_message.startswith("/start"):
                # /start のみの処理 (例：使い方の説明)
                if chat_id not in user_histories:
                  user_histories[chat_id] = [{"role": "system", "content": config.SYSTEM_PROMPT}]
                reply_message = config.GREETING_MESSAGE
              elif chat_id not in user_histories:
                # 新規ユーザーの場合のみ、履歴を初期化
                user_histories[chat_id] = [{"role": "system", "content": config.SYSTEM_PROMPT}]
                reply_message = config.GREETING_MESSAGE
            else:
                # 通常のメッセージ処理
                user_histories[chat_id].append({"role": "user", "content": user_message})
                reply_message = await chat_with_gpt(user_histories[chat_id])
                user_histories[chat_id].append({"role": "assistant", "content": reply_message})

            # メイン応答を送信
            try:
                await bot.send_message(chat_id=chat_id, text=reply_message)
            except Exception as e:
                logger.error(f"Telegram send_message error: {e}")
                await bot.send_message(chat_id=chat_id, text="メッセージの送信に失敗しました。")

            # リンクの処理 (存在する場合)
            links_with_titles = extract_links_with_titles(reply_message)
            if links_with_titles:
                buttons = [
                    InlineKeyboardButton(text=title, url=link)
                    for title, link in links_with_titles
                ]
                reply_markup = InlineKeyboardMarkup.from_column(buttons)
                try:
                    await bot.send_message(chat_id=chat_id, text="関連リンクはこちらです:", reply_markup=reply_markup)
                except Exception as e:
                    logger.error(f"Telegram send_message error: {e}")
                    await bot.send_message(chat_id=chat_id, text="リンクメッセージの送信に失敗しました。")

        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Internal Server Error", 500