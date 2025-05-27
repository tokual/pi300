import json
import os
import sys
from telethon import TelegramClient
from telethon.tl.types import Message
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram API credentials from environment variables
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')

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
        
        # Initialize client for user account
        self.client = TelegramClient('user_session', API_ID, API_HASH)
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
    
    async def setup_session_if_needed(self):
        """Set up session if it doesn't exist"""
        if not self.session_exists():
            print("No session file found. Setting up authentication...")
            print("This is a one-time setup process.")
            
            # Check if we're running in an automated environment (cron)
            if not sys.stdin.isatty():
                print("ERROR: Cannot authenticate in automated environment (cron job).")
                print("Please run this script manually first to create the session file:")
                print("cd /home/pi300/pi300 && python3 main.py")
                raise RuntimeError("Authentication required but running in non-interactive mode")
            
            try:
                # Start the client and handle authentication
                await self.client.start(phone=PHONE_NUMBER)
                print("Authentication successful! Session file created.")
                print("Future runs will use this session automatically.")
                
                # Test the connection
                me = await self.client.get_me()
                print(f"Logged in as: {me.first_name} {me.last_name or ''} (@{me.username or 'no username'})")
                
                return True
                
            except Exception as e:
                print(f"Authentication failed: {e}")
                # Clean up partial session file if authentication failed
                if os.path.exists('user_session.session'):
                    os.remove('user_session.session')
                raise
        else:
            print("Using existing session file.")
            await self.client.start()
            return True
    
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
            messages = await self.client.get_messages(SOURCE_CHANNEL, limit=limit)
            
            new_messages_count = 0
            
            # Process messages in chronological order (oldest first)
            for message in reversed(messages):
                if isinstance(message, Message) and message.id not in self.forwarded_messages:
                    try:
                        # Forward the message
                        await self.client.forward_messages(
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
    
    async def run(self):
        """Main execution method"""
        try:
            # Set up session (authenticate if needed)
            await self.setup_session_if_needed()
            print("Connected to Telegram as user")
            
            # Proceed with message forwarding
            await self.forward_new_messages()
            
        finally:
            await self.client.disconnect()

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
