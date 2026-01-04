import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
from datetime import datetime

class BotState(Enum):
    MENU = "menu"
    GENERAL_CHAT = "general_chat"
    
    # Group Creation States
    CREATE_GROUP_NAME = "create_group_name"
    CREATE_GROUP_MEMBERS = "create_group_members"
    CREATE_GROUP_DURATION = "create_group_duration"
    CREATE_GROUP_CONFIRM = "create_group_confirm"
    
    # Edit Group States
    EDIT_GROUP_SELECT = "edit_group_select"
    EDIT_GROUP_CHOICE = "edit_group_choice"
    EDIT_GROUP_NAME = "edit_group_name"
    EDIT_GROUP_MEMBERS = "edit_group_members"
    
    # Plan Group Trip States
    PLAN_GROUP_TRIP_SELECT = "plan_group_trip_select"
    PLAN_GROUP_TRIP_NAME = "plan_group_trip_name"
    PLAN_GROUP_TRIP_CITIES = "plan_group_trip_cities"
    PLAN_GROUP_TRIP_CLASS = "plan_group_trip_class"
    PLAN_GROUP_TRIP_CONFIRM = "plan_group_trip_confirm"
    
    # Add Event States
    ADD_EVENT_GROUP = "add_event_group"
    ADD_EVENT_NAME = "add_event_name"
    ADD_EVENT_DESCRIPTION = "add_event_description"
    ADD_EVENT_AMOUNT = "add_event_amount"
    ADD_EVENT_OWED_BY = "add_event_owed_by"
    ADD_EVENT_OWED_TO = "add_event_owed_to"
    ADD_EVENT_REASON = "add_event_reason"
    ADD_EVENT_CONFIRM = "add_event_confirm"
    
    # Plan Solo Trip States
    PLAN_SOLO_TRIP_NAME = "plan_solo_trip_name"
    PLAN_SOLO_TRIP_CITIES = "plan_solo_trip_cities"
    PLAN_SOLO_TRIP_CLASS = "plan_solo_trip_class"
    PLAN_SOLO_TRIP_CONFIRM = "plan_solo_trip_confirm"
    
    # Settle Debt States
    SETTLE_DEBT_GROUP = "settle_debt_group"
    SETTLE_DEBT_EVENT = "settle_debt_event"
    SETTLE_DEBT_TRANSACTION = "settle_debt_transaction"


