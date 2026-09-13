# FORM — Mobile app design

Open index.html in a browser. No build step or backend is required.
On desktop, use the left role selector and right screen index. On mobile, use the Demo menu at the top right.

## Design
Working brand: JHGYM. Replace with the gym's name and logo.
Red #D82828, black #111111, white #FFFFFF, neutral #F3F3F1.
Typography: Barlow Condensed (700/800) headings and Arial/Helvetica body; fonts are bundled locally.
390px mobile canvas, responsive full-screen mobile layout, minimum 44px main actions.
Native HTML forms, keyboard support, reduced motion, labelled controls.

## Included
Member: sign in/register, dashboard, training plan, set logger, session summary,
class schedule/details/book/cancel, progress/measurements/photos/records,
nutrition/goals/meal entry, water/goals/logging, trainer chat, membership card/plans,
shop/product/cart/checkout/order status, profile/settings, notifications, gym information,
contact and feedback.
Trainer: overview, assigned members, member details, program builder and chat.
Admin: overview, cash confirmation, member actions, staff account form,
class creation and order fulfilment with separate cash-payment status.

## Preview boundaries
All data is illustrative. The prototype is NOT connected to the API.
Member interactions use localStorage where implemented; browser photo previews are temporary.
No credentials are stored or sent. Do not enter real credentials or sensitive personal data.
Staff screens demonstrate primary workflows and are not a complete production admin client.
Examples use September 2026, USD prices and a placeholder Beirut gym.
Product silhouettes are editable SVG illustrations, not photographs of actual inventory.
The local gym image is illustrative stock imagery, if available.

## Backend rules preserved
- Member signup never asks for a role. Staff roles appear only in the review controls.
- Membership requests await staff cash confirmation; active members extend at reception.
- The digital member card is informational. No QR check-in or attendance controls.
- Shop checkout requests address, phone and notes; only cash on delivery.
- Product prices and discounts must come from backend effective_price/cart totals in production.
- Class full and cancellation states are represented.
- Workout set completion is submitted at session finish, not per-set API persistence.
- Password recovery offers reception contact because email delivery is not wired.
- Notifications have an in-app view; push delivery is not assumed.
- Trainer screens use assigned-member scope.
- Admin order transitions and payment confirmation follow allowed backend states.

## Implementation mapping
Source: docs/FLUTTER_API_CONTRACT.md, README.md, app/schemas/dashboard.py, app/models/enums.py.

| UI | API group |
| --- | --- |
| Auth and account | /auth/*, /members/me |
| Today | /dashboard/me, /dashboard/card |
| Training and logger | /workouts/programs/me, /workouts/programs/{id}, /workouts/sessions |
| Exercise information | /exercises |
| Classes | /classes, /classes/{id}/book, /classes/bookings/me |
| Progress | /progress/measurements, /photos, /records, /achievements |
| Nutrition and water | /nutrition/*, /water/* |
| Coach chat | /conversations/*, /ws/chat/{conversation_id} |
| Membership | /memberships/plans, /memberships/me, /memberships/subscribe |
| Shop | /store/products, /store/cart, /store/checkout, /store/orders/me |
| Notifications | /notifications |
| Gym and support | /gym/*, /faqs, /contact, /feedback |
| Coach workspace | /trainers/me/members, /workouts/programs |
| Admin workspace | /admin/dashboard, /members, /memberships/{id}/confirm-payment, /store/orders/* |

## Production follow-through
Replace sample fixtures with API models and state management; add server validation,
loading/retry/expired-session states, ownership checks, secure token storage and refresh rotation.
Resolve sample client names to actual UUIDs and expand the program builder to multiple days/exercises.
Use real gym hours, trainer media, exercise instructions, inventory images and promotion validity.
No production backend files were changed.

## Review results
31 screens rendered at 390px and 360px without horizontal overflow. Nine interaction paths checked. No browser runtime errors. See review-report.json.
Open design-overview.png for six key screens and preview-desktop.png for the desktop review layout.

## Assets
Barlow Condensed by Jeremy Tribby, distributed under SIL Open Font License; see assets/OFL.txt.
Illustrative gym photo: https://images.unsplash.com/photo-1534438327276-14e5300c3a48 (Unsplash).
