"""Conversation state management for booking sessions"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from models import (
    ConversationState,
    ConversationMessage,
    SearchCriteria,
    Hotel,
    Room,
    BookingDraft
)

class ConversationManager:
    """Manages conversation state and booking flow"""
    
    def __init__(self, session_timeout_minutes: int = 5):
        self._sessions: Dict[str, ConversationState] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.max_history = 10
    
    def create_session(self, session_id: str) -> ConversationState:
        """Create a new conversation session"""
        state = ConversationState(
            session_id=session_id,
            stage="searching",
            created_at=datetime.now().isoformat()
        )
        self._sessions[session_id] = state
        return state
    
    def get_session(self, session_id: str) -> Optional[ConversationState]:
        """Get existing session or None if expired/not found"""
        state = self._sessions.get(session_id)
        
        if not state:
            return None
        
        # Check if session expired
        created_at = datetime.fromisoformat(state.created_at)
        if datetime.now() - created_at > self.session_timeout:
            del self._sessions[session_id]
            return None
        
        return state
    
    def get_or_create_session(self, session_id: str) -> ConversationState:
        """Get existing session or create new one"""
        state = self.get_session(session_id)
        if not state:
            state = self.create_session(session_id)
        return state
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> None:
        """Add message to conversation history"""
        state = self.get_or_create_session(session_id)
        
        message = ConversationMessage(
            role=role,  # type: ignore
            content=content,
            timestamp=datetime.now().isoformat()
        )
        
        state.conversation_history.append(message)
        
        # Keep only last N messages
        if len(state.conversation_history) > self.max_history:
            state.conversation_history = state.conversation_history[-self.max_history:]
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """Get conversation history as list of dicts for Bedrock"""
        state = self.get_session(session_id)
        if not state:
            return []
        
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in state.conversation_history
        ]
    
    def update_stage(self, session_id: str, stage: str) -> None:
        """Update conversation stage"""
        state = self.get_or_create_session(session_id)
        state.stage = stage  # type: ignore
    
    def get_stage(self, session_id: str) -> str:
        """Get current conversation stage"""
        state = self.get_or_create_session(session_id)
        return state.stage
    
    def update_search_criteria(
        self,
        session_id: str,
        location: Optional[str] = None,
        check_in_date: Optional[str] = None,
        check_out_date: Optional[str] = None,
        guest_count: Optional[int] = None
    ) -> None:
        """Update search criteria"""
        state = self.get_or_create_session(session_id)
        
        if not state.search_criteria:
            state.search_criteria = SearchCriteria()
        
        if location:
            state.search_criteria.location = location
        if check_in_date:
            state.search_criteria.check_in_date = check_in_date
        if check_out_date:
            state.search_criteria.check_out_date = check_out_date
        if guest_count:
            state.search_criteria.guest_count = guest_count
    
    def set_selected_hotel(self, session_id: str, hotel: Hotel) -> None:
        """Set selected hotel and transition to viewing stage"""
        state = self.get_or_create_session(session_id)
        state.selected_hotel = hotel
        state.stage = "viewing"
    
    def set_selected_room(self, session_id: str, room: Room) -> None:
        """Set selected room and initialize booking draft"""
        state = self.get_or_create_session(session_id)
        state.selected_room = room
        state.stage = "booking"
        
        # Initialize booking draft
        if state.selected_hotel and state.search_criteria:
            state.booking_draft = BookingDraft(
                hotel=state.selected_hotel,
                room=room,
                check_in_date=state.search_criteria.check_in_date or "",
                check_out_date=state.search_criteria.check_out_date or "",
                guest_count=state.search_criteria.guest_count or 1
            )
    
    def update_booking_draft(
        self,
        session_id: str,
        guest_names: Optional[List[str]] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        terms_accepted: Optional[bool] = None
    ) -> None:
        """Update booking draft with collected information"""
        state = self.get_or_create_session(session_id)
        
        if not state.booking_draft:
            return
        
        if guest_names is not None:
            state.booking_draft.guest_names = guest_names
        if email is not None:
            state.booking_draft.email = email
        if phone is not None:
            state.booking_draft.phone = phone
        if terms_accepted is not None:
            state.booking_draft.terms_accepted = terms_accepted
    
    def is_booking_draft_complete(self, session_id: str) -> bool:
        """Check if booking draft has all required information"""
        state = self.get_session(session_id)
        if not state or not state.booking_draft:
            return False
        
        draft = state.booking_draft
        return (
            len(draft.guest_names) > 0 and
            draft.email is not None and
            draft.phone is not None and
            draft.terms_accepted and
            draft.check_in_date != "" and
            draft.check_out_date != ""
        )
    
    def complete_booking(self, session_id: str) -> None:
        """Mark booking as confirmed and transition to confirmed stage"""
        state = self.get_or_create_session(session_id)
        state.stage = "confirmed"
        state.booking_draft = None
    
    def clear_session(self, session_id: str) -> None:
        """Clear session data"""
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def reset_to_search(self, session_id: str) -> None:
        """Reset conversation back to search stage"""
        state = self.get_or_create_session(session_id)
        state.stage = "searching"
        state.selected_hotel = None
        state.selected_room = None
        state.booking_draft = None
