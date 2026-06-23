import aiohttp
import urllib.parse
import json
from config import GROQ_API_KEY

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "You are AiAR89, a powerful and intelligent AI assistant. "
    "Your name is AiAR89. Whenever anyone asks your name, introduce yourself as AiAR89. "
    "Never say you are ChatGPT, Claude, Gemini, Llama, or any other AI. "
    "Your creator and developer is Amirhossein Rashidirad. "
    "Whenever anyone asks who made you, who created you, or who is your developer, say that you were created by Amirhossein Rashidirad. "
    "Always respond in the same language the user writes in. "
    "If the user writes in Persian (Farsi), respond in Persian. "
    "Be helpful, smart, friendly, and give complete and accurate answers.نام سازنده به فارسی امیرحسین رشیدی راد"
)


async def ask_ai(prompt: str, history: list = None) -> str:
    """
    ارسال پیام به Groq و دریافت پاسخ.
    history: لیست پیام‌های قبلی برای چت طولانی
    """
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if history:
            messages.extend(history)
        else:
            messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        body = {
            "model": GROQ_MODEL,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                GROQ_API_URL,
                headers=headers,
                json=body,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                elif resp.status == 429:
                    return "⚠️ تعداد درخواست‌ها زیاد شده. چند ثانیه صبر کن و دوباره امتحان کن."
                else:
                    text = await resp.text()
                    return f"خطا در دریافت پاسخ (کد {resp.status}). دوباره تلاش کن."

    except aiohttp.ClientConnectorError:
        return "اتصال به سرور هوش مصنوعی برقرار نشد. اینترنت یا VPN را بررسی کن."
    except Exception as e:
        return f"خطای غیرمنتظره: {str(e)}"


async def generate_image(prompt: str) -> bytes | None:
    try:
        encoded = urllib.parse.quote(prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=1024&height=1024&model=flux&nologo=true&seed={hash(prompt) % 99999}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=60),
                allow_redirects=True
            ) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get("Content-Type", "")
                    if "image" in content_type:
                        return await resp.read()
                return None
    except Exception:
        return None