class ExpenseBotLogic:
    """
    Advanced conversational bot with state management and task execution
    """
    
    def __init__(self):
        self.gemini_api_key = None  # Set from config if needed
    
    async def generate_reply(
        self, 
        user_message: str, 
        user_id: str, 
        chat_history: List[Dict],
        db_cursor
    ) -> Dict:
        """Main entry point for generating bot replies"""
        
        message_lower = user_message.lower().strip()
        
        # Get current state
        current_state, state_data = await self._get_user_state(user_id, db_cursor)
        
        # Handle based on state
        if current_state == BotState.MENU:
            return await self._handle_menu(message_lower, user_id, db_cursor)
        elif current_state == BotState.GENERAL_CHAT:
            return await self._handle_general_chat(user_message, user_id, db_cursor)
        
        # Task-specific handlers
        elif current_state.name.startswith("CREATE_GROUP"):
            return await self._handle_create_group(user_message, current_state, state_data, user_id, db_cursor)
        elif current_state.name.startswith("EDIT_GROUP"):
            return await self._handle_edit_group(user_message, current_state, state_data, user_id, db_cursor)
        elif current_state.name.startswith("PLAN_GROUP_TRIP"):
            return await self._handle_plan_group_trip(user_message, current_state, state_data, user_id, db_cursor)
        elif current_state.name.startswith("ADD_EVENT"):
            return await self._handle_add_event(user_message, current_state, state_data, user_id, db_cursor)
        elif current_state.name.startswith("PLAN_SOLO_TRIP"):
            return await self._handle_plan_solo_trip(user_message, current_state, state_data, user_id, db_cursor)
        elif current_state.name.startswith("SETTLE_DEBT"):
            return await self._handle_settle_debt(user_message, current_state, state_data, user_id, db_cursor)
        
        # Default fallback
        return await self._reset_to_menu(user_id, db_cursor)
    
    async def _get_user_state(self, user_id: str, cur) -> Tuple[BotState, Dict]:
        """Get user's current conversation state"""
        await cur.execute(
            "SELECT state, state_data FROM ChatbotState WHERE user_id = %s",
            (user_id,)
        )
        result = await cur.fetchone()
        
        if result:
            state = BotState(result["state"])
            state_data = json.loads(result["state_data"]) if result["state_data"] else {}
            return state, state_data
        
        # Default to menu
        await self._set_user_state(user_id, BotState.MENU, {}, cur)
        return BotState.MENU, {}
    
    async def _set_user_state(self, user_id: str, state: BotState, data: Dict, cur):
        """Update user's conversation state"""
        await cur.execute(
            """
            INSERT INTO ChatbotState (user_id, state, state_data) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE state = %s, state_data = %s
            """,
            (user_id, state.value, json.dumps(data), state.value, json.dumps(data))
        )
        await cur._connection.commit()
    
    async def _handle_menu(self, message: str, user_id: str, cur) -> Dict:
        """Handle main menu interactions"""
        
        # First time or returning to menu
        if message in ["menu", "start", "hi", "hello", "help"]:
            return {
                "reply": "Hello! I'm your Personal Assistant. I can help you around if you so wish for it.\n\nHow may I help you? Choose between one of the below:\n\n1️⃣ General - Chat with me about anything\n2️⃣ Task - Get things done (create groups, plan trips, etc.)",
                "extracted": []
            }
        
        # User chooses General
        if any(x in message for x in ["general", "1"]):
            await self._set_user_state(user_id, BotState.GENERAL_CHAT, {}, cur)
            return {
                "reply": "Great! I'm here to chat. Feel free to ask me anything or just have a conversation. (Type 'menu' anytime to go back)",
                "extracted": []
            }
        
        # User chooses Task
        if any(x in message for x in ["task", "2"]):
            return {
                "reply": "Perfect! Here are the tasks I can help with:\n\n1️⃣ Create Group\n2️⃣ Edit Group\n3️⃣ Plan Group Trip\n4️⃣ Add Event\n5️⃣ Plan Solo Trip\n6️⃣ Settle Debt\n\nType the number or name of the task you want.",
                "extracted": []
            }
        
        # Task selection
        task_message = message.replace("️", "").strip()  # Remove emoji modifiers
        
        if "create group" in task_message or task_message == "1":
            await self._set_user_state(user_id, BotState.CREATE_GROUP_NAME, {}, cur)
            return {"reply": "Let's create a new group! What would you like to name this group?", "extracted": []}
        
        if "edit group" in task_message or task_message == "2":
            await self._set_user_state(user_id, BotState.EDIT_GROUP_SELECT, {}, cur)
            return {"reply": "Which group would you like to edit? Please provide the group name.", "extracted": []}
        
        if "plan group trip" in task_message or task_message == "3":
            await self._set_user_state(user_id, BotState.PLAN_GROUP_TRIP_SELECT, {}, cur)
            return {"reply": "Let's plan a group trip! Which group is this trip for? Please provide the group name.", "extracted": []}
        
        if "add event" in task_message or task_message == "4":
            await self._set_user_state(user_id, BotState.ADD_EVENT_GROUP, {}, cur)
            return {"reply": "I'll help you add an event. Which group is this event for?", "extracted": []}
        
        if "plan solo trip" in task_message or task_message == "5":
            await self._set_user_state(user_id, BotState.PLAN_SOLO_TRIP_NAME, {}, cur)
            return {"reply": "Exciting! Let's plan your solo trip. What would you like to name this trip?", "extracted": []}
        
        if "settle debt" in task_message or task_message == "6":
            await self._set_user_state(user_id, BotState.SETTLE_DEBT_GROUP, {}, cur)
            return {"reply": "Let's settle a debt. Which group is this for?", "extracted": []}
        
        return {
            "reply": "I didn't quite understand. Type 'menu' to see all options.",
            "extracted": []
        }
    
    async def _handle_general_chat(self, message: str, user_id: str, cur) -> Dict:
        """Handle general conversation"""
        
        if message.lower() == "menu":
            return await self._reset_to_menu(user_id, cur)
        
        # Simple conversational responses
        # TODO: Integrate with Gemini/GPT API here
        responses = [
            "That's interesting! Tell me more.",
            "I see. How does that make you feel?",
            "Fascinating! What else would you like to discuss?",
            "That's a great point. Anything else on your mind?"
        ]
        
        import random
        return {
            "reply": random.choice(responses) + "\n\n(Type 'menu' to return to main menu)",
            "extracted": []
        }
    
    async def _handle_create_group(self, message: str, state: BotState, data: Dict, user_id: str, cur) -> Dict:
        """Handle group creation flow"""
        
        message_clean = message.strip()
        
        if message_clean.lower() in ["menu", "cancel"]:
            return await self._reset_to_menu(user_id, cur)
        
        if state == BotState.CREATE_GROUP_NAME:
            # Validate group name uniqueness
            await cur.execute("SELECT * FROM `Group` WHERE group_name = %s", (message_clean,))
            if await cur.fetchone():
                return {"reply": "❌ That group name is already taken. Please choose another name:", "extracted": []}
            
            data["group_name"] = message_clean
            await self._set_user_state(user_id, BotState.CREATE_GROUP_MEMBERS, data, cur)
            return {"reply": f"Great! Group '{message_clean}' it is.\n\nNow, who should be members of this group? Please provide usernames separated by commas (e.g., user1, user2, user3)", "extracted": []}
        
        elif state == BotState.PLAN_SOLO_TRIP_CONFIRM:
            if message_clean.lower() == "confirm":
                await self._set_user_state(user_id, BotState.MENU, {}, cur)
                return {
                    "reply": f"✅ Solo trip '{data['trip_name']}' will be created! Visit /plan-solo-trip page to complete with exact destinations.\n\nType 'menu' for more.",
                    "action": "redirect_trip_planning",
                    "data": {"userId": user_id, "isSolo": True},
                    "extracted": []
                }
            else:
                return await self._reset_to_menu(user_id, cur)
        
        return {"reply": "Error. Type 'menu'.", "extracted": []}
    
    async def _handle_settle_debt(self, message: str, state: BotState, data: Dict, user_id: str, cur) -> Dict:
        """Handle debt settlement"""
        
        message_clean = message.strip()
        
        if message_clean.lower() in ["menu", "cancel"]:
            return await self._reset_to_menu(user_id, cur)
        
        if state == BotState.SETTLE_DEBT_GROUP:
            # Check group exists
            await cur.execute("SELECT * FROM `Group` WHERE group_name = %s", (message_clean,))
            if not await cur.fetchone():
                return {"reply": "❌ Group not found. Try again or type 'menu':", "extracted": []}
            
            data["group_name"] = message_clean
            await self._set_user_state(user_id, BotState.SETTLE_DEBT_EVENT, data, cur)
            
            # Show events in this group
            await cur.execute("SELECT event_name FROM Event WHERE group_name = %s", (message_clean,))
            events = await cur.fetchall()
            
            if not events:
                return {"reply": f"No events found in group '{message_clean}'.\n\nType 'menu' to return.", "extracted": []}
            
            event_list = "\n".join([f"• {e['event_name']}" for e in events])
            return {"reply": f"Events in '{message_clean}':\n\n{event_list}\n\nWhich event?", "extracted": []}
        
        elif state == BotState.SETTLE_DEBT_EVENT:
            # Check event exists
            await cur.execute(
                "SELECT * FROM Event WHERE group_name = %s AND event_name = %s",
                (data["group_name"], message_clean)
            )
            if not await cur.fetchone():
                return {"reply": "❌ Event not found. Try again:", "extracted": []}
            
            data["event_name"] = message_clean
            await self._set_user_state(user_id, BotState.SETTLE_DEBT_TRANSACTION, data, cur)
            
            # Show unpaid transactions
            await cur.execute(
                """
                SELECT t.transaction_id, t.amount, t.owed_by, t.owed_to, t.reason, t.timestamp,
                       u1.first_name as owed_by_first, u1.last_name as owed_by_last,
                       u2.first_name as owed_to_first, u2.last_name as owed_to_last
                FROM Transaction t
                JOIN User u1 ON t.owed_by = u1.username
                JOIN User u2 ON t.owed_to = u2.username
                WHERE t.group_name = %s AND t.event_name = %s AND t.is_paid = 0
                """,
                (data["group_name"], message_clean)
            )
            transactions = await cur.fetchall()
            
            if not transactions:
                return {"reply": f"No unpaid transactions in '{message_clean}'.\n\nType 'menu' to return.", "extracted": []}
            
            # Filter transactions where user is involved
            user_transactions = [
                t for t in transactions 
                if t['owed_by'] == user_id or t['owed_to'] == user_id
            ]
            
            if not user_transactions:
                return {"reply": f"You have no pending transactions in this event.\n\nType 'menu' to return.", "extracted": []}
            
            txn_list = []
            for i, t in enumerate(user_transactions, 1):
                txn_list.append(
                    f"{i}. ₹{t['amount']} - {t['owed_by_first']} {t['owed_by_last']} → {t['owed_to_first']} {t['owed_to_last']}\n   Reason: {t['reason']}"
                )
            
            data["transactions"] = user_transactions
            
            return {
                "reply": f"Your pending transactions:\n\n" + "\n\n".join(txn_list) + f"\n\nType the number to settle (1-{len(user_transactions)}):",
                "extracted": []
            }
        
        elif state == BotState.SETTLE_DEBT_TRANSACTION:
            try:
                choice = int(message_clean)
                if choice < 1 or choice > len(data["transactions"]):
                    return {"reply": f"❌ Invalid choice. Enter 1-{len(data['transactions'])}:", "extracted": []}
                
                txn = data["transactions"][choice - 1]
                
                # Generate receipt upload URL
                receipt_url = f"/receipt_upload?groupName={data['group_name']}&eventName={data['event_name']}&timestamp={txn['timestamp']}&owedBy={txn['owed_by']}&owedTo={txn['owed_to']}"
                
                await self._set_user_state(user_id, BotState.MENU, {}, cur)
                
                return {
                    "reply": f"✅ Please upload receipt for:\n\n₹{txn['amount']} - {txn['reason']}\n\nClick the link to upload receipt and mark as paid.\n\nType 'menu' when done.",
                    "action": "open_receipt_upload",
                    "data": {"url": receipt_url},
                    "extracted": []
                }
            except ValueError:
                return {"reply": "❌ Please enter a number:", "extracted": []}
        
        return {"reply": "Error. Type 'menu'.", "extracted": []}
    
    async def _reset_to_menu(self, user_id: str, cur) -> Dict:
        """Reset user to main menu"""
        await self._set_user_state(user_id, BotState.MENU, {}, cur)
        return {
            "reply": "Returning to menu...\n\nHow may I help you? Choose between:\n\n1️⃣ General\n2️⃣ Task",
            "extracted": []
        }
    
    async def _handle_edit_group(self, message: str, state: BotState, data: Dict, user_id: str, cur) -> Dict:
        """Handle group editing flow"""
        
        message_clean = message.strip()
        
        if message_clean.lower() in ["menu", "cancel"]:
            return await self._reset_to_menu(user_id, cur)
        
        if state == BotState.EDIT_GROUP_SELECT:
            # Check if group exists and user is creator
            await cur.execute(
                "SELECT * FROM `Group` WHERE group_name = %s AND created_by = %s",
                (message_clean, user_id)
            )
            group = await cur.fetchone()
            
            if not group:
                return {"reply": "❌ Group not found or you're not the creator. Please try again or type 'menu':", "extracted": []}
            
            data["group_name"] = message_clean
            await self._set_user_state(user_id, BotState.EDIT_GROUP_CHOICE, data, cur)
            return {
                "reply": f"Editing group '{message_clean}'. What would you like to edit?\n\n1️⃣ Group Name\n2️⃣ Members",
                "extracted": []
            }
        
        elif state == BotState.EDIT_GROUP_CHOICE:
            choice = message_clean.lower().replace("️", "").strip()
            if "name" in choice or choice == "1":
                await self._set_user_state(user_id, BotState.EDIT_GROUP_NAME, data, cur)
                return {"reply": "What should the new name be?", "extracted": []}
            elif "member" in choice or choice == "2":
                await self._set_user_state(user_id, BotState.EDIT_GROUP_MEMBERS, data, cur)
                return {"reply": "Please provide the updated list of members (comma-separated usernames):", "extracted": []}
            else:
                return {"reply": "Please choose '1' for Name or '2' for Members:", "extracted": []}
        
        elif state == BotState.EDIT_GROUP_NAME:
            # Check new name availability
            await cur.execute("SELECT * FROM `Group` WHERE group_name = %s", (message_clean,))
            if await cur.fetchone():
                return {"reply": "❌ That name is taken. Choose another:", "extracted": []}
            
            try:
                # Update group name (this is tricky with foreign keys, might need to be handled differently)
                await cur.execute(
                    "UPDATE `Group` SET group_name = %s WHERE group_name = %s AND created_by = %s",
                    (message_clean, data["group_name"], user_id)
                )
                await cur._connection.commit()
                
                await self._set_user_state(user_id, BotState.MENU, {}, cur)
                return {"reply": f"✅ Group renamed to '{message_clean}'!\n\nType 'menu' for more options.", "extracted": []}
            except Exception as e:
                return {"reply": f"❌ Error: {str(e)}\n\nType 'menu' to return.", "extracted": []}
        
        elif state == BotState.EDIT_GROUP_MEMBERS:
            members = [m.strip() for m in message_clean.split(",") if m.strip()]
            
            # Validate members
            invalid = []
            for member in members:
                await cur.execute("SELECT username FROM User WHERE username = %s", (member,))
                if not await cur.fetchone():
                    invalid.append(member)
            
            if invalid:
                return {"reply": f"❌ Invalid users: {', '.join(invalid)}\n\nPlease try again:", "extracted": []}
            
            try:
                # Delete old members
                await cur.execute(
                    "DELETE FROM GroupMember WHERE group_name = %s",
                    (data["group_name"],)
                )
                
                # Add new members
                if user_id not in members:
                    members.append(user_id)
                
                for member in members:
                    await cur.execute(
                        "INSERT INTO GroupMember (group_name, user_id) VALUES (%s, %s)",
                        (data["group_name"], member)
                    )
                
                await cur._connection.commit()
                
                await self._set_user_state(user_id, BotState.MENU, {}, cur)
                return {"reply": f"✅ Members updated!\n\nType 'menu' for more.", "extracted": []}
            except Exception as e:
                return {"reply": f"❌ Error: {str(e)}\n\nType 'menu'.", "extracted": []}
        
        return {"reply": "Error. Type 'menu'.", "extracted": []}
    
    async def _handle_plan_group_trip(self, message: str, state: BotState, data: Dict, user_id: str, cur) -> Dict:
        """Handle group trip planning"""
        
        message_clean = message.strip()
        
        if message_clean.lower() in ["menu", "cancel"]:
            return await self._reset_to_menu(user_id, cur)
        
        if state == BotState.PLAN_GROUP_TRIP_SELECT:
            # Verify group exists
            await cur.execute("SELECT * FROM `Group` WHERE group_name = %s", (message_clean,))
            if not await cur.fetchone():
                return {"reply": "❌ Group not found. Try again or type 'menu':", "extracted": []}
            
            data["group_name"] = message_clean
            await self._set_user_state(user_id, BotState.PLAN_GROUP_TRIP_NAME, data, cur)
            return {"reply": "What should we name this trip?", "extracted": []}
        
        elif state == BotState.PLAN_GROUP_TRIP_NAME:
            data["trip_name"] = message_clean
            await self._set_user_state(user_id, BotState.PLAN_GROUP_TRIP_CITIES, data, cur)
            return {"reply": "Great! Now list the cities you want to visit (comma-separated, e.g., Paris, London, Rome):", "extracted": []}
        
        elif state == BotState.PLAN_GROUP_TRIP_CITIES:
            cities = [c.strip() for c in message_clean.split(",") if c.strip()]
            if len(cities) < 2:
                return {"reply": "❌ Please provide at least 2 cities:", "extracted": []}
            
            data["cities"] = cities
            await self._set_user_state(user_id, BotState.PLAN_GROUP_TRIP_CLASS, data, cur)
            return {"reply": "What travel class? Type:\n• economy\n• business\n• first", "extracted": []}
        
        elif state == BotState.PLAN_GROUP_TRIP_CLASS:
            travel_class = message_clean.lower() if message_clean.lower() in ["economy", "business", "first"] else "economy"
            data["travel_class"] = travel_class
            
            await self._set_user_state(user_id, BotState.PLAN_GROUP_TRIP_CONFIRM, data, cur)
            return {
                "reply": f"📋 Trip Summary:\n\nTrip: {data['trip_name']}\nGroup: {data['group_name']}\nCities: {', '.join(data['cities'])}\nClass: {travel_class}\n\nType 'confirm' to create or 'cancel'.",
                "extracted": []
            }
        
        elif state == BotState.PLAN_GROUP_TRIP_CONFIRM:
            if message_clean.lower() == "confirm":
                await self._set_user_state(user_id, BotState.MENU, {}, cur)
                return {
                    "reply": f"✅ Trip '{data['trip_name']}' will be created! You can visit /plan-group-trip page to complete the planning with exact destinations.\n\nType 'menu' for more.",
                    "action": "redirect_trip_planning",
                    "data": {"groupName": data["group_name"], "userId": user_id},
                    "extracted": []
                }
            else:
                return await self._reset_to_menu(user_id, cur)
        
        return {"reply": "Error. Type 'menu'.", "extracted": []}
    
    async def _handle_add_event(self, message: str, state: BotState, data: Dict, user_id: str, cur) -> Dict:
        """Handle event addition"""
        
        message_clean = message.strip()
        
        if message_clean.lower() in ["menu", "cancel"]:
            return await self._reset_to_menu(user_id, cur)
        
        if state == BotState.ADD_EVENT_GROUP:
            # Check group exists
            await cur.execute("SELECT * FROM `Group` WHERE group_name = %s", (message_clean,))
            if not await cur.fetchone():
                return {"reply": "❌ Group not found. Try again or type 'menu':", "extracted": []}
            
            data["group_name"] = message_clean
            await self._set_user_state(user_id, BotState.ADD_EVENT_NAME, data, cur)
            return {"reply": "What's the event name?", "extracted": []}
        
        elif state == BotState.ADD_EVENT_NAME:
            # Check unique event name
            await cur.execute(
                "SELECT * FROM Event WHERE group_name = %s AND event_name = %s",
                (data["group_name"], message_clean)
            )
            if await cur.fetchone():
                return {"reply": "❌ Event name must be unique. Choose another:", "extracted": []}
            
            data["event_name"] = message_clean
            await self._set_user_state(user_id, BotState.ADD_EVENT_DESCRIPTION, data, cur)
            return {"reply": "Provide a brief description (or type 'skip'):", "extracted": []}
        
        elif state == BotState.ADD_EVENT_DESCRIPTION:
            data["description"] = "" if message_clean.lower() == "skip" else message_clean
            await self._set_user_state(user_id, BotState.ADD_EVENT_AMOUNT, data, cur)
            return {"reply": "What's the amount?", "extracted": []}
        
        elif state == BotState.ADD_EVENT_AMOUNT:
            try:
                amount = float(message_clean)
                data["amount"] = amount
                await self._set_user_state(user_id, BotState.ADD_EVENT_OWED_BY, data, cur)
                return {"reply": "Who owes this money? (username)", "extracted": []}
            except:
                return {"reply": "❌ Invalid amount. Please enter a number:", "extracted": []}
        
        elif state == BotState.ADD_EVENT_OWED_BY:
            await cur.execute("SELECT username FROM User WHERE username = %s", (message_clean,))
            if not await cur.fetchone():
                return {"reply": "❌ User not found. Try again:", "extracted": []}
            
            data["owed_by"] = message_clean
            await self._set_user_state(user_id, BotState.ADD_EVENT_OWED_TO, data, cur)
            return {"reply": "Who should receive this money? (username)", "extracted": []}
        
        elif state == BotState.ADD_EVENT_OWED_TO:
            await cur.execute("SELECT username FROM User WHERE username = %s", (message_clean,))
            if not await cur.fetchone():
                return {"reply": "❌ User not found. Try again:", "extracted": []}
            
            if message_clean == data["owed_by"]:
                return {"reply": "❌ Users can't owe themselves! Try again:", "extracted": []}
            
            data["owed_to"] = message_clean
            await self._set_user_state(user_id, BotState.ADD_EVENT_REASON, data, cur)
            return {"reply": "What's the reason for this transaction?", "extracted": []}
        
        elif state == BotState.ADD_EVENT_REASON:
            data["reason"] = message_clean
            await self._set_user_state(user_id, BotState.ADD_EVENT_CONFIRM, data, cur)
            return {
                "reply": f"📋 Event Summary:\n\nGroup: {data['group_name']}\nEvent: {data['event_name']}\nDescription: {data.get('description', 'N/A')}\nAmount: {data['amount']}\n{data['owed_by']} owes {data['owed_to']}\nReason: {data['reason']}\n\nType 'confirm' or 'cancel'.",
                "extracted": []
            }
        
        elif state == BotState.ADD_EVENT_CONFIRM:
            if message_clean.lower() == "confirm":
                try:
                    # Create event
                    await cur.execute(
                        "INSERT INTO Event (group_name, event_name, created_by, description, duration) VALUES (%s, %s, %s, %s, %s)",
                        (data["group_name"], data["event_name"], user_id, data.get("description", ""), "N/A")
                    )
                    
                    # Create transaction
                    await cur.execute(
                        "INSERT INTO Transaction (group_name, event_name, created_by, owed_by, owed_to, amount, reason, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (data["group_name"], data["event_name"], user_id, data["owed_by"], data["owed_to"], data["amount"], data["reason"], datetime.now())
                    )
                    
                    await cur._connection.commit()
                    
                    await self._set_user_state(user_id, BotState.MENU, {}, cur)
                    return {"reply": "✅ Event created successfully!\n\nType 'menu' for more.", "extracted": []}
                except Exception as e:
                    return {"reply": f"❌ Error: {str(e)}\n\nType 'menu'.", "extracted": []}
            else:
                return await self._reset_to_menu(user_id, cur)
        
        return {"reply": "Error. Type 'menu'.", "extracted": []}
    
    async def _handle_plan_solo_trip(self, message: str, state: BotState, data: Dict, user_id: str, cur) -> Dict:
        """Handle solo trip planning"""
        
        message_clean = message.strip()
        
        if message_clean.lower() in ["menu", "cancel"]:
            return await self._reset_to_menu(user_id, cur)
        
        if state == BotState.PLAN_SOLO_TRIP_NAME:
            data["trip_name"] = message_clean
            await self._set_user_state(user_id, BotState.PLAN_SOLO_TRIP_CITIES, data, cur)
            return {"reply": "List the cities you want to visit (comma-separated, e.g., Tokyo, Seoul, Bangkok):", "extracted": []}
        
        elif state == BotState.PLAN_SOLO_TRIP_CITIES:
            cities = [c.strip() for c in message_clean.split(",") if c.strip()]
            if len(cities) < 2:
                return {"reply": "❌ Please provide at least 2 cities:", "extracted": []}
            
            data["cities"] = cities
            await self._set_user_state(user_id, BotState.PLAN_SOLO_TRIP_CLASS, data, cur)
            return {"reply": "What travel class? Type:\n• economy\n• business\n• first", "extracted": []}
        
        elif state == BotState.PLAN_SOLO_TRIP_CLASS:
            travel_class = message_clean.lower() if message_clean.lower() in ["economy", "business", "first"] else "economy"
            data["travel_class"] = travel_class
            
            await self._set_user_state(user_id, BotState.PLAN_SOLO_TRIP_CONFIRM, data, cur)
            return {
                "reply": f"📋 Solo Trip Summary:\n\nTrip: {data['trip_name']}\nCities: {', '.join(data['cities'])}\nClass: {travel_class}\n\nType 'confirm' or 'cancel'.",
                "extracted": []
            }
        
        elif state == BotState.CREATE_GROUP_MEMBERS:
            members = [m.strip() for m in message_clean.split(",") if m.strip()]
            
            if not members:
                return {"reply": "Please provide at least one member:", "extracted": []}
            
            # Validate all members exist
            invalid_members = []
            for member in members:
                await cur.execute("SELECT username FROM User WHERE username = %s", (member,))
                if not await cur.fetchone():
                    invalid_members.append(member)
            
            if invalid_members:
                return {"reply": f"❌ These users don't exist: {', '.join(invalid_members)}\n\nPlease provide valid usernames:", "extracted": []}
            
            data["members"] = members
            await self._set_user_state(user_id, BotState.CREATE_GROUP_DURATION, data, cur)
            return {"reply": "Perfect! How long is this group for? (e.g., '1 week', '1 month', or type 'skip')", "extracted": []}
        
        elif state == BotState.CREATE_GROUP_DURATION:
            duration = "" if message_clean.lower() == "skip" else message_clean
            data["duration"] = duration
            
            await self._set_user_state(user_id, BotState.CREATE_GROUP_CONFIRM, data, cur)
            return {
                "reply": f"📋 Summary:\n\nGroup Name: {data['group_name']}\nMembers: {', '.join(data['members'])}\nDuration: {duration or 'Not specified'}\n\nType 'confirm' to create this group or 'cancel' to abort.",
                "extracted": []
            }
        
        elif state == BotState.CREATE_GROUP_CONFIRM:
            if message_clean.lower() == "confirm":
                # Create the group
                try:
                    await cur.execute(
                        "INSERT INTO `Group` (group_name, created_by, duration) VALUES (%s, %s, %s)",
                        (data["group_name"], user_id, data.get("duration", ""))
                    )
                    
                    # Add creator if not in members
                    members = data["members"]
                    if user_id not in members:
                        members.append(user_id)
                    
                    # Add all members
                    for member in members:
                        await cur.execute(
                            "INSERT INTO GroupMember (group_name, user_id) VALUES (%s, %s)",
                            (data["group_name"], member)
                        )
                    
                    await cur._connection.commit()
                    
                    await self._set_user_state(user_id, BotState.MENU, {}, cur)
                    return {
                        "reply": f"✅ Group '{data['group_name']}' created successfully!\n\nType 'menu' to see what else I can help with.",
                        "extracted": []
                    }
                except Exception as e:
                    return {"reply": f"❌ Error creating group: {str(e)}\n\nType 'menu' to return.", "extracted": []}
            else:
                return await self._reset_to_menu(user_id, cur)
        
        return {"reply": "Something went wrong. Type 'menu' to start over.", "extracted": []}