"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-06

"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE difficulty_level AS ENUM ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')")
    op.execute("CREATE TYPE discount_type AS ENUM ('PERCENTAGE', 'FIXED')")
    op.execute("CREATE TYPE user_role AS ENUM ('ADMIN', 'TRAINER', 'MEMBER')")
    op.execute("CREATE TYPE device_platform AS ENUM ('ANDROID', 'IOS', 'WEB')")
    op.execute("CREATE TYPE fitness_level AS ENUM ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')")
    op.execute("CREATE TYPE notification_type AS ENUM ('MEMBERSHIP', 'WORKOUT_ASSIGNED', 'CLASS_REMINDER', 'NEW_MESSAGE', 'PROMOTION', 'ORDER_UPDATE', 'SYSTEM')")
    op.execute("CREATE TYPE contact_status AS ENUM ('OPEN', 'IN_PROGRESS', 'RESOLVED')")
    op.execute("CREATE TYPE inventory_reason AS ENUM ('RESTOCK', 'SALE', 'ORDER_CANCELLED', 'ADJUSTMENT', 'DAMAGED')")
    op.execute("CREATE TYPE meal_type AS ENUM ('BREAKFAST', 'LUNCH', 'DINNER', 'SNACK')")
    op.execute("CREATE TYPE membership_status AS ENUM ('PENDING', 'ACTIVE', 'EXPIRED', 'CANCELLED', 'SUSPENDED')")
    op.execute("CREATE TYPE payment_status AS ENUM ('PENDING', 'PAID', 'CANCELLED', 'REFUNDED')")
    op.execute("CREATE TYPE order_status AS ENUM ('PENDING', 'CONFIRMED', 'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED')")
    op.execute("CREATE TYPE class_booking_status AS ENUM ('BOOKED', 'CANCELLED', 'ATTENDED')")
    op.execute("CREATE TYPE workout_session_status AS ENUM ('SCHEDULED', 'COMPLETED', 'SKIPPED')")

    op.execute("""
CREATE TABLE achievements (
	name VARCHAR(150) NOT NULL, 
	description TEXT, 
	icon VARCHAR(500), 
	criteria TEXT, 
	id UUID NOT NULL, 
	PRIMARY KEY (id)
)
""")
    op.execute("""
CREATE TABLE conversations (
	last_message_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
)
""")
    op.execute("""
CREATE TABLE exercises (
	name VARCHAR(150) NOT NULL, 
	description TEXT, 
	muscle_group VARCHAR(100), 
	equipment VARCHAR(150), 
	difficulty difficulty_level, 
	instructions TEXT, 
	media_url VARCHAR(500), 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
)
""")
    op.execute("""CREATE INDEX ix_exercises_muscle_group ON exercises (muscle_group)""")
    op.execute("""CREATE INDEX ix_exercises_is_active ON exercises (is_active)""")
    op.execute("""CREATE INDEX ix_exercises_name ON exercises (name)""")
    op.execute("""
CREATE TABLE faqs (
	question VARCHAR(500) NOT NULL, 
	answer TEXT NOT NULL, 
	order_index INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id)
)
""")
    op.execute("""
CREATE TABLE gym_opening_hours (
	day_of_week SMALLINT NOT NULL, 
	open_time TIME WITHOUT TIME ZONE, 
	close_time TIME WITHOUT TIME ZONE, 
	is_closed BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (day_of_week)
)
""")
    op.execute("""
CREATE TABLE gym_rules (
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	order_index INTEGER NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id)
)
""")
    op.execute("""
CREATE TABLE gym_settings (
	name VARCHAR(150) NOT NULL, 
	description TEXT, 
	phone VARCHAR(30), 
	email VARCHAR(255), 
	address TEXT, 
	logo_url VARCHAR(500), 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
)
""")
    op.execute("""
CREATE TABLE membership_plans (
	name VARCHAR(150) NOT NULL, 
	description TEXT, 
	duration_days INTEGER NOT NULL, 
	price NUMERIC(10, 2) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
)
""")
    op.execute("""CREATE INDEX ix_membership_plans_is_active ON membership_plans (is_active)""")
    op.execute("""
CREATE TABLE product_categories (
	name VARCHAR(150) NOT NULL, 
	description TEXT, 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)
""")
    op.execute("""CREATE INDEX ix_product_categories_is_active ON product_categories (is_active)""")
    op.execute("""
CREATE TABLE promotions (
	name VARCHAR(150) NOT NULL, 
	description TEXT, 
	discount_type discount_type NOT NULL, 
	discount_value NUMERIC(10, 2) NOT NULL, 
	start_date TIMESTAMP WITH TIME ZONE NOT NULL, 
	end_date TIMESTAMP WITH TIME ZONE NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	stack_priority INTEGER NOT NULL, 
	combinable BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
)
""")
    op.execute("""CREATE INDEX ix_promotions_is_active ON promotions (is_active)""")
    op.execute("""CREATE INDEX ix_promotions_end_date ON promotions (end_date)""")
    op.execute("""
CREATE TABLE users (
	email VARCHAR(255) NOT NULL, 
	hashed_password VARCHAR(255) NOT NULL, 
	role user_role NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	is_email_verified BOOLEAN NOT NULL, 
	last_login_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
)
""")
    op.execute("""CREATE INDEX ix_users_role ON users (role)""")
    op.execute("""CREATE UNIQUE INDEX ix_users_email ON users (email)""")
    op.execute("""
CREATE TABLE audit_logs (
	actor_id UUID, 
	action VARCHAR(100) NOT NULL, 
	entity_type VARCHAR(100) NOT NULL, 
	entity_id VARCHAR(64), 
	before JSONB, 
	after JSONB, 
	ip_address VARCHAR(64), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL
)
""")
    op.execute("""CREATE INDEX ix_audit_logs_action ON audit_logs (action)""")
    op.execute("""CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at)""")
    op.execute("""CREATE INDEX ix_audit_logs_entity_type ON audit_logs (entity_type)""")
    op.execute("""CREATE INDEX ix_audit_logs_actor_id ON audit_logs (actor_id)""")
    op.execute("""
CREATE TABLE conversation_participants (
	conversation_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	last_read_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_conversation_user UNIQUE (conversation_id, user_id), 
	FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_conversation_participants_user_id ON conversation_participants (user_id)""")
    op.execute("""CREATE INDEX ix_conversation_participants_conversation_id ON conversation_participants (conversation_id)""")
    op.execute("""
CREATE TABLE device_tokens (
	user_id UUID NOT NULL, 
	token VARCHAR(500) NOT NULL, 
	platform device_platform NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_device_token UNIQUE (user_id, token), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_device_tokens_user_id ON device_tokens (user_id)""")
    op.execute("""
CREATE TABLE member_profiles (
	user_id UUID NOT NULL, 
	full_name VARCHAR(150) NOT NULL, 
	photo_url VARCHAR(500), 
	date_of_birth DATE, 
	phone VARCHAR(30), 
	height_cm FLOAT, 
	weight_kg FLOAT, 
	fitness_level fitness_level, 
	fitness_goal VARCHAR(500), 
	member_code VARCHAR(20) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (member_code)
)
""")
    op.execute("""
CREATE TABLE messages (
	conversation_id UUID NOT NULL, 
	sender_id UUID NOT NULL, 
	content TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE, 
	FOREIGN KEY(sender_id) REFERENCES users (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_messages_created_at ON messages (created_at)""")
    op.execute("""CREATE INDEX ix_messages_conversation_id ON messages (conversation_id)""")
    op.execute("""
CREATE TABLE notifications (
	user_id UUID NOT NULL, 
	type notification_type NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	body TEXT NOT NULL, 
	data JSONB, 
	read_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_notifications_created_at ON notifications (created_at)""")
    op.execute("""CREATE INDEX ix_notifications_user_id ON notifications (user_id)""")
    op.execute("""
CREATE TABLE password_reset_tokens (
	user_id UUID NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	used BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (token_hash)
)
""")
    op.execute("""CREATE INDEX ix_password_reset_tokens_user_id ON password_reset_tokens (user_id)""")
    op.execute("""
CREATE TABLE products (
	category_id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	description TEXT, 
	price NUMERIC(10, 2) NOT NULL, 
	sku VARCHAR(64) NOT NULL, 
	stock_quantity INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_product_stock_nonnegative CHECK (stock_quantity >= 0), 
	FOREIGN KEY(category_id) REFERENCES product_categories (id) ON DELETE RESTRICT, 
	UNIQUE (sku)
)
""")
    op.execute("""CREATE INDEX ix_products_category_id ON products (category_id)""")
    op.execute("""CREATE INDEX ix_products_is_active ON products (is_active)""")
    op.execute("""
CREATE TABLE promotion_categories (
	promotion_id UUID NOT NULL, 
	category_id UUID NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(promotion_id) REFERENCES promotions (id) ON DELETE CASCADE, 
	FOREIGN KEY(category_id) REFERENCES product_categories (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_promotion_categories_category_id ON promotion_categories (category_id)""")
    op.execute("""CREATE INDEX ix_promotion_categories_promotion_id ON promotion_categories (promotion_id)""")
    op.execute("""
CREATE TABLE promotion_membership_plans (
	promotion_id UUID NOT NULL, 
	plan_id UUID NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(promotion_id) REFERENCES promotions (id) ON DELETE CASCADE, 
	FOREIGN KEY(plan_id) REFERENCES membership_plans (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_promotion_membership_plans_plan_id ON promotion_membership_plans (plan_id)""")
    op.execute("""CREATE INDEX ix_promotion_membership_plans_promotion_id ON promotion_membership_plans (promotion_id)""")
    op.execute("""
CREATE TABLE refresh_sessions (
	user_id UUID NOT NULL, 
	jti VARCHAR(64) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	family_id VARCHAR(64) NOT NULL, 
	revoked BOOLEAN NOT NULL, 
	replaced_by_jti VARCHAR(64), 
	user_agent VARCHAR(255), 
	ip_address VARCHAR(64), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_refresh_sessions_expires_at ON refresh_sessions (expires_at)""")
    op.execute("""CREATE INDEX ix_refresh_sessions_family_id ON refresh_sessions (family_id)""")
    op.execute("""CREATE INDEX ix_refresh_sessions_user_id ON refresh_sessions (user_id)""")
    op.execute("""CREATE UNIQUE INDEX ix_refresh_sessions_jti ON refresh_sessions (jti)""")
    op.execute("""CREATE INDEX ix_refresh_sessions_user_revoked ON refresh_sessions (user_id, revoked)""")
    op.execute("""
CREATE TABLE trainer_profiles (
	user_id UUID NOT NULL, 
	full_name VARCHAR(150) NOT NULL, 
	photo_url VARCHAR(500), 
	bio VARCHAR(2000), 
	specialization VARCHAR(255), 
	years_experience INTEGER, 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
""")
    op.execute("""
CREATE TABLE body_measurements (
	member_id UUID NOT NULL, 
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	weight_kg FLOAT, 
	body_fat_pct FLOAT, 
	chest_cm FLOAT, 
	waist_cm FLOAT, 
	hips_cm FLOAT, 
	arms_cm FLOAT, 
	thighs_cm FLOAT, 
	notes TEXT, 
	recorded_by UUID, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE, 
	FOREIGN KEY(recorded_by) REFERENCES users (id) ON DELETE SET NULL
)
""")
    op.execute("""CREATE INDEX ix_body_measurements_member_id ON body_measurements (member_id)""")
    op.execute("""
CREATE TABLE contact_requests (
	member_id UUID, 
	name VARCHAR(150) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	phone VARCHAR(30), 
	subject VARCHAR(200) NOT NULL, 
	message TEXT NOT NULL, 
	status contact_status NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE SET NULL
)
""")
    op.execute("""CREATE INDEX ix_contact_requests_status ON contact_requests (status)""")
    op.execute("""CREATE INDEX ix_contact_requests_member_id ON contact_requests (member_id)""")
    op.execute("""
CREATE TABLE feedback (
	member_id UUID NOT NULL, 
	rating SMALLINT NOT NULL, 
	comment TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_feedback_rating_range CHECK (rating BETWEEN 1 AND 5), 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_feedback_member_id ON feedback (member_id)""")
    op.execute("""
CREATE TABLE gym_classes (
	name VARCHAR(150) NOT NULL, 
	description TEXT, 
	trainer_id UUID NOT NULL, 
	capacity INTEGER NOT NULL, 
	location VARCHAR(150), 
	start_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	end_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(trainer_id) REFERENCES trainer_profiles (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_gym_classes_trainer_id ON gym_classes (trainer_id)""")
    op.execute("""CREATE INDEX ix_gym_classes_is_active ON gym_classes (is_active)""")
    op.execute("""CREATE INDEX ix_gym_classes_start_time ON gym_classes (start_time)""")
    op.execute("""
CREATE TABLE inventory_movements (
	product_id UUID NOT NULL, 
	change_qty INTEGER NOT NULL, 
	reason inventory_reason NOT NULL, 
	reference_type VARCHAR(50), 
	reference_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
)
""")
    op.execute("""CREATE INDEX ix_inventory_movements_product_id ON inventory_movements (product_id)""")
    op.execute("""CREATE INDEX ix_inventory_movements_created_at ON inventory_movements (created_at)""")
    op.execute("""
CREATE TABLE meal_entries (
	member_id UUID NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	meal_type meal_type NOT NULL, 
	calories FLOAT, 
	protein_g FLOAT, 
	carbs_g FLOAT, 
	fat_g FLOAT, 
	logged_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_meal_entries_member_id ON meal_entries (member_id)""")
    op.execute("""CREATE INDEX ix_meal_entries_logged_at ON meal_entries (logged_at)""")
    op.execute("""
CREATE TABLE member_achievements (
	member_id UUID NOT NULL, 
	achievement_id UUID NOT NULL, 
	achieved_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_member_achievement UNIQUE (member_id, achievement_id), 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE, 
	FOREIGN KEY(achievement_id) REFERENCES achievements (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_member_achievements_member_id ON member_achievements (member_id)""")
    op.execute("""
CREATE TABLE membership_subscriptions (
	member_id UUID NOT NULL, 
	plan_id UUID NOT NULL, 
	status membership_status NOT NULL, 
	payment_status payment_status NOT NULL, 
	price_at_purchase NUMERIC(10, 2) NOT NULL, 
	start_date DATE, 
	expiry_date DATE, 
	confirmed_by UUID, 
	confirmed_at TIMESTAMP WITH TIME ZONE, 
	cancelled_at TIMESTAMP WITH TIME ZONE, 
	notes TEXT, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE, 
	FOREIGN KEY(plan_id) REFERENCES membership_plans (id) ON DELETE RESTRICT, 
	FOREIGN KEY(confirmed_by) REFERENCES users (id) ON DELETE SET NULL
)
""")
    op.execute("""CREATE INDEX ix_membership_subscriptions_status ON membership_subscriptions (status)""")
    op.execute("""CREATE INDEX ix_membership_subscriptions_expiry_date ON membership_subscriptions (expiry_date)""")
    op.execute("""CREATE UNIQUE INDEX uq_one_open_subscription_per_member ON membership_subscriptions (member_id) WHERE status IN ('PENDING', 'ACTIVE')""")
    op.execute("""CREATE INDEX ix_membership_subscriptions_member_id ON membership_subscriptions (member_id)""")
    op.execute("""CREATE INDEX ix_membership_subscriptions_payment_status ON membership_subscriptions (payment_status)""")
    op.execute("""
CREATE TABLE nutrition_goals (
	member_id UUID NOT NULL, 
	daily_calories FLOAT, 
	protein_g FLOAT, 
	carbs_g FLOAT, 
	fat_g FLOAT, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (member_id), 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE
)
""")
    op.execute("""
CREATE TABLE personal_records (
	member_id UUID NOT NULL, 
	exercise_id UUID NOT NULL, 
	value FLOAT NOT NULL, 
	unit VARCHAR(20) NOT NULL, 
	achieved_at DATE NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE, 
	FOREIGN KEY(exercise_id) REFERENCES exercises (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_personal_records_member_id ON personal_records (member_id)""")
    op.execute("""
CREATE TABLE product_images (
	product_id UUID NOT NULL, 
	url VARCHAR(500) NOT NULL, 
	order_index INTEGER NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_product_images_product_id ON product_images (product_id)""")
    op.execute("""
CREATE TABLE progress_photos (
	member_id UUID NOT NULL, 
	photo_url VARCHAR(500) NOT NULL, 
	taken_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	notes TEXT, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_progress_photos_member_id ON progress_photos (member_id)""")
    op.execute("""
CREATE TABLE promotion_products (
	promotion_id UUID NOT NULL, 
	product_id UUID NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(promotion_id) REFERENCES promotions (id) ON DELETE CASCADE, 
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_promotion_products_promotion_id ON promotion_products (promotion_id)""")
    op.execute("""CREATE INDEX ix_promotion_products_product_id ON promotion_products (product_id)""")
    op.execute("""
CREATE TABLE shopping_carts (
	member_id UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (member_id), 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE
)
""")
    op.execute("""
CREATE TABLE store_orders (
	member_id UUID NOT NULL, 
	status order_status NOT NULL, 
	payment_status payment_status NOT NULL, 
	subtotal NUMERIC(10, 2) NOT NULL, 
	discount_total NUMERIC(10, 2) NOT NULL, 
	total NUMERIC(10, 2) NOT NULL, 
	delivery_address TEXT NOT NULL, 
	phone VARCHAR(30) NOT NULL, 
	notes TEXT, 
	confirmed_by UUID, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE, 
	FOREIGN KEY(confirmed_by) REFERENCES users (id) ON DELETE SET NULL
)
""")
    op.execute("""CREATE INDEX ix_store_orders_status ON store_orders (status)""")
    op.execute("""CREATE INDEX ix_store_orders_member_id ON store_orders (member_id)""")
    op.execute("""
CREATE TABLE trainer_member_assignments (
	trainer_id UUID NOT NULL, 
	member_id UUID NOT NULL, 
	active BOOLEAN NOT NULL, 
	assigned_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	unassigned_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(trainer_id) REFERENCES trainer_profiles (id) ON DELETE CASCADE, 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE UNIQUE INDEX uq_active_assignment_per_member ON trainer_member_assignments (member_id) WHERE active = true""")
    op.execute("""CREATE INDEX ix_trainer_member_assignments_member_id ON trainer_member_assignments (member_id)""")
    op.execute("""CREATE INDEX ix_trainer_member_assignments_trainer_id ON trainer_member_assignments (trainer_id)""")
    op.execute("""
CREATE TABLE water_entries (
	member_id UUID NOT NULL, 
	amount_ml INTEGER NOT NULL, 
	logged_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_water_entries_logged_at ON water_entries (logged_at)""")
    op.execute("""CREATE INDEX ix_water_entries_member_id ON water_entries (member_id)""")
    op.execute("""
CREATE TABLE water_goals (
	member_id UUID NOT NULL, 
	daily_target_ml INTEGER NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (member_id), 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE
)
""")
    op.execute("""
CREATE TABLE workout_programs (
	trainer_id UUID NOT NULL, 
	member_id UUID NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	description TEXT, 
	start_date DATE, 
	end_date DATE, 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(trainer_id) REFERENCES trainer_profiles (id) ON DELETE CASCADE, 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_workout_programs_trainer_id ON workout_programs (trainer_id)""")
    op.execute("""CREATE INDEX ix_workout_programs_member_id ON workout_programs (member_id)""")
    op.execute("""
CREATE TABLE cart_items (
	cart_id UUID NOT NULL, 
	product_id UUID NOT NULL, 
	quantity INTEGER NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_cart_product UNIQUE (cart_id, product_id), 
	CONSTRAINT ck_cart_item_qty_positive CHECK (quantity > 0), 
	FOREIGN KEY(cart_id) REFERENCES shopping_carts (id) ON DELETE CASCADE, 
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_cart_items_cart_id ON cart_items (cart_id)""")
    op.execute("""
CREATE TABLE class_bookings (
	class_id UUID NOT NULL, 
	member_id UUID NOT NULL, 
	status class_booking_status NOT NULL, 
	booked_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	cancelled_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(class_id) REFERENCES gym_classes (id) ON DELETE CASCADE, 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE UNIQUE INDEX uq_one_active_booking_per_member ON class_bookings (class_id, member_id) WHERE status = 'BOOKED'""")
    op.execute("""CREATE INDEX ix_class_bookings_member_id ON class_bookings (member_id)""")
    op.execute("""CREATE INDEX ix_class_bookings_class_id ON class_bookings (class_id)""")
    op.execute("""
CREATE TABLE store_order_items (
	order_id UUID NOT NULL, 
	product_id UUID NOT NULL, 
	product_name_snapshot VARCHAR(200) NOT NULL, 
	unit_price NUMERIC(10, 2) NOT NULL, 
	quantity INTEGER NOT NULL, 
	subtotal NUMERIC(10, 2) NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES store_orders (id) ON DELETE CASCADE, 
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT
)
""")
    op.execute("""CREATE INDEX ix_store_order_items_order_id ON store_order_items (order_id)""")
    op.execute("""
CREATE TABLE workout_days (
	program_id UUID NOT NULL, 
	day_number INTEGER NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(program_id) REFERENCES workout_programs (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_workout_days_program_id ON workout_days (program_id)""")
    op.execute("""
CREATE TABLE workout_exercises (
	workout_day_id UUID NOT NULL, 
	exercise_id UUID NOT NULL, 
	sets INTEGER NOT NULL, 
	reps INTEGER NOT NULL, 
	target_weight_kg FLOAT, 
	rest_seconds INTEGER, 
	notes TEXT, 
	order_index INTEGER NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workout_day_id) REFERENCES workout_days (id) ON DELETE CASCADE, 
	FOREIGN KEY(exercise_id) REFERENCES exercises (id) ON DELETE RESTRICT
)
""")
    op.execute("""CREATE INDEX ix_workout_exercises_workout_day_id ON workout_exercises (workout_day_id)""")
    op.execute("""
CREATE TABLE workout_sessions (
	program_id UUID NOT NULL, 
	member_id UUID NOT NULL, 
	workout_day_id UUID NOT NULL, 
	scheduled_date DATE NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	status workout_session_status NOT NULL, 
	notes TEXT, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(program_id) REFERENCES workout_programs (id) ON DELETE CASCADE, 
	FOREIGN KEY(member_id) REFERENCES member_profiles (id) ON DELETE CASCADE, 
	FOREIGN KEY(workout_day_id) REFERENCES workout_days (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_workout_sessions_member_id ON workout_sessions (member_id)""")
    op.execute("""CREATE INDEX ix_workout_sessions_status ON workout_sessions (status)""")
    op.execute("""CREATE INDEX ix_workout_sessions_program_id ON workout_sessions (program_id)""")
    op.execute("""
CREATE TABLE workout_set_logs (
	session_id UUID NOT NULL, 
	workout_exercise_id UUID NOT NULL, 
	set_number INTEGER NOT NULL, 
	reps_done INTEGER, 
	weight_used_kg FLOAT, 
	completed BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES workout_sessions (id) ON DELETE CASCADE, 
	FOREIGN KEY(workout_exercise_id) REFERENCES workout_exercises (id) ON DELETE CASCADE
)
""")
    op.execute("""CREATE INDEX ix_workout_set_logs_session_id ON workout_set_logs (session_id)""")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS workout_set_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS workout_sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS workout_exercises CASCADE")
    op.execute("DROP TABLE IF EXISTS workout_days CASCADE")
    op.execute("DROP TABLE IF EXISTS store_order_items CASCADE")
    op.execute("DROP TABLE IF EXISTS class_bookings CASCADE")
    op.execute("DROP TABLE IF EXISTS cart_items CASCADE")
    op.execute("DROP TABLE IF EXISTS workout_programs CASCADE")
    op.execute("DROP TABLE IF EXISTS water_goals CASCADE")
    op.execute("DROP TABLE IF EXISTS water_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS trainer_member_assignments CASCADE")
    op.execute("DROP TABLE IF EXISTS store_orders CASCADE")
    op.execute("DROP TABLE IF EXISTS shopping_carts CASCADE")
    op.execute("DROP TABLE IF EXISTS promotion_products CASCADE")
    op.execute("DROP TABLE IF EXISTS progress_photos CASCADE")
    op.execute("DROP TABLE IF EXISTS product_images CASCADE")
    op.execute("DROP TABLE IF EXISTS personal_records CASCADE")
    op.execute("DROP TABLE IF EXISTS nutrition_goals CASCADE")
    op.execute("DROP TABLE IF EXISTS membership_subscriptions CASCADE")
    op.execute("DROP TABLE IF EXISTS member_achievements CASCADE")
    op.execute("DROP TABLE IF EXISTS meal_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS inventory_movements CASCADE")
    op.execute("DROP TABLE IF EXISTS gym_classes CASCADE")
    op.execute("DROP TABLE IF EXISTS feedback CASCADE")
    op.execute("DROP TABLE IF EXISTS contact_requests CASCADE")
    op.execute("DROP TABLE IF EXISTS body_measurements CASCADE")
    op.execute("DROP TABLE IF EXISTS trainer_profiles CASCADE")
    op.execute("DROP TABLE IF EXISTS refresh_sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS promotion_membership_plans CASCADE")
    op.execute("DROP TABLE IF EXISTS promotion_categories CASCADE")
    op.execute("DROP TABLE IF EXISTS products CASCADE")
    op.execute("DROP TABLE IF EXISTS password_reset_tokens CASCADE")
    op.execute("DROP TABLE IF EXISTS notifications CASCADE")
    op.execute("DROP TABLE IF EXISTS messages CASCADE")
    op.execute("DROP TABLE IF EXISTS member_profiles CASCADE")
    op.execute("DROP TABLE IF EXISTS device_tokens CASCADE")
    op.execute("DROP TABLE IF EXISTS conversation_participants CASCADE")
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TABLE IF EXISTS promotions CASCADE")
    op.execute("DROP TABLE IF EXISTS product_categories CASCADE")
    op.execute("DROP TABLE IF EXISTS membership_plans CASCADE")
    op.execute("DROP TABLE IF EXISTS gym_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS gym_rules CASCADE")
    op.execute("DROP TABLE IF EXISTS gym_opening_hours CASCADE")
    op.execute("DROP TABLE IF EXISTS faqs CASCADE")
    op.execute("DROP TABLE IF EXISTS exercises CASCADE")
    op.execute("DROP TABLE IF EXISTS conversations CASCADE")
    op.execute("DROP TABLE IF EXISTS achievements CASCADE")

    op.execute("DROP TYPE IF EXISTS difficulty_level")
    op.execute("DROP TYPE IF EXISTS discount_type")
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS device_platform")
    op.execute("DROP TYPE IF EXISTS fitness_level")
    op.execute("DROP TYPE IF EXISTS notification_type")
    op.execute("DROP TYPE IF EXISTS contact_status")
    op.execute("DROP TYPE IF EXISTS inventory_reason")
    op.execute("DROP TYPE IF EXISTS meal_type")
    op.execute("DROP TYPE IF EXISTS membership_status")
    op.execute("DROP TYPE IF EXISTS payment_status")
    op.execute("DROP TYPE IF EXISTS order_status")
    op.execute("DROP TYPE IF EXISTS class_booking_status")
    op.execute("DROP TYPE IF EXISTS workout_session_status")

