"""Import every model module so Base.metadata is fully populated for Alembic
autogenerate and so SQLAlchemy can resolve string-based relationship()s."""

from app.models.audit import AuditLog
from app.models.base import Base
from app.models.chat import Conversation, ConversationParticipant, Message
from app.models.exercise import Exercise
from app.models.gym_class import ClassBooking, GymClass
from app.models.gym_info import FAQ, ContactRequest, Feedback, GymOpeningHours, GymRule, GymSettings
from app.models.membership import MembershipPlan, MembershipSubscription
from app.models.notification import DeviceToken, Notification
from app.models.profiles import MemberProfile, TrainerMemberAssignment, TrainerProfile
from app.models.progress import Achievement, BodyMeasurement, MemberAchievement, PersonalRecord, ProgressPhoto
from app.models.promotion import Promotion, PromotionCategory, PromotionMembershipPlan, PromotionProduct
from app.models.store import (
    CartItem,
    InventoryMovement,
    Product,
    ProductCategory,
    ProductImage,
    ShoppingCart,
    StoreOrder,
    StoreOrderItem,
)
from app.models.tracking import MealEntry, NutritionGoal, WaterEntry, WaterGoal
from app.models.user import PasswordResetToken, RefreshSession, User
from app.models.workout import (
    WorkoutDay,
    WorkoutExercise,
    WorkoutProgram,
    WorkoutSession,
    WorkoutSetLog,
)

__all__ = [
    "Base",
    "User",
    "RefreshSession",
    "PasswordResetToken",
    "MemberProfile",
    "TrainerProfile",
    "TrainerMemberAssignment",
    "MembershipPlan",
    "MembershipSubscription",
    "Exercise",
    "WorkoutProgram",
    "WorkoutDay",
    "WorkoutExercise",
    "WorkoutSession",
    "WorkoutSetLog",
    "BodyMeasurement",
    "ProgressPhoto",
    "PersonalRecord",
    "Achievement",
    "MemberAchievement",
    "GymClass",
    "ClassBooking",
    "Conversation",
    "ConversationParticipant",
    "Message",
    "Notification",
    "DeviceToken",
    "WaterGoal",
    "WaterEntry",
    "NutritionGoal",
    "MealEntry",
    "ProductCategory",
    "Product",
    "ProductImage",
    "InventoryMovement",
    "ShoppingCart",
    "CartItem",
    "StoreOrder",
    "StoreOrderItem",
    "Promotion",
    "PromotionProduct",
    "PromotionCategory",
    "PromotionMembershipPlan",
    "GymSettings",
    "GymOpeningHours",
    "GymRule",
    "FAQ",
    "ContactRequest",
    "Feedback",
    "AuditLog",
]
