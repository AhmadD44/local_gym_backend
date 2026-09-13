# Flutter app review — 12 September 2026

Reviewed project: `C:/Users/ahmad/Desktop/Gym_App/gym_app`. This is a review, with no implementation changes. The supplied API contract and the local backend were used to check integration assumptions.

## Assessment

A substantial implementation with a good foundation, but not ready for production yet. Feature separation, BLoC state management, typed models, decimal money handling, centralized theme tokens, and lazy tab initialization are strengths. The main risk is incomplete behavior across screens and failure paths, rather than missing folders or poor code organization.

Coverage included authentication/account, role navigation, member dashboard, membership, workouts/programs/exercises, classes, store/cart/orders, progress, nutrition/water, trainer features, chat/notifications, administration, and platform configuration. This was source review plus automated checks; it was not live end-to-end verification of every screen.

## Findings, in priority order

### 1. High — membership cash confirmation omits the required request body

App: `lib/features/admin/data/datasources/admin_memberships_remote_datasource.dart:69`. Backend: `app/api/v1/endpoints/memberships.py:148`.

The app posts without data. The endpoint requires `MembershipConfirmPaymentRequest`, even though its notes field is optional. This produces validation failure instead of confirming payment. Send at least an empty JSON object, or the entered notes. An isolated request-capture test confirmed that the app sends null data.

### 2. High — authentication ending does not clear pushed protected routes

App: `lib/app/app.dart:54`; `lib/features/navigation/app_drawer.dart:31`.

The auth consumer changes MaterialApp's home, but feature routes pushed onto Navigator remain above it. An isolated widget test confirmed that a protected detail screen stays visible after the underlying home changes to AuthScreen. This can leave prior account information onscreen after session expiry or sign-out. It is a UI/session isolation defect, not evidence that backend authorization can be bypassed. Reset the protected navigation stack on authentication changes.

### 3. High — image upload retry fails after access-token expiry

App: `lib/core/network/api_client.dart:88`.

The interceptor retries the same finalized FormData after refreshing the token. A simulated upload returning 401 reproduced `Bad state: The FormData has already been finalized`; the retry never reached the HTTP adapter. Clone/rebuild multipart data and its files before replay. Cover upload plus refresh in a regression test.

### 4. High — newly created promotions have no discount targets

App: `lib/features/admin/data/models/promotion_requests.dart:4`; `lib/features/admin/presentation/widgets/edit_promotion_sheet.dart`. Backend: `app/services/promotion_service.py:41` and `:112`.

The creation model/form does not send product_ids, category_ids, or plan_ids. The backend uses those associations to decide applicability; an empty target set does not mean a global promotion. A promotion can therefore be created successfully but discount nothing. Provide target selection and send the associations during creation.

### 5. High — scheduled workouts have no normal resume route

App: `lib/features/workouts/presentation/screens/program_detail_screen.dart:59`; `lib/features/dashboard/presentation/screens/member_dashboard_screen.dart:276`.

SessionDetailScreen is opened immediately after creating a schedule. The dashboard's existing scheduled workout is a display-only card; there is no other session-detail entry point in the reviewed source. Leaving that screen or reopening the app makes it impossible to resume through the ordinary flow without scheduling another session. Add a Start/Resume action using the existing session ID and load its workout day. Avoid opening a future scheduled workout as if it were today's session.

### 6. Medium — “log out all devices” silently ignores server failure

App: `lib/features/auth/data/repositories/account_repo.dart:39`.

The remote result is ignored, local credentials are cleared, and success is returned. An isolated test reproduced success after a remote failure. The current device can sign out locally, but the UI must not imply that other devices were revoked without server confirmation. Also review protected account calls made through the separate auth Dio client: they do not share the regular client's refresh handling.

### 7. Medium — temporary refresh failures destroy the session

App: `lib/core/network/api_client.dart:135`.

The broad catch clears stored credentials for temporary errors as well as invalid refresh tokens. A simulated 503 confirmed deletion of the refresh token. Distinguish definite invalid-session responses from retryable failures, accounting for refresh-token rotation when a response is lost.

### 8. Medium — cart errors are invisible

App: `lib/features/store/presentation/screens/cart_screen.dart:48`.

