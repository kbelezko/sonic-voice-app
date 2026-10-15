from datetime import datetime, date
from typing import Tuple, Optional
import re

class ValidationError(Exception):
    """Custom validation error"""
    pass

class DateValidationService:
    """Service for validating dates and date ranges"""
    
    @staticmethod
    def validate_check_in_date(check_in_str: str) -> Tuple[bool, Optional[str]]:
        """Validate check-in date (must be today or future)"""
        try:
            check_in = datetime.fromisoformat(check_in_str).date()
            today = date.today()
            
            if check_in < today:
                return False, "Check-in date must be today or in the future"
            
            return True, None
        except ValueError:
            return False, "Invalid date format. Use YYYY-MM-DD"
    
    @staticmethod
    def validate_check_out_date(check_in_str: str, check_out_str: str) -> Tuple[bool, Optional[str]]:
        """Validate check-out date (must be after check-in)"""
        try:
            check_in = datetime.fromisoformat(check_in_str).date()
            check_out = datetime.fromisoformat(check_out_str).date()
            
            if check_out <= check_in:
                return False, "Check-out date must be after check-in date"
            
            return True, None
        except ValueError:
            return False, "Invalid date format. Use YYYY-MM-DD"
    
    @staticmethod
    def validate_date_range(check_in_str: str, check_out_str: str) -> Tuple[bool, Optional[str]]:
        """Validate complete date range"""
        # Validate check-in
        is_valid, error = DateValidationService.validate_check_in_date(check_in_str)
        if not is_valid:
            return False, error
        
        # Validate check-out
        is_valid, error = DateValidationService.validate_check_out_date(check_in_str, check_out_str)
        if not is_valid:
            return False, error
        
        return True, None
    
    @staticmethod
    def calculate_nights(check_in_str: str, check_out_str: str) -> int:
        """Calculate number of nights between check-in and check-out"""
        try:
            check_in = datetime.fromisoformat(check_in_str).date()
            check_out = datetime.fromisoformat(check_out_str).date()
            delta = check_out - check_in
            return delta.days
        except ValueError:
            raise ValidationError("Invalid date format")


class ContactValidationService:
    """Service for validating contact information"""
    
    # Email regex pattern (simplified but functional)
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # Phone pattern: allows digits, spaces, +, -, (, )
    PHONE_PATTERN = re.compile(r'^[\d\s\+\-\(\)]+$')
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """Validate email format"""
        if not email or email.strip() == "":
            return False, "Email is required"
        
        if not ContactValidationService.EMAIL_PATTERN.match(email):
            return False, "Invalid email format"
        
        return True, None
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
        """Validate phone format"""
        if not phone or phone.strip() == "":
            return False, "Phone number is required"
        
        if not ContactValidationService.PHONE_PATTERN.match(phone):
            return False, "Phone must contain only digits and valid formatting characters (+, -, (), spaces)"
        
        # Check minimum length
        digits_only = re.sub(r'[^\d]', '', phone)
        if len(digits_only) < 10:
            return False, "Phone number must have at least 10 digits"
        
        return True, None


class GuestCountValidationService:
    """Service for validating guest counts"""
    
    MIN_GUESTS = 1
    MAX_GUESTS = 10
    
    @staticmethod
    def validate_guest_count(guest_count: int) -> Tuple[bool, Optional[str]]:
        """Validate guest count range (1-10)"""
        if guest_count < GuestCountValidationService.MIN_GUESTS:
            return False, f"Guest count must be at least {GuestCountValidationService.MIN_GUESTS}"
        
        if guest_count > GuestCountValidationService.MAX_GUESTS:
            return False, f"Guest count cannot exceed {GuestCountValidationService.MAX_GUESTS}"
        
        return True, None
    
    @staticmethod
    def validate_room_capacity(guest_count: int, room_capacity: int) -> Tuple[bool, Optional[str]]:
        """Validate guest count against room capacity"""
        if guest_count > room_capacity:
            return False, f"Guest count ({guest_count}) exceeds room capacity ({room_capacity})"
        
        return True, None
