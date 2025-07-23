from keep_alive import keep_alive
import os
from ap_main import setup_bot, start_bot

def main():
    keep_alive()
    updater = setup_bot()
    start_bot(updater)

if __name__ == "__main__":
    os.environ["TELEGRAM_TOKEN"] = "BURAYA_TELEGRAM_BOT_TOKENIN"
    main()
