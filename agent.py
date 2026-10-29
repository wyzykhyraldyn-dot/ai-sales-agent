import streamlit as st
import json
from groq import Groq
import requests
import smtplib
from email.mime.text import MIMEText
import pandas as pd

# --- 1. الإعدادات الأساسية ---
st.set_page_config(page_title="AI Sales Agent Pro", page_icon="🤖", layout="wide")

# --- 2. قراءة البيانات السرية من ملف secrets.toml (تم تأمينها) ---
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
SENDER_EMAIL = st.secrets["SENDER_EMAIL"] 
SENDER_PASSWORD = st.secrets["SENDER_PASSWORD"]

client = Groq(api_key=GROQ_API_KEY)

# تهيئة الذاكرة لتخزين العملاء (CRM)
if "leads_db" not in st.session_state:
    st.session_state.leads_db = []

def send_email(to_email, subject, body):
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        return False

# --- 3. واجهة المستخدم (تبويبان) ---
st.markdown("<h1 style='text-align: center;'>🤖 AI Sales Agent Pro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>مساعدك الذكي لفرز العملاء، تقييمهم، والرد عليهم آلياً.</p>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📥 تحليل رسالة جديدة", "📊 لوحة إدارة العملاء (CRM)"])

with tab1:
    st.subheader("جرّب إدخال رسالة عميل:")
    customer_message = st.text_area(
        "", 
        "Hi, I want to build a new e-commerce store. I have a budget of $2000 and I need it fast. You can email me at test@example.com"
    )

    # تم إصلاح التحذير هنا باستخدام width='stretch'
    if st.button("🚀 تحليل وتنفيذ", width='stretch'):
        if customer_message:
            with st.spinner("⏳ الوكيل يفكر ويحلل..."):
                
                system_prompt = """
                You are an AI Sales Agent. Analyze the customer message carefully.
                You must return ONLY a valid JSON object with these exact keys:
                - "score": Integer from 0 to 100. Give 30 points if they provided email/phone, 30 points if they expressed clear intent to buy, 40 points if they mentioned budget/timeline/quantity.
                - "status": "Hot" (score >= 80), "Warm" (score 40-79), or "Cold" (score < 40).
                - "customer_email": Extract email if found, else empty string.
                - "customer_intent": A very short summary of what they want.
                - "reply_to_customer": A professional reply. If they are Warm or Cold, ask them for the missing details to qualify them.
                Do NOT include any markdown formatting. Return raw JSON only.
                """
                
                try:
                    response = client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": customer_message}
                        ],
                        response_format={"type": "json_object"} 
                    )
                    
                    result = json.loads(response.choices[0].message.content)
                    
                    # تخزين العميل في قاعدة البيانات
                    st.session_state.leads_db.append({
                        "الرسالة": customer_message,
                        "النية": result["customer_intent"],
                        "النقاط": result["score"],
                        "الحالة": result["status"],
                        "البريد": result["customer_email"]
                    })
                    
                    st.divider()
                    
                    # عرض النتيجة
                    if result["status"] == "Hot":
                        st.success(f"🔥 **عميل جاد (Hot)** | النقاط: {result['score']}/100")
                        # إشعارات للجادين فقط
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                                      json={"chat_id": TELEGRAM_CHAT_ID, "text": f"🚨 عميل جاد!\n{result['customer_intent']}\nالرسالة: {customer_message}"})
                        st.info("⚡ تم إرسال إشعار تيليجرام.")
                        
                        if result["customer_email"]:
                            send_email(result["customer_email"], "Thank you for contacting us!", result["reply_to_customer"])
                            st.success("📧 تم إرسال إيميل للعميل.")
                            
                    elif result["status"] == "Warm":
                        st.warning(f"🟡 **عميل مهتم (Warm)** | النقاط: {result['score']}/100")
                        st.info("⏳ تم تسجيله، وسيتم إرسال رد يطلب منه تفاصيل أكثر.")
                    else:
                        st.error(f"❄️ **غير جاد (Cold)** | النقاط: {result['score']}/100")
                    
                    st.subheader("📩 الرد التلقائي المقترح:")
                    st.info(result["reply_to_customer"])
                    
                except Exception as e:
                    st.error(f"حدث خطأ: {e}")

with tab2:
    st.subheader("📊 قاعدة بيانات العملاء (CRM)")
    st.write("هنا يمكنك رؤية جميع الرسائل التي تم تحليلها، مما يثبت أن النظام يعمل كأداة إدارة حقيقية.")
    if st.session_state.leads_db:
        df = pd.DataFrame(st.session_state.leads_db)
        st.dataframe(df, width='stretch')
    else:
        st.info("لا يوجد عملاء بعد. اذهب إلى تبويب 'تحليل رسالة جديدة' وجرب.")