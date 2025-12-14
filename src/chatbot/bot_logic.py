import re
from typing import Dict, List, Optional
import random

class ExpenseBotLogic:
    """
    Context-aware logic engine. It uses the chat history to understand 
    what the user is replying to.
    """
    
    async def generate_reply(self, user_message: str, user_id: str, chat_history: List[Dict]) -> Dict:
        message_lower = user_message.lower().strip()
        last_bot_message = self._get_last_bot_message(chat_history)
        
        # 1. Check if user is replying to a specific question (Context Flow)
        context_reply = self._handle_contextual_flow(message_lower, last_bot_message)
        if context_reply:
            return context_reply

        # 2. Check for general intents (Keywords)
        extracted = self.extract_information(user_message)
        return self._handle_new_intent(message_lower, extracted)

    def _get_last_bot_message(self, history: List[Dict]) -> Optional[str]:
        # History comes from DB (newest first usually). Find the first 'bot' message.
        if not history: return None
        for msg in history:
            if msg['sender'] == 'bot':
                return msg['message']
        return None

    def _handle_contextual_flow(self, message: str, last_bot_msg: Optional[str]) -> Optional[Dict]:
        """Checks if the user's message is an answer to the bot's previous question."""
        if not last_bot_msg: return None
        last_msg_lower = last_bot_msg.lower()

        # Context: Bot asked for Group Name
        if "name" in last_msg_lower and "group" in last_msg_lower:
            return {
                "reply": f"'{message}' is a great name. Who should be in this group? (List User IDs separated by commas)",
                "extracted": [{"category": "group_name", "value": message}]
            }

        # Context: Bot asked for Members
        if "user ids" in last_msg_lower:
            members = [m.strip() for m in message.split(',')]
            return {
                "reply": f"I've noted {len(members)} members. You can now go to the dashboard to finalize this group.",
                "extracted": [{"category": "group_members", "value": str(members)}]
            }

        # Context: Bot asked "How many people?" (Split logic)
        if "how many people" in last_msg_lower:
            match = re.search(r'\d+', message)
            if match:
                count = int(match.group(0))
                # We need to find the amount from previous context, but for now let's be generic
                return {
                    "reply": f"Okay, splitting among {count} people. That simplifies things! Anything else?",
                    "extracted": []
                }

        return None

    def _handle_new_intent(self, message: str, extracted: List[Dict]) -> Dict:
        """Handles new topics."""
        
        # Intent: Greetings
        if any(x in message for x in ['hi', 'hello', 'hey', 'start']):
            return {
                "reply": "Hello! I can help you split bills, track debts, or find places to go. Try saying 'Split 500' or 'Suggest a place in Goa'.",
                "extracted": []
            }

        # Intent: Recommendations (Goa, Bangalore, etc.)
        if "spot" in message or "place" in message or "visit" in message:
            loc_match = self._extract_location(message)
            location = loc_match if loc_match else "your city"
            
            suggestions = [
                f"If you're in {location}, check out the local cafes near the city center.",
                f"For {location}, I recommend trying the popular seafood spots!",
                f"{location} has great nightlife. Are you planning a dinner or a party?"
            ]
            return {
                "reply": random.choice(suggestions),
                "extracted": [{"category": "location_interest", "value": location}]
            }

        # Intent: Split Bill
        if "split" in message or "divide" in message:
            amount_match = next((e for e in extracted if e['category'] == 'amount'), None)
            if amount_match:
                return {
                    "reply": f"I see an amount of {amount_match['value']}. How many people are splitting this?",
                    "extracted": extracted
                }
            return {
                "reply": "Sure, I can help split. What is the total amount?",
                "extracted": []
            }

        # Intent: Create Group
        if "create" in message and "group" in message:
            return {
                "reply": "Let's set up a new group. What would you like to name it?",
                "extracted": []
            }

        # Fallback
        return {
            "reply": "I didn't quite catch that. You can ask me to 'Split a bill' or 'Create a group'.",
            "extracted": extracted
        }

    def extract_information(self, message: str) -> List[Dict]:
        extracted = []
        # Extract Amount (e.g. 500, 500rs, rs. 500)
        amount_match = re.search(r'(?:rs\.?|₹)?\s*(\d+(?:\.\d{2})?)\s*(?:rs\.?|₹)?', message, re.IGNORECASE)
        if amount_match:
            try:
                extracted.append({"category": "amount", "value": str(float(amount_match.group(1))), "context": message})
            except: pass
        return extracted

    def _extract_location(self, message: str) -> Optional[str]:
        # Simple heuristic: Look for capitalized words that aren't keywords
        words = message.split()
        for word in words:
            if word[0].isupper() and len(word) > 3 and word.lower() not in ['what', 'where', 'good']:
                return word
        return None