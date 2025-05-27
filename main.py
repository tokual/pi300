import json
import os
import sys
from telethon import TelegramClient
from telethon.tl.types import Message
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, AuthKeyUnregisteredError
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram API credentials from environment variables
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')

# Bot credentials
BOT_TOKEN = os.getenv('BOT_TOKEN')
USER_CHAT_ID = os.getenv('USER_CHAT_ID')

# Channel configuration from environment variables
SOURCE_CHANNEL = os.getenv('SOURCE_CHANNEL')
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL')

# File to track forwarded messages
FORWARDED_MESSAGES_FILE = os.getenv('FORWARDED_MESSAGES_FILE', 'forwarded_messages.json')

class TelegramForwarder:
    def __init__(self):
        # Validate required environment variables
        if not all([API_ID, API_HASH, PHONE_NUMBER, SOURCE_CHANNEL, TARGET_CHANNEL]):
            raise ValueError("Missing required environment variables. Check your .env file.")
        
        # Initialize clients
        self.user_client = TelegramClient('user_session', API_ID, API_HASH)
        self.bot_client = None
        self.forwarded_messages = self.load_forwarded_messages()
    
    def load_forwarded_messages(self):
        """Load the list of already forwarded message IDs"""
        if os.path.exists(FORWARDED_MESSAGES_FILE):
            try:
                with open(FORWARDED_MESSAGES_FILE, 'r') as f:
                    data = json.load(f)
                    return set(data) if data else set()
            except (json.JSONDecodeError, FileNotFoundError):
                return set()
        return set()
    
    def save_forwarded_messages(self):
        """Save the list of forwarded message IDs"""
        with open(FORWARDED_MESSAGES_FILE, 'w') as f:
            json.dump(list(self.forwarded_messages), f)
    
    def is_first_run(self):
        """Check if this is the first run (empty or non-existent JSON file)"""
        return len(self.forwarded_messages) == 0
    
    def session_exists(self):
        """Check if session file exists"""
        return os.path.exists('user_session.session')
    
    async def send_bot_notification(self, message):
        """Send notification via bot when user session fails"""
        if not BOT_TOKEN or not USER_CHAT_ID:
            print("Bot credentials not configured. Cannot send notification.")
            return False
        
        try:
            print("Sending notification via bot...")
            self.bot_client = TelegramClient('bot_session', API_ID, API_HASH)
            await self.bot_client.start(bot_token=BOT_TOKEN)
            
            await self.bot_client.send_message(int(USER_CHAT_ID), message)
            print("Notification sent successfully via bot.")
            
            await self.bot_client.disconnect()
            return True
            
        except Exception as e:
            print(f"Failed to send bot notification: {e}")
            return False
    
    async def is_session_valid(self):
        """Check if the existing session is valid without triggering interactive login"""
        try:
            await self.user_client.connect()
            
            # Check if user is authorized without triggering interactive login
            if await self.user_client.is_user_authorized():
                print("Session is valid.")
                return True
            else:
                print("Session exists but user is not authorized.")
                return False
                
        except Exception as e:
            print(f"Session validation failed: {e}")
            return False
    
    async def setup_session_if_needed(self):
        """Set up session if it doesn't exist or is invalid"""
        # First, check if we have a valid session
        if self.session_exists():
            if await self.is_session_valid():
                return True
            else:
                print("Removing invalid session file...")
                # Disconnect first
                if self.user_client.is_connected():
                    await self.user_client.disconnect()
                # Remove invalid session files
                for session_file in ['user_session.session', 'user_session.session-journal']:
                    if os.path.exists(session_file):
                        os.remove(session_file)
                        print(f"Removed {session_file}")
        
        # If we reach here, we need to create a new session
        print("No valid session found. Setting up authentication...")
        print("This is a one-time setup process.")
        
        # Check if we're running in an automated environment (cron)
        if not sys.stdin.isatty():
            print("ERROR: Cannot authenticate in automated environment (cron job).")
            
            # Send bot notification about authentication needed
            await self.send_bot_notification(
                "🚨 Telegram Forwarder Alert 🚨\n\n"
                "User session has expired and requires re-authentication.\n"
                "Please run the following command manually:\n\n"
                "cd /home/pi300/pi300 && python3 main.py\n\n"
                "The automated forwarding has been paused until re-authentication is complete."
            )
            
            raise RuntimeError("Authentication required but running in non-interactive mode")
        
        try:
            # Create a fresh client for authentication
            auth_client = TelegramClient('user_session', API_ID, API_HASH)
            
            # Start with phone number for new authentication
            await auth_client.start(phone=PHONE_NUMBER)
            print("Authentication successful! Session file created.")
            
            # Test the connection
            me = await auth_client.get_me()
            print(f"Logged in as: {me.first_name} {me.last_name or ''} (@{me.username or 'no username'})")
            
            # Disconnect the auth client
            await auth_client.disconnect()
            
            # Now reconnect with our main client using the new session
            self.user_client = TelegramClient('user_session', API_ID, API_HASH)
            await self.user_client.connect()
            
            # Send success notification
            await self.send_bot_notification(
                "✅ Telegram Forwarder Authenticated ✅\n\n"
                f"Successfully logged in as: {me.first_name} {me.last_name or ''}\n"
                "Automated message forwarding is now active."
            )
            
            return True
            
        except Exception as e:
            print(f"Authentication failed: {e}")
            
            # Send failure notification
            await self.send_bot_notification(
                "❌ Telegram Forwarder Authentication Failed ❌\n\n"
                f"Error: {str(e)}\n\n"
                "Please check your credentials and try manual authentication:\n"
                "cd /home/pi300/pi300 && python3 main.py"
            )
            
            # Clean up partial session files if authentication failed
            for session_file in ['user_session.session', 'user_session.session-journal']:
                if os.path.exists(session_file):
                    os.remove(session_file)
            
            raise
    
    async def forward_new_messages(self):
        """Forward new messages from source to target channel"""
        try:
            # Determine how many messages to check based on first run
            if self.is_first_run():
                print("First run detected - will only forward the latest message")
                limit = 1  # Only get the latest message on first run
            else:
                limit = 50  # Normal operation - check last 50 messages
            
            # Get recent messages from source channel
            messages = await self.user_client.get_messages(SOURCE_CHANNEL, limit=limit)
            
            new_messages_count = 0
            
            # Process messages in chronological order (oldest first)
            for message in reversed(messages):
                if isinstance(message, Message) and message.id not in self.forwarded_messages:
                    try:
                        # Forward the message
                        await self.user_client.forward_messages(
                            entity=TARGET_CHANNEL,
                            messages=message,
                            from_peer=SOURCE_CHANNEL
                        )
                        
                        # Mark as forwarded
                        self.forwarded_messages.add(message.id)
                        new_messages_count += 1
                        
                        print(f"Forwarded message ID {message.id}")
                        
                        # Rate limiting: Wait between forwards
                        if new_messages_count > 1:
                            await asyncio.sleep(2)
                        
                    except Exception as e:
                        print(f"Error forwarding message ID {message.id}: {e}")
                        if "Too Many Requests" in str(e):
                            print("Rate limit hit, waiting 60 seconds...")
                            await asyncio.sleep(60)
            
            # Save the updated list
            self.save_forwarded_messages()
            
            if new_messages_count > 0:
                print(f"Successfully forwarded {new_messages_count} new messages")
            else:
                print("No new messages to forward")
                
        except Exception as e:
            print(f"Error in forward_new_messages: {e}")
            
            # Send error notification if it's a critical issue
            await self.send_bot_notification(
                "❌ Telegram Forwarder Error ❌\n\n"
                f"Error during message forwarding: {str(e)}\n\n"
                "Please check the system logs for more details."
            )
    
    async def run(self):
        """Main execution method"""
        try:
            # Set up session (authenticate if needed)
            await self.setup_session_if_needed()
            print("Connected to Telegram as user")
            
            # Proceed with message forwarding
            await self.forward_new_messages()
            
        finally:
            if self.user_client and self.user_client.is_connected():
                await self.user_client.disconnect()
            if self.bot_client and self.bot_client.is_connected():
                await self.bot_client.disconnect()

async def main():
    print("Starting Telegram message forwarder...")
    
    try:
        forwarder = TelegramForwarder()
        await forwarder.run()
    except ValueError as e:
        print(f"Configuration error: {e}")
        return
    except RuntimeError as e:
        print(f"Runtime error: {e}")
        return
    except Exception as e:
        print(f"Unexpected error: {e}")
        return
    
    print("Telegram forwarder completed.")

if __name__ == "__main__":
    asyncio.run(main())
