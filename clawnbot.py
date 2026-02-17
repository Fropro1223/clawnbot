import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, Application
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger
import dateparser
import google.generativeai as genai

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
TOKEN = os.environ.get("CLAWNBOT_TOKEN")
DB_FILE = "sqlite:///jobs.sqlite"

# Configure Gemini
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    # Using a fast and capable model
    model = genai.GenerativeModel('gemini-1.5-flash') 
else:
    model = None

# Read Context
try:
    with open("CONTEXT.md", "r") as f:
        SYSTEM_CONTEXT = f.read()
except Exception as e:
    SYSTEM_CONTEXT = "You are a helpful assistant."
    print(f"⚠️ Warning: CONTEXT.md not found: {e}")

# Scheduler Configuration
jobstores = {
    'default': SQLAlchemyJobStore(url=DB_FILE)
}
scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="Europe/Istanbul")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Greeting message."""
    await update.message.reply_text(
        "Merhaba! Ben Clawnbot 🤖\n\n"
        "Bana zaman ayarlı mesajlar gönderebilirsin.\n"
        "Komutlar:\n"
        "• /hatirlat <zaman> <mesaj> - Hatırlatma kurar\n"
        "  (Örn: /hatirlat 10 dakika sonra Fırını kapat)\n"
        "• /liste - Aktif hatırlatmaları listeler\n"
        "• /iptal <id> - Hatırlatmayı iptal eder"
    )

async def send_reminder(chat_id: int, message: str):
    """Callback function to send the reminder."""
    # We need to create a new application instance or use the existing bot instance to send message
    # Since this runs in a separate job, we use the bot token directly.
    # Note: APScheduler runs this in the event loop.
    from telegram import Bot
    bot = Bot(token=TOKEN)
    try:
        await bot.send_message(chat_id=chat_id, text=f"⏰ HATIRLATMA: {message}")
        print(f"✅ Reminder sent to {chat_id}: {message}", flush=True)
    except Exception as e:
        print(f"❌ Failed to send reminder: {e}", flush=True)

async def schedule_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses time and schedules a message."""
    if not context.args:
        await update.message.reply_text("Kullanım: /hatirlat <zaman> <mesaj>\nÖrn: /hatirlat yarın 14:00 Toplantı var")
        return

    # Split args into time string and message
    # Heuristic: We try to parse the beginning of the string as time.
    # Since dateparser is smart, let's try to assume the message starts after the time.
    # However, natural language is tricky. 
    # Strategy: Combine all args, verify if it contains a time logic.
    
    # Better Strategy for this specific bot command structure:
    # Let's try to split by common time prepositions or just rely on dateparser's search?
    # Actually, simpler: join everything, assume the dateparser picks up the time info implicitly?
    # No, dateparser.parse returns a datetime.
    
    # Improved Strategy:
    # 1. Join all args.
    # 2. Use dateparser with 'PREFER_DATES_FROM': 'future'
    # 3. If we find a date, we schedule it. The "message" is trickier to extract if mixed.
    # Let's ask the user to simplify: /hatirlat <zaman_ifadesi> | <mesaj> might be easier but less natural.
    # Let's try to parse the first few words as time.
    
    full_text = " ".join(context.args)
    
    # Try to split by common keyword if possible, or just parse the whole thing and see what dateparser returns.
    # Issue: "5 dakika sonra" -> dateparser parses "5 dakika sonra" correctly.
    # Problem: How to separate "5 dakika sonra" from "Fırını kapat"?
    
    # Let's iterate words to find the split point where dateparser returns a valid date
    # This is a bit brute-force but works for "time first" commands.
    
    best_date = None
    split_index = 0
    
    words = context.args
    # Try increasing window of words
    for i in range(1, len(words) + 1):
        time_part = " ".join(words[:i])
        dt = dateparser.parse(time_part, settings={'PREFER_DATES_FROM': 'future', 'To': 'Europe/Istanbul'})
        if dt:
             # Check if it's in the past (dateparser sometimes returns past dates)
             if dt > datetime.now():
                 best_date = dt
                 split_index = i
             # Keep going to see if adding more words refines it (e.g. "next Friday" vs "next")
             # But usually shortest valid match that is in future is risky? 
             # actually "next friday" is better than "next".
             # let's assume greedy match: Keep matching as long as it returns a valid date?
             # But "5 dakika sonra git" -> "5 dakika sonra" is date, "git" breaks it?
             # dateparser might ignore "git" and still return the date.
             pass
    
    # Let's rely on strict splitting for now to be safe or just take the best guess.
    # Alternative: Use " " as separator implies single word time.
    # Let's try: Parse the whole string. If dateparser extracts a date, we use it, 
    # but we don't know WHICH part was the date.
    
    # Reverting to a simpler logic for robustness:
    # Try to parse the first 1-3 words as time expression.
    # Or, use a separator like " - " or "," or just guess.
    
    # Let's try the iterate-until-fail approach which is common.
    # Check 1 word, 2 words, ... N words.
    # If N words parse to a date, and N+1 words parse to SAME date or invalid, maybe N is the boundary?
    # But dateparser is fuzzy.
    
    # Let's stick to a robust assumption: Time is at the start.
    # We will try to parse increasing chunks. We pick the longest chunk that produces a valid future date.
    
    best_len = 0
    final_dt = None
    
    for i in range(len(words), 0, -1):
        test_str = " ".join(words[:i])
        dt = dateparser.parse(test_str, settings={'PREFER_DATES_FROM': 'future'}) # settings={'TIMEZONE': 'Europe/Istanbul'}
        if dt and dt > datetime.now():
            # Found a candidate
            final_dt = dt
            best_len = i
            break # Since we started from longest, this includes the most specific time info? 
                  # WAIT: "5 dakika sonra fırını kapat" -> dateparser might parse the WHOLE thing and ignore "fırını kapat" if it's fuzzy.
                  # If dateparser is too fuzzy, this is bad. 
                  # "strict" parsing is not supported well in dateparser.
    
    # Fallback: Let's assume the user puts time first.
    # Let's try to be smart: parsed_date = dateparser.parse(full_text)
    # If valid, ask user to confirm? No, scheduling should be instant.
    
    # Let's use the `dateparser.search.search_dates` if available?
    try:
        from dateparser.search import search_dates
        # languages=['tr'] helps
        matches = search_dates(full_text, languages=['tr', 'en'], settings={'PREFER_DATES_FROM': 'future'})
        
        if not matches:
            await update.message.reply_text("❌ Zaman ifadesi bulunamadı. Lütfen '10 dakika sonra', 'yarın 14:00' gibi ifadeler kullanın.")
            return

        # matches returns list of (substring, datetime_obj)
        # We take the first one? Or the one that looks like a date?
        # Usually checking the first match is enough for a command like this.
        
        found_text, found_date = matches[0]
        
        if found_date < datetime.now():
            found_date += timedelta(days=1) # If user says "10:00" and it's 11:00, assume tomorrow? 
            # dateparser usually handles this with PREFER_DATES_FROM future, but search_dates might be different.
            if found_date < datetime.now():
                 await update.message.reply_text(f"❌ Geçmiş zaman algılandı: {found_date}. Lütfen gelecek bir zaman belirtin.")
                 return

        # The message content is everything ELSE.
        # We replace the found date text with empty string to get the message? 
        # Be careful of overlaps.
        
        reminder_msg = full_text.replace(found_text, "").strip()
        if not reminder_msg:
            reminder_msg = "Hatırlatma" # Default message
            
        if reminder_msg.startswith("-") or reminder_msg.startswith(":"):
             reminder_msg = reminder_msg[1:].strip()

        # Update final_dt
        final_dt = found_date
        
    except Exception as e:
        logger.error(f"Date parsing error: {e}")
        await update.message.reply_text("❌ Tarih anlaşılamadı.")
        return

    # Schedule the job
    chat_id = update.effective_chat.id
    job = scheduler.add_job(
        send_reminder,
        DateTrigger(run_date=final_dt),
        args=[chat_id, reminder_msg],
        name=str(chat_id) # Store chat_id in name for filtering later
    )

    formatted_time = final_dt.strftime("%d %B %H:%M:%S")
    await update.message.reply_text(
        f"✅ Hatırlatma kuruldu!\n\n"
        f"🕒 Zaman: {formatted_time}\n"
        f"📝 Mesaj: {reminder_msg}\n"
        f"🆔 Job ID: `{job.id}`"
    )

