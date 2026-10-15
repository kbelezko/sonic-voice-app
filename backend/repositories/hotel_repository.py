from typing import List, Optional
from datetime import datetime
import uuid
from models import Hotel, Room, Review, SearchCriteria

class HotelRepository:
    """In-memory hotel repository with mock data"""
    
    def __init__(self):
        self._hotels: List[Hotel] = []
        self._initialize_mock_data()
    
    def _initialize_mock_data(self):
        """Populate repository with 20-30 static hotels"""
        
        # Helper to create reviews
        def create_reviews(hotel_id: str, count: int = 5) -> List[Review]:
            reviews = []
            comments = [
                "Amazing stay! Great location and friendly staff.",
                "Clean rooms, comfortable beds. Would recommend.",
                "Excellent amenities and beautiful views.",
                "Good value for money. Will visit again.",
                "Perfect for business travel. Quiet and professional."
            ]
            for i in range(count):
                reviews.append(Review(
                    id=str(uuid.uuid4()),
                    hotel_id=hotel_id,
                    rating=(i % 2) + 4,  # 4 or 5 stars
                    comment=comments[i % len(comments)],
                    author=f"Guest {i+1}",
                    date=f"2024-{(i % 12) + 1:02d}-15"
                ))
            return reviews
        
        # Hotel data
        hotels_data = [
            {
                "name": "Ocean View Resort",
                "location": "Miami Beach",
                "description": "Luxury beachfront resort with stunning ocean views",
                "amenities": ["WiFi", "Pool", "Spa", "Restaurant", "Beach Access", "Gym"],
                "photos": [
                    "https://example.com/ocean1.jpg",
                    "https://example.com/ocean2.jpg",
                    "https://example.com/ocean3.jpg"
                ]
            },
            {
                "name": "Mountain Lodge",
                "location": "Denver",
                "description": "Cozy mountain retreat with breathtaking views",
                "amenities": ["WiFi", "Fireplace", "Ski Storage", "Restaurant", "Gym"],
                "photos": [
                    "https://example.com/mountain1.jpg",
                    "https://example.com/mountain2.jpg",
                    "https://example.com/mountain3.jpg"
                ]
            },
            {
                "name": "City Center Hotel",
                "location": "New York",
                "description": "Modern hotel in the heart of Manhattan",
                "amenities": ["WiFi", "Business Center", "Restaurant", "Gym", "Rooftop Bar"],
                "photos": [
                    "https://example.com/city1.jpg",
                    "https://example.com/city2.jpg",
                    "https://example.com/city3.jpg",
                    "https://example.com/city4.jpg"
                ]
            },
            {
                "name": "Desert Oasis Inn",
                "location": "Phoenix",
                "description": "Southwestern charm with pool and patio",
                "amenities": ["WiFi", "Pool", "Spa", "Restaurant", "Golf Course"],
                "photos": [
                    "https://example.com/desert1.jpg",
                    "https://example.com/desert2.jpg",
                    "https://example.com/desert3.jpg"
                ]
            },
            {
                "name": "Harbor Hotel",
                "location": "San Francisco",
                "description": "Waterfront hotel with bay views",
                "amenities": ["WiFi", "Restaurant", "Bar", "Gym", "Business Center"],
                "photos": [
                    "https://example.com/harbor1.jpg",
                    "https://example.com/harbor2.jpg",
                    "https://example.com/harbor3.jpg"
                ]
            },
            {
                "name": "Garden Suites",
                "location": "Seattle",
                "description": "Boutique hotel with lush gardens",
                "amenities": ["WiFi", "Garden", "Restaurant", "Spa", "Gym"],
                "photos": [
                    "https://example.com/garden1.jpg",
                    "https://example.com/garden2.jpg",
                    "https://example.com/garden3.jpg"
                ]
            },
            {
                "name": "Skyline Tower",
                "location": "Chicago",
                "description": "Luxury high-rise with skyline views",
                "amenities": ["WiFi", "Pool", "Spa", "Restaurant", "Gym", "Concierge"],
                "photos": [
                    "https://example.com/skyline1.jpg",
                    "https://example.com/skyline2.jpg",
                    "https://example.com/skyline3.jpg"
                ]
            },
            {
                "name": "Lakeside Retreat",
                "location": "Orlando",
                "description": "Family-friendly resort near theme parks",
                "amenities": ["WiFi", "Pool", "Kids Club", "Restaurant", "Shuttle Service"],
                "photos": [
                    "https://example.com/lakeside1.jpg",
                    "https://example.com/lakeside2.jpg",
                    "https://example.com/lakeside3.jpg"
                ]
            },
            {
                "name": "Historic Inn",
                "location": "Boston",
                "description": "Charming historic hotel in downtown",
                "amenities": ["WiFi", "Restaurant", "Bar", "Business Center"],
                "photos": [
                    "https://example.com/historic1.jpg",
                    "https://example.com/historic2.jpg",
                    "https://example.com/historic3.jpg"
                ]
            },
            {
                "name": "Beachcomber Hotel",
                "location": "San Diego",
                "description": "Casual beachfront hotel with ocean access",
                "amenities": ["WiFi", "Beach Access", "Pool", "Restaurant", "Surf Rentals"],
                "photos": [
                    "https://example.com/beach1.jpg",
                    "https://example.com/beach2.jpg",
                    "https://example.com/beach3.jpg"
                ]
            },
            {
                "name": "Capitol Suites",
                "location": "Washington DC",
                "description": "Elegant suites near national monuments",
                "amenities": ["WiFi", "Business Center", "Restaurant", "Gym", "Concierge"],
                "photos": [
                    "https://example.com/capitol1.jpg",
                    "https://example.com/capitol2.jpg",
                    "https://example.com/capitol3.jpg"
                ]
            },
            {
                "name": "River Walk Inn",
                "location": "San Antonio",
                "description": "Boutique hotel on the famous River Walk",
                "amenities": ["WiFi", "Restaurant", "Bar", "River View"],
                "photos": [
                    "https://example.com/river1.jpg",
                    "https://example.com/river2.jpg",
                    "https://example.com/river3.jpg"
                ]
            },
            {
                "name": "Music City Hotel",
                "location": "Nashville",
                "description": "Vibrant hotel in the heart of downtown",
                "amenities": ["WiFi", "Live Music", "Restaurant", "Bar", "Rooftop"],
                "photos": [
                    "https://example.com/music1.jpg",
                    "https://example.com/music2.jpg",
                    "https://example.com/music3.jpg"
                ]
            },
            {
                "name": "Marina Bay Hotel",
                "location": "Miami",
                "description": "Waterfront hotel with marina access",
                "amenities": ["WiFi", "Marina", "Pool", "Restaurant", "Boat Rentals"],
                "photos": [
                    "https://example.com/marina1.jpg",
                    "https://example.com/marina2.jpg",
                    "https://example.com/marina3.jpg"
                ]
            },
            {
                "name": "Pine Forest Lodge",
                "location": "Portland",
                "description": "Rustic lodge surrounded by nature",
                "amenities": ["WiFi", "Hiking Trails", "Restaurant", "Fireplace", "Spa"],
                "photos": [
                    "https://example.com/pine1.jpg",
                    "https://example.com/pine2.jpg",
                    "https://example.com/pine3.jpg"
                ]
            },
            {
                "name": "Grand Plaza Hotel",
                "location": "Las Vegas",
                "description": "Luxurious casino resort on the Strip",
                "amenities": ["WiFi", "Casino", "Pool", "Spa", "Restaurant", "Entertainment"],
                "photos": [
                    "https://example.com/grand1.jpg",
                    "https://example.com/grand2.jpg",
                    "https://example.com/grand3.jpg",
                    "https://example.com/grand4.jpg"
                ]
            },
            {
                "name": "Coastal Inn",
                "location": "Charleston",
                "description": "Historic coastal inn with southern charm",
                "amenities": ["WiFi", "Restaurant", "Garden", "Bike Rentals"],
                "photos": [
                    "https://example.com/coastal1.jpg",
                    "https://example.com/coastal2.jpg",
                    "https://example.com/coastal3.jpg"
                ]
            },
            {
                "name": "Airport Executive Hotel",
                "location": "Atlanta",
                "description": "Convenient hotel near the airport",
                "amenities": ["WiFi", "Shuttle Service", "Business Center", "Restaurant", "Gym"],
                "photos": [
                    "https://example.com/airport1.jpg",
                    "https://example.com/airport2.jpg",
                    "https://example.com/airport3.jpg"
                ]
            },
            {
                "name": "Bayfront Resort",
                "location": "Tampa",
                "description": "Family resort with water activities",
                "amenities": ["WiFi", "Pool", "Water Park", "Restaurant", "Kids Club"],
                "photos": [
                    "https://example.com/bayfront1.jpg",
                    "https://example.com/bayfront2.jpg",
                    "https://example.com/bayfront3.jpg"
                ]
            },
            {
                "name": "Downtown Lofts",
                "location": "Austin",
                "description": "Modern lofts in the entertainment district",
                "amenities": ["WiFi", "Bar", "Restaurant", "Rooftop", "Gym"],
                "photos": [
                    "https://example.com/lofts1.jpg",
                    "https://example.com/lofts2.jpg",
                    "https://example.com/lofts3.jpg"
                ]
            },
            {
                "name": "Sunset Beach Hotel",
                "location": "Malibu",
                "description": "Beachside hotel with stunning sunsets",
                "amenities": ["WiFi", "Beach Access", "Restaurant", "Spa", "Yoga Classes"],
                "photos": [
                    "https://example.com/sunset1.jpg",
                    "https://example.com/sunset2.jpg",
                    "https://example.com/sunset3.jpg"
                ]
            },
            {
                "name": "Metropolitan Hotel",
                "location": "New York",
                "description": "Boutique hotel in trendy neighborhood",
                "amenities": ["WiFi", "Restaurant", "Bar", "Art Gallery", "Gym"],
                "photos": [
                    "https://example.com/metro1.jpg",
                    "https://example.com/metro2.jpg",
                    "https://example.com/metro3.jpg"
                ]
            },
            {
                "name": "Canyon View Resort",
                "location": "Sedona",
                "description": "Desert resort with red rock views",
                "amenities": ["WiFi", "Pool", "Spa", "Hiking", "Restaurant"],
                "photos": [
                    "https://example.com/canyon1.jpg",
                    "https://example.com/canyon2.jpg",
                    "https://example.com/canyon3.jpg"
                ]
            },
            {
                "name": "Riverfront Hotel",
                "location": "Portland",
                "description": "Modern hotel on the Willamette River",
                "amenities": ["WiFi", "Restaurant", "Gym", "Bike Rentals", "River View"],
                "photos": [
                    "https://example.com/riverfront1.jpg",
                    "https://example.com/riverfront2.jpg",
                    "https://example.com/riverfront3.jpg"
                ]
            },
            {
                "name": "Palm Springs Resort",
                "location": "Palm Springs",
                "description": "Mid-century modern resort with pool",
                "amenities": ["WiFi", "Pool", "Spa", "Golf", "Restaurant"],
                "photos": [
                    "https://example.com/palm1.jpg",
                    "https://example.com/palm2.jpg",
                    "https://example.com/palm3.jpg"
                ]
            }
        ]
        
        # Room types to assign
        room_types = [
            {"type": "Standard Single", "capacity": 1, "price": 99, "features": ["Queen Bed", "City View", "WiFi"]},
            {"type": "Standard Double", "capacity": 2, "price": 129, "features": ["Two Queen Beds", "WiFi", "Mini Fridge"]},
            {"type": "Deluxe Suite", "capacity": 4, "price": 199, "features": ["King Bed", "Sofa Bed", "Kitchenette", "Balcony"]},
            {"type": "Family Room", "capacity": 6, "price": 249, "features": ["Two Queen Beds", "Bunk Beds", "Kitchenette"]},
            {"type": "Executive Suite", "capacity": 4, "price": 299, "features": ["King Bed", "Living Room", "Work Desk", "City View"]},
            {"type": "Penthouse", "capacity": 8, "price": 499, "features": ["Master Bedroom", "Two Bathrooms", "Full Kitchen", "Terrace"]},
        ]
        
        # Create hotels
        for hotel_data in hotels_data:
            hotel_id = str(uuid.uuid4())
            
            # Create 3-4 room types per hotel
            rooms = []
            for i, room_type_data in enumerate(room_types[:4]):
                room_id = str(uuid.uuid4())
                rooms.append(Room(
                    id=room_id,
                    hotel_id=hotel_id,
                    type=room_type_data["type"],
                    capacity=room_type_data["capacity"],
                    price_per_night=float(room_type_data["price"]),
                    features=room_type_data["features"],
                    available=True
                ))
            
            # Create reviews
            reviews = create_reviews(hotel_id)
            avg_rating = sum(r.rating for r in reviews) / len(reviews)
            
            # Create hotel
            hotel = Hotel(
                id=hotel_id,
                name=hotel_data["name"],
                location=hotel_data["location"],
                description=hotel_data["description"],
                amenities=hotel_data["amenities"],
                rooms=rooms,
                photos=hotel_data["photos"],
                reviews=reviews,
                rating=round(avg_rating, 1)
            )
            
            self._hotels.append(hotel)
    
    def search(self, criteria: SearchCriteria) -> List[Hotel]:
        """Search hotels by location, dates, and guest count"""
        results = self._hotels.copy()
        
        # Filter by location (case-insensitive substring match)
        if criteria.location:
            location_lower = criteria.location.lower()
            results = [h for h in results if location_lower in h.location.lower()]
        
        # Filter by guest count (check if any room has sufficient capacity)
        if criteria.guest_count:
            results = [h for h in results if any(r.capacity >= criteria.guest_count for r in h.rooms)]
        
        # Note: Dates are not checked since all hotels are always available in mock data
        
        return results
    
    def get_by_id(self, hotel_id: str) -> Optional[Hotel]:
        """Get hotel by ID"""
        for hotel in self._hotels:
            if hotel.id == hotel_id:
                return hotel
        return None
    
    def get_all(self) -> List[Hotel]:
        """Get all hotels"""
        return self._hotels.copy()
