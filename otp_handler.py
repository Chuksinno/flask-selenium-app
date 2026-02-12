# otp_handler.py - ENHANCED VERSION (Optional)
from telegram.ext import Application, MessageHandler, filters
import threading
import queue
import logging
from datetime import datetime, timedelta

OTP_QUEUE = queue.Queue()
OTP_TIMEOUT = 180  # 3 minutes
OTP_ATTEMPTS = {}

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def start_otp_listener(bot_token: str):
    def _run():
        try:
            # Create application with new syntax
            application = Application.builder().token(bot_token).build()

            def handle_otp(update, context):
                user_id = update.effective_user.id
                otp = update.message.text.strip()
                
                # Rate limiting check
                current_time = datetime.now()
                if user_id in OTP_ATTEMPTS:
                    time_diff = current_time - OTP_ATTEMPTS[user_id]
                    if time_diff < timedelta(seconds=30):
                        update.message.reply_text("⏳ Please wait 30 seconds between OTP attempts.")
                        return
                
                OTP_ATTEMPTS[user_id] = current_time
                
                # Validate OTP
                if otp.isdigit() and 4 <= len(otp) <= 8:
                    OTP_QUEUE.put(otp)
                    logging.info(f"OTP received from user {user_id}: {otp}")
                    update.message.reply_text(f"✅ OTP received: `{otp}`\n\nProcessing authentication...", parse_mode='Markdown')
                else:
                    update.message.reply_text("❌ Invalid OTP format.\n\nPlease send only 4-8 digits.")
                    logging.warning(f"Invalid OTP attempt from user {user_id}: {otp}")

            # Add handler
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp))
            
            print("[🔄] Starting OTP polling service...")
            logging.info("OTP listener starting polling...")
            application.run_polling()
            
        except Exception as e:
            print(f"[❌] OTP listener error: {e}")
            logging.error(f"OTP listener crashed: {e}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    print("[✅] OTP listener thread started successfully.")
    logging.info("OTP listener thread initialized.")

# Helper function to get OTP with timeout
def get_otp(timeout=OTP_TIMEOUT):
    """
    Get OTP from queue with timeout
    Returns OTP string or None if timeout
    """
    try:
        return OTP_QUEUE.get(timeout=timeout)
    except:
        return None

# Optional: Clear old OTP attempts periodically
def cleanup_old_attempts():
    """Remove OTP attempts older than 1 hour"""
    current_time = datetime.now()
    expired_users = [
        user_id for user_id, timestamp in OTP_ATTEMPTS.items()
        if current_time - timestamp > timedelta(hours=1)
    ]
    for user_id in expired_users:
        del OTP_ATTEMPTS[user_id]