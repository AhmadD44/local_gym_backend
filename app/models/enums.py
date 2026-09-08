from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    TRAINER = "TRAINER"
    MEMBER = "MEMBER"


class FitnessLevel(StrEnum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class MembershipStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    SUSPENDED = "SUSPENDED"


class DifficultyLevel(StrEnum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class WorkoutSessionStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"


class ClassBookingStatus(StrEnum):
    BOOKED = "BOOKED"
    CANCELLED = "CANCELLED"
    ATTENDED = "ATTENDED"


class NotificationType(StrEnum):
    MEMBERSHIP = "MEMBERSHIP"
    WORKOUT_ASSIGNED = "WORKOUT_ASSIGNED"
    CLASS_REMINDER = "CLASS_REMINDER"
    NEW_MESSAGE = "NEW_MESSAGE"
    PROMOTION = "PROMOTION"
    ORDER_UPDATE = "ORDER_UPDATE"
    SYSTEM = "SYSTEM"


class DevicePlatform(StrEnum):
    ANDROID = "ANDROID"
    IOS = "IOS"
    WEB = "WEB"


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class DiscountType(StrEnum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"


class InventoryReason(StrEnum):
    RESTOCK = "RESTOCK"
    SALE = "SALE"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ADJUSTMENT = "ADJUSTMENT"
    DAMAGED = "DAMAGED"


class ContactStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class MealType(StrEnum):
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"
    SNACK = "SNACK"
