from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, EmailStr
import re

class Review(BaseModel):
    id: str
    hotel_id: str
    rating: int = Field(ge=1, le=5)
    comment: str
    author: str
    date: str  # ISO 8601 date

class Room(BaseModel):
    id: str
    hotel_id: str
    type: str
    capacity: int = Field(ge=1, le=10)
    price_per_night: float = Field(gt=0)
    features: List[str]
    available: bool = True

class Hotel(BaseModel):
    id: str
    name: str
    location: str
    description: str
    amenities: List[str]
    rooms: List[Room]
    photos: List[str] = Field(min_length=3)
    reviews: List[Review]
    rating: float = Field(ge=1.0, le=5.0)

class Booking(BaseModel):
    id: str  # Format: "BK-YYYYMMDD-XXXX"
    hotel_id: str
    hotel_name: str
    room_id: str
    room_type: str
    check_in_date: str  # ISO 8601 date (YYYY-MM-DD)
    check_out_date: str  # ISO 8601 date (YYYY-MM-DD)
    guest_names: List[str] = Field(min_length=1)
    guest_count: int = Field(ge=1, le=10)
    total_price: float = Field(gt=0)
    price_per_night: float = Field(gt=0)
    status: Literal["confirmed", "cancelled"] = "confirmed"
    created_at: str  # ISO 8601 timestamp
    email: EmailStr
    phone: str

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Allow digits, spaces, +, -, (, )
        if not re.match(r'^[\d\s\+\-\(\)]+$', v):
            raise ValueError('Phone must contain only digits and valid formatting characters (+, -, (), spaces)')
        return v

    @field_validator('guest_names')
    @classmethod
    def validate_guest_names(cls, v: List[str]) -> List[str]:
        for name in v:
            if len(name) > 50:
                raise ValueError('Guest names must be 50 characters or less')
        return v

class SearchCriteria(BaseModel):
    location: Optional[str] = Field(None, max_length=100)
    check_in_date: Optional[str] = None  # ISO 8601 date
    check_out_date: Optional[str] = None  # ISO 8601 date
    guest_count: Optional[int] = Field(None, ge=1, le=10)

class BookingDraft(BaseModel):
    hotel: Hotel
    room: Room
    check_in_date: str
    check_out_date: str
    guest_names: List[str] = Field(default_factory=list)
    guest_count: int
    email: Optional[str] = None
    phone: Optional[str] = None
    terms_accepted: bool = False

class ConversationMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: str  # ISO 8601 timestamp

class ConversationState(BaseModel):
    session_id: str
    stage: Literal["searching", "viewing", "booking", "confirmed"] = "searching"
    search_criteria: Optional[SearchCriteria] = None
    selected_hotel: Optional[Hotel] = None
    selected_room: Optional[Room] = None
    booking_draft: Optional[BookingDraft] = None
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    created_at: str  # ISO 8601 timestamp

# WebSocket message models
class AudioChunkMessage(BaseModel):
    type: Literal["audio_chunk"] = "audio_chunk"
    data: str  # base64 encoded audio
    format: Literal["webm"] = "webm"
    sample_rate: int

class VoiceControlMessage(BaseModel):
    type: Literal["voice_start", "voice_end"]

class TranscriptionMessage(BaseModel):
    type: Literal["transcription"] = "transcription"
    text: str
    is_final: bool

class AssistantTextMessage(BaseModel):
    type: Literal["assistant_text"] = "assistant_text"
    text: str

class AssistantVoiceMessage(BaseModel):
    type: Literal["assistant_voice"] = "assistant_voice"
    audio: str  # base64 encoded audio
    format: Literal["mp3"] = "mp3"

class ToolExecutionMessage(BaseModel):
    type: Literal["tool_execution"] = "tool_execution"
    tool_name: str
    status: Literal["executing", "completed", "failed"]

class HotelResultsMessage(BaseModel):
    type: Literal["hotel_results"] = "hotel_results"
    hotels: List[Hotel]
    count: int
    message: str

class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str
    code: str
