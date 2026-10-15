// Shared type definitions for hotel booking system

export interface Hotel {
  id: string;
  name: string;
  location: string;
  description: string;
  amenities: string[];
  rooms: Room[];
  photos: string[];
  reviews: Review[];
  rating: number;
}

export interface Room {
  id: string;
  hotel_id: string;
  type: string;
  capacity: number; // 1-10 guests
  price_per_night: number;
  features: string[];
  available: boolean;
}

export interface Review {
  id: string;
  hotel_id: string;
  rating: number; // 1-5
  comment: string;
  author: string;
  date: string; // ISO 8601 date
}

export interface Booking {
  id: string; // Format: "BK-YYYYMMDD-XXXX"
  hotel_id: string;
  hotel_name: string;
  room_id: string;
  room_type: string;
  check_in_date: string; // ISO 8601 date (YYYY-MM-DD)
  check_out_date: string; // ISO 8601 date (YYYY-MM-DD)
  guest_names: string[];
  guest_count: number;
  total_price: number;
  price_per_night: number;
  status: "confirmed" | "cancelled";
  created_at: string; // ISO 8601 timestamp
  email: string;
  phone: string;
}

export interface SearchCriteria {
  location?: string;
  check_in_date?: string; // ISO 8601 date
  check_out_date?: string; // ISO 8601 date
  guest_count?: number; // 1-10
}

export interface ConversationMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string; // ISO 8601 timestamp
}

// WebSocket message types
export type WebSocketMessageType =
  | "audio_chunk"
  | "voice_start"
  | "voice_end"
  | "transcription"
  | "assistant_text"
  | "assistant_voice"
  | "tool_execution"
  | "hotel_results"
  | "sonic_event"
  | "error";

export interface AudioChunkMessage {
  type: "audio_chunk";
  data: string; // base64 encoded audio
  format: "webm";
  sample_rate: number;
}

export interface VoiceControlMessage {
  type: "voice_start" | "voice_end";
}

export interface TranscriptionMessage {
  type: "transcription";
  text: string;
  is_final: boolean;
  role: "user" | "assistant";
}

export interface AssistantTextMessage {
  type: "assistant_text";
  text: string;
}

export interface AssistantVoiceMessage {
  type: "assistant_voice";
  audio: string; // base64 encoded audio
  format: "mp3";
}

export interface ToolExecutionMessage {
  type: "tool_execution";
  tool_name: string;
  status: "executing" | "completed" | "failed";
}

export interface HotelResultsMessage {
  type: "hotel_results";
  hotels: Hotel[];
  count: number;
  message: string;
}

export interface ErrorMessage {
  type: "error";
  message: string;
  code: string;
}

export interface SonicEventMessage {
  type: "sonic_event";
  event_type: string;
  data: Record<string, unknown>;
}

export type WebSocketMessage =
  | AudioChunkMessage
  | VoiceControlMessage
  | TranscriptionMessage
  | AssistantTextMessage
  | AssistantVoiceMessage
  | ToolExecutionMessage
  | HotelResultsMessage
  | SonicEventMessage
  | ErrorMessage;

// Voice button states
export type VoiceButtonState = "inactive" | "listening" | "processing";

// Connection status
export type ConnectionStatus = "disconnected" | "connecting" | "connected" | "reconnecting" | "error";

// A single Nova Sonic technical event forwarded to the events panel
export interface SonicEvent {
  event_type: string;
  data: Record<string, unknown>;
  ts: string; // ISO timestamp added on the frontend
}
