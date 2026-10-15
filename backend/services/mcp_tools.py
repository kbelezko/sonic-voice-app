"""MCP-compatible tool definitions and handlers for hotel booking"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from models import Hotel, Booking, SearchCriteria
from repositories import HotelRepository, BookingRepository
from services.validation import (
    DateValidationService,
    ContactValidationService,
    GuestCountValidationService,
    ValidationError
)

class MCPTools:
    """MCP tool definitions and execution handlers"""
    
    def __init__(self, hotel_repo: HotelRepository, booking_repo: BookingRepository):
        self.hotel_repo = hotel_repo
        self.booking_repo = booking_repo
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return MCP-compatible tool definitions"""
        return [
            {
                "name": "search_hotels",
                "description": "Search for available hotels based on location, dates, and guest count",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City or location to search"
                        },
                        "check_in_date": {
                            "type": "string",
                            "format": "date",
                            "description": "Check-in date (YYYY-MM-DD)"
                        },
                        "check_out_date": {
                            "type": "string",
                            "format": "date",
                            "description": "Check-out date (YYYY-MM-DD)"
                        },
                        "guest_count": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10,
                            "description": "Number of guests"
                        }
                    },
                    "required": ["location"]
                }
            },
            {
                "name": "get_hotel_details",
                "description": "Get detailed information about a specific hotel",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "hotel_id": {
                            "type": "string",
                            "description": "Unique hotel identifier"
                        }
                    },
                    "required": ["hotel_id"]
                }
            },
            {
                "name": "create_booking",
                "description": "Create a new hotel booking",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "hotel_id": {"type": "string"},
                        "room_id": {"type": "string"},
                        "check_in_date": {"type": "string", "format": "date"},
                        "check_out_date": {"type": "string", "format": "date"},
                        "guest_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1
                        },
                        "guest_count": {"type": "integer", "minimum": 1, "maximum": 10},
                        "email": {"type": "string", "format": "email"},
                        "phone": {"type": "string"}
                    },
                    "required": [
                        "hotel_id", "room_id", "check_in_date", "check_out_date",
                        "guest_names", "email", "phone"
                    ]
                }
            },
            {
                "name": "get_booking",
                "description": "Get booking details by confirmation ID",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "booking_id": {
                            "type": "string",
                            "description": "Booking confirmation ID"
                        }
                    },
                    "required": ["booking_id"]
                }
            },
            {
                "name": "cancel_booking",
                "description": "Cancel an existing booking",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "booking_id": {
                            "type": "string",
                            "description": "Booking confirmation ID to cancel"
                        }
                    },
                    "required": ["booking_id"]
                }
            }
        ]
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return results"""
        if tool_name == "search_hotels":
            return self.search_hotels(**parameters)
        elif tool_name == "get_hotel_details":
            return self.get_hotel_details(**parameters)
        elif tool_name == "create_booking":
            return self.create_booking(**parameters)
        elif tool_name == "get_booking":
            return self.get_booking(**parameters)
        elif tool_name == "cancel_booking":
            return self.cancel_booking(**parameters)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    def search_hotels(
        self,
        location: str,
        check_in_date: Optional[str] = None,
        check_out_date: Optional[str] = None,
        guest_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """Search for hotels with validation"""
        try:
            # Validate dates if provided
            if check_in_date and check_out_date:
                is_valid, error = DateValidationService.validate_date_range(
                    check_in_date, check_out_date
                )
                if not is_valid:
                    return {"error": error, "hotels": []}
            
            # Validate guest count if provided
            if guest_count:
                is_valid, error = GuestCountValidationService.validate_guest_count(guest_count)
                if not is_valid:
                    return {"error": error, "hotels": []}
            
            # Search hotels
            criteria = SearchCriteria(
                location=location,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                guest_count=guest_count
            )
            hotels = self.hotel_repo.search(criteria)
            
            if not hotels:
                return {
                    "hotels": [],
                    "count": 0,
                    "message": f"No hotels found in {location} matching your criteria"
                }
            
            return {
                "hotels": [hotel.model_dump() for hotel in hotels],
                "count": len(hotels),
                "message": f"Found {len(hotels)} hotels in {location}"
            }
        
        except Exception as e:
            return {"error": str(e), "hotels": []}
    
    def get_hotel_details(self, hotel_id: str) -> Dict[str, Any]:
        """Get detailed hotel information"""
        hotel = self.hotel_repo.get_by_id(hotel_id)
        
        if not hotel:
            return {"error": f"Hotel not found: {hotel_id}"}
        
        return {"hotel": hotel.model_dump()}
    
    def create_booking(
        self,
        hotel_id: str,
        room_id: str,
        check_in_date: str,
        check_out_date: str,
        guest_names: List[str],
        email: str,
        phone: str,
        guest_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new booking with full validation"""
        try:
            # Validate dates
            is_valid, error = DateValidationService.validate_date_range(
                check_in_date, check_out_date
            )
            if not is_valid:
                return {"error": error}
            
            # Validate email
            is_valid, error = ContactValidationService.validate_email(email)
            if not is_valid:
                return {"error": error}
            
            # Validate phone
            is_valid, error = ContactValidationService.validate_phone(phone)
            if not is_valid:
                return {"error": error}
            
            # Get hotel and room
            hotel = self.hotel_repo.get_by_id(hotel_id)
            if not hotel:
                return {"error": f"Hotel not found: {hotel_id}"}
            
            room = None
            for r in hotel.rooms:
                if r.id == room_id:
                    room = r
                    break
            
            if not room:
                return {"error": f"Room not found: {room_id}"}
            
            # Determine guest count
            actual_guest_count = guest_count if guest_count else len(guest_names)
            
            # Validate guest count
            is_valid, error = GuestCountValidationService.validate_guest_count(actual_guest_count)
            if not is_valid:
                return {"error": error}
            
            # Validate room capacity
            is_valid, error = GuestCountValidationService.validate_room_capacity(
                actual_guest_count, room.capacity
            )
            if not is_valid:
                return {"error": error}
            
            # Calculate total price
            nights = DateValidationService.calculate_nights(check_in_date, check_out_date)
            total_price = nights * room.price_per_night
            
            # Create booking
            booking = Booking(
                id="",  # Will be generated
                hotel_id=hotel_id,
                hotel_name=hotel.name,
                room_id=room_id,
                room_type=room.type,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                guest_names=guest_names,
                guest_count=actual_guest_count,
                total_price=total_price,
                price_per_night=room.price_per_night,
                status="confirmed",
                created_at=datetime.now().isoformat(),
                email=email,
                phone=phone
            )
            
            created_booking = self.booking_repo.create(booking)
            
            return {
                "success": True,
                "booking": created_booking.model_dump(),
                "message": f"Booking confirmed! Confirmation number: {created_booking.id}"
            }
        
        except Exception as e:
            return {"error": f"Booking failed: {str(e)}"}
    
    def get_booking(self, booking_id: str) -> Dict[str, Any]:
        """Retrieve booking by ID"""
        booking = self.booking_repo.get_by_id(booking_id)
        
        if not booking:
            return {"error": f"Booking not found: {booking_id}"}
        
        return {"booking": booking.model_dump()}
    
    def cancel_booking(self, booking_id: str) -> Dict[str, Any]:
        """Cancel a booking with refund calculation"""
        booking = self.booking_repo.get_by_id(booking_id)
        
        if not booking:
            return {"error": f"Booking not found: {booking_id}"}
        
        if booking.status == "cancelled":
            return {"error": "Booking is already cancelled"}
        
        # Check for late cancellation (within 24 hours of check-in)
        try:
            check_in = datetime.fromisoformat(booking.check_in_date).date()
            today = datetime.now().date()
            days_until_checkin = (check_in - today).days
            
            # Apply late cancellation penalty if within 24 hours
            if days_until_checkin < 1:
                refund_amount = booking.total_price * 0.5  # 50% penalty
                penalty_message = "Late cancellation penalty applied (50%)"
            else:
                refund_amount = booking.total_price
                penalty_message = "Full refund"
            
            # Update booking status
            self.booking_repo.update_status(booking_id, "cancelled")
            
            return {
                "success": True,
                "booking_id": booking_id,
                "status": "cancelled",
                "refund_amount": refund_amount,
                "penalty_message": penalty_message,
                "message": f"Booking {booking_id} cancelled successfully"
            }
        
        except Exception as e:
            return {"error": f"Cancellation failed: {str(e)}"}
