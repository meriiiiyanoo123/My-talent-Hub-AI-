import os
import json
import anthropic
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pypdf import PdfReader
import io

app = FastAPI()

# السماح بالاتصال من أي مكان لتجنب مشاكل الهاتف
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# جلب المفتاح السري تلقائياً من إعدادات Render
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

def extract_text_from_pdf(file_bytes):
    pdf_file = io.BytesIO(file_bytes)
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# مسار استقبال الـ CV والفرز بالذكاء الاصطناعي
@app.post("/api/candidates/upload")
async def upload_and_screen(file: UploadFile = File(...), job_description: str = Form(...)):
    if not CLAUDE_API_KEY:
        return {"error": "مفتاح الـ API الخاص بـ Claude غير مفعّل في إعدادات المنصة!"}
        
    try:
        file_bytes = await file.read()
        cv_text = extract_text_from_pdf(file_bytes)
        
        prompt = f"""
        قارن السيرة الذاتية التالية بمتطلبات الوظيفة بدقة عالية.
        متطلبات الوظيفة: {job_description}
        السيرة الذاتية: {cv_text}
        
        يجب أن يكون الرد بصيغة JSON فقط كالتالي (دون أي كلام جانبي أو مقدمات):
        {{
          "match_score": 85,
          "summary": "ملخص باللغة العربية عن المرشح ومناسبته للوظيفة وما ينقصه",
          "strengths": ["نقطة قوة 1", "نقطة قوة 2"],
          "missing": ["مهارة ناقصة 1", "مهارة ناقصة 2"]
        }}
        """
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        
        ai_result = json.loads(response.content[0].text)
        return ai_result

    except Exception as e:
        return {"error": str(e)}

# تشغيل صفحة الواجهة فوراً عند فتح رابط Render
@app.get("/")
async def read_index():
    return FileResponse('index.html')
    