async def list_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List active jobs for this user."""
    chat_id = str(update.effective_chat.id)
    jobs = scheduler.get_jobs()
    
    user_jobs = [j for j in jobs if j.name == chat_id]
    
    if not user_jobs:
        await update.message.reply_text("📭 Aktif hatırlatmanız yok.")
        return

    msg = "📋 **Aktif Hatırlatmalar:**\n"
    for j in user_jobs:
        run_time = j.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
        msg += f"• `{j.id}`: {run_time} - {j.args[1]}\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def cancel_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel a job by ID."""
    if not context.args:
        await update.message.reply_text("Kullanım: /iptal <id>")
        return
        
    job_id = context.args[0]
    chat_id = str(update.effective_chat.id)
    
    job = scheduler.get_job(job_id)
    if not job:
        await update.message.reply_text("❌ Bu ID ile bir hatırlatma bulunamadı.")
        return
        
    if job.name != chat_id:
        await update.message.reply_text("❌ Bu hatırlatma size ait değil.")
        return
        
    scheduler.remove_job(job_id)
    await update.message.reply_text(f"✅ Hatırlatma iptal edildi: {job_id}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages using Gemini."""
    if not model or not GOOGLE_API_KEY:
        # Silently ignore or reply? Users prefer feedback.
        await update.message.reply_text("🧠 Beynim (GOOGLE_API_KEY) henüz takılmadı. Sadece /komut la çalışıyorum.")
        return

    user_msg = update.message.text
    chat_id = update.effective_chat.id
    
    # Indicate typing
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        # Construct Prompt
        full_prompt = f"{SYSTEM_CONTEXT}\n\nUSER MESSAGE: {user_msg}\n\nRESPONSE (In Turkish, helpful, concise):"
        
        # Async generation
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: model.generate_content(full_prompt))
        
        reply = response.text.strip()
        
        # CHECK FOR COMMAND EXECUTION
        if reply.startswith("CMD:"):
            command = reply.replace("CMD:", "").strip()
            await update.message.reply_text(f"💻 AI Komut Çalıştırıyor: `{command}`", parse_mode='Markdown')
            
            # Execute Command
            import subprocess
            try:
                proc = subprocess.run(
                    command, 
                    shell=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30
                )
                output = proc.stdout
                error = proc.stderr
                
                final_response = ""
                if output:
                    final_response += f"📄 **Çıktı:**\n```\n{output[:3000]}\n```"
                if error:
                    final_response += f"\n⚠️ **Hata:**\n```\n{error[:1000]}\n```"
                    
                if not final_response:
                    final_response = "✅ Komut çalıştı (Çıktı yok)."
                    
                await update.message.reply_text(final_response, parse_mode='Markdown')
                
            except Exception as cmd_err:
                await update.message.reply_text(f"❌ Komut Hatası: {str(cmd_err)}")
        else:
            # Normal text response
            await update.message.reply_text(reply, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        await update.message.reply_text(f"🤯 Hata oluştu: {str(e)}")

def main():
    if not TOKEN:
        print("❌ HATA: CLAWNBOT_TOKEN environment variable bulunamadı!", flush=True)
        return

    # Create the application configuration
    app = ApplicationBuilder().token(TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hatirlat", schedule_message))
    app.add_handler(CommandHandler("liste", list_jobs))
    app.add_handler(CommandHandler("iptal", cancel_job))
    app.add_handler(CommandHandler("term", term_command))
    
    # NEW: Handle text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Post-init hook to start scheduler
    async def post_init(application: Application):
        scheduler.start()
        print("🚀 Scheduler started inside event loop.", flush=True)
        if GOOGLE_API_KEY:
            print("🧠 Gemini AI connected.", flush=True)
        else:
            print("⚠️ Gemini AI NOT connected (Missing GOOGLE_API_KEY).", flush=True)

    # Run the bot
    app.post_init = post_init
    app.run_polling()

async def term_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute a terminal command."""
    # SECURITY: Check user ID
    # Add allowed user ID to .env or hardcode check if crucial
    # For now, we assume the user configuring this is the owner.
    # Ideally: allowed_id = int(os.environ.get("ALLOWED_TELEGRAM_ID"))
    
    if not context.args:
        await update.message.reply_text("Kullanım: /term <komut>\nÖrn: /term ls -la")
        return

    command = " ".join(context.args)
    
    await update.message.reply_text(f"💻 Çalıştırılıyor: `{command}`", parse_mode='Markdown')
    
    try:
        # Run command
        # Capture output
        import subprocess
        
        # Enforce CWD as workspace root if needed, or rely on script loc
        # Using shell=True is dangerous but requested for "terminal usage"
        
        proc = subprocess.run(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            timeout=30 # 30s timeout
        )
        
        output = proc.stdout
        error = proc.stderr
        
        response = ""
        if output:
            response += f"📄 **Çıktı:**\n```\n{output[:3000]}\n```" # Truncate for Telegram limit
        if error:
            response += f"\n⚠️ **Hata:**\n```\n{error[:1000]}\n```"
            
        if not response:
            response = "✅ Komut çalıştı (Çıktı yok)."
            
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except subprocess.TimeoutExpired:
        await update.message.reply_text("❌ Zaman aşımı (30s).")
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {str(e)}")


if __name__ == "__main__":
    main()