Every state other than CartLoaded renders a spinner, including CartError. An isolated widget test confirmed the spinner and absence of error text. CartLoaded.actionError is also not presented, so checkout failures such as stock rejection lack feedback. Add explicit load-error/retry and action-error displays, preserving entered checkout information.

### 9. Medium — chat lacks asynchronous error/disconnect recovery

App: `lib/features/chat/presentation/bloc/chat_room_bloc.dart:67`; `lib/features/chat/data/datasources/chat_socket_service.dart:24`.

The subscription handles data only, while the service forwards stream errors and closes on disconnect. The surrounding try/catch does not handle later asynchronous stream errors. Add onError/onDone handling, a visible connection state, reconnect/auth recovery, and message catch-up. History is fetched once with the default page size; add cursor pagination so older messages remain accessible.

### 10. Medium — account recovery and admin account access are missing

App: `lib/features/auth/presentation/screens/auth_screen.dart`; `lib/features/navigation/app_drawer.dart`.

The supplied contract includes working forgot-password and reset-password endpoints, but the app has no corresponding recovery flow. Admin navigation also has no account/sign-out destination; the existing sign-out interfaces belong to member/trainer profile screens. Add account access for every role, plus email/reset-code/new-password recovery with useful error states.

### 11. Medium — the member dashboard stays stale

App: `lib/features/navigation/app_shell.dart`; dashboard dependencies and screen.

The retained tab loads its dashboard once, without a normal refresh action or mutation-driven invalidation. Completing a workout or changing membership/progress can leave home showing the old summary. Add pull-to-refresh and invalidate relevant dashboard data after successful mutations.

### 12. Release configuration needs completion

App: `ios/Runner/Info.plist`; `android/app/build.gradle.kts:24` and `:37`.

iOS has no NSPhotoLibraryUsageDescription despite gallery picking with default metadata options. The installed image_picker documentation requires this configuration. Verify gallery behavior on a real iOS device. Android still uses the example application identifier and debug signing for release. Set production identifiers, signing, display names and launcher assets before distribution.

## Design and navigation opinion

The red/black/white foundation is coherent and restrained. The actual dashboard was rendered at 390 × 844 in both themes using fixture data and loaded fonts. It reads clearly, but the uniformly rounded cards and equal emphasis make it feel like a generic dashboard more than a distinctive gym product. The three metric cards also have uneven heights. These renders are dashboard bodies in a test scaffold, not full-app screenshots or device approval.

Make today's workout the dominant element: program/day name, exercise count, and one obvious red Start/Resume button. Keep membership status compact. Use the condensed heading font more deliberately and make secondary metrics quieter. Avoid treating all weight gain as negative and all loss as positive without knowing the member's goal.

The implementation still differs from the previously agreed navigation. Recommended destinations:

| Role | Bottom navigation |
| --- | --- |
| Member | Home · Train · Classes · Shop · Progress |
| Trainer | Overview · Members · Programs · Messages |
| Admin | Overview · Members · Store · Manage |

Use the left drawer for a real account header (photo, name, role), profile, membership/account options appropriate to the role, nutrition/water, gym information, settings, and sign-out. Put notifications in a consistent top-bar entry. Keep payment/order management accessible within admin Store/Manage. The current member You tab and admin Payments/Orders tabs are still the older structure.

## Verification and limits

- `flutter analyze --no-pub`: no issues.
- Existing `flutter test --no-pub --reporter compact`: 90 tests passed.
- Six additional isolated diagnostic probes passed by reproducing the undesirable behavior described above: missing payment body, refresh-503 session deletion, multipart replay failure, false logout-all success, retained protected route, and cart-error spinner. These are evidence probes, not tests asserting correct behavior.
- Two additional dashboard render checks passed at phone size in light/dark themes. Images are saved alongside this report.
- Temporary review test files were removed from the Flutter project after use; diagnostic source is retained here. To rerun it, copy it into the app's test directory so its support imports resolve.
- Existing tests are primarily isolated/fake-backed checks. There are no admin tests in the reviewed suite. Passing them does not establish API contract compatibility or real multi-user behavior.
- No live backend transactions, real account credentials, physical-device testing, iOS build, release build, or actual push delivery were verified. The supplied backend contract says push delivery is still a stub; mobile UI alone cannot make that feature operational.

Fix the first five findings before expanding features, then exercise complete member, trainer, and admin journeys against a test backend, including token expiry, offline recovery, insufficient stock, and interrupted workouts/chat.
