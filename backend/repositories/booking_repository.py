from typing import Dict, List, Optional
from datetime import datetime
import uuid
import random
import string
from models import Booking

class BookingRepository:
    """In-memory booking repository"""
    
    def __init__(self):
        self._bookings: Dict[str, Booking] = {}
    
    def _generate_confirmation_id(self) -> str:
        """Generate unique confirmation ID in format BK-YYYYMMDD-XXXX"""
        date_str = datetime.now().strftime("%Y%m%d")
        # Generate random 4-character alphanumeric code
        random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        confirmation_id = f"BK-{date_str}-{random_code}"
        
        # Ensure uniqueness
        while confirmation_id in self._bookings:
            random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            confirmation_id = f"BK-{date_str}-{random_code}"
        
        return confirmation_id
    
    def create(self, booking: Booking) -> Booking:
        """Create a new booking with generated confirmation ID"""
        # Generate confirmation ID if not provided
        if not booking.id or booking.id == "":
            booking.id = self._generate_confirmation_id()
        
        # Set created_at timestamp
        if not booking.created_at:
            booking.created_at = datetime.now().isoformat()
        
        # Store booking
        self._bookings[booking.id] = booking
        return booking
    
    def get_by_id(self, booking_id: str) -> Optional[Booking]:
        """Retrieve booking by ID"""
        return self._bookings.get(booking_id)
    
    def update_status(self, booking_id: str, status: str) -> Optional[Booking]:
        """Update booking status (confirmed → cancelled)"""
        booking = self._bookings.get(booking_id)
        if booking:
            booking.status = status  # type: ignore
            return booking
        return None
    
    def get_all(self, status: Optional[str] = None) -> List[Booking]:
        """Get all bookings, optionally filtered by status"""
        bookings = list(self._bookings.values())
        if status:
            bookings = [b for b in bookings if b.status == status]
        return bookings
    
    def get_by_email(self, email: str) -> List[Booking]:
        """Get all bookings for a specific email"""
        return [b for b in self._bookings.values() if b.email == email]
