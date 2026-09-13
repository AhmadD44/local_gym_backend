import 'package:dartz/dartz.dart' show Either, Right;
import 'package:decimal/decimal.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gym_app/core/errors/failures.dart';
import 'package:gym_app/core/models/page.dart' as models;
import 'package:gym_app/core/theme/app_theme.dart';
import 'package:gym_app/features/admin/data/models/promotion_requests.dart';
import 'package:gym_app/features/classes/data/models/class_booking_model.dart';
import 'package:gym_app/features/classes/data/models/gym_class_model.dart';
import 'package:gym_app/features/classes/domain/usecases/classes_usecases.dart';
import 'package:gym_app/features/classes/presentation/bloc/classes_bloc.dart';
import 'package:gym_app/features/classes/presentation/screens/classes_browse_screen.dart';
import 'package:gym_app/features/classes/presentation/screens/classes_screen.dart';
import 'package:gym_app/features/membership/data/models/membership_plan_model.dart';
import 'package:gym_app/features/membership/presentation/screens/membership_screen.dart';
import 'package:gym_app/features/promotions/data/models/promotion_model.dart';
import 'package:gym_app/features/promotions/presentation/screens/promotion_detail_screen.dart';
import 'package:gym_app/features/store/data/models/product_models.dart';
import 'package:gym_app/features/store/domain/usecases/store_usecases.dart';
import 'package:gym_app/features/store/presentation/bloc/products_bloc.dart';
import 'package:gym_app/features/store/presentation/screens/store_screen.dart';
import 'support/classes_fakes.dart';
import 'support/store_fakes.dart';

GymClass gymClass(String name, int days) => GymClass.fromJson({
  'id': name, 'created_at': DateTime.now().toIso8601String(), 'updated_at': DateTime.now().toIso8601String(),
  'name': name, 'trainer_id': 'trainer-1',
  'trainer': {'id': 'trainer-1', 'user_id': 'user-1', 'full_name': 'Coach Lee', 'is_active': true},
  'capacity': 20, 'start_time': DateTime.now().add(Duration(days: days)).toUtc().toIso8601String(),
  'end_time': DateTime.now().add(Duration(days: days, hours: 1)).toUtc().toIso8601String(),
  'is_active': true, 'booked_count': 1, 'available_spots': 19,
});

Promotion offer({bool expired = false, bool targeted = true}) => Promotion.fromJson({
  'id': 'offer-1', 'created_at': DateTime.now().toIso8601String(), 'updated_at': DateTime.now().toIso8601String(),
  'name': 'September member savings', 'discount_type': 'PERCENTAGE', 'discount_value': '20.00',
  'start_date': DateTime.now().subtract(const Duration(days: 3)).toIso8601String(),
  'end_date': DateTime.now().add(Duration(days: expired ? -1 : 7)).toIso8601String(),
  'is_active': true, 'stack_priority': 100, 'combinable': false,
  'category_ids': targeted ? ['category-1'] : [], 'plan_ids': targeted ? ['plan-1'] : [], 'product_ids': [],
});

class ScheduleRepo extends NoopClassesRepo {
  final flags = <bool>[];
  @override
  Future<Either<Failure, List<GymClass>>> getClasses({bool upcomingOnly = true}) async {
    flags.add(upcomingOnly);
    return Right([gymClass('Tomorrow strength', 1), gymClass('Yesterday mobility', -1)]);
  }
  @override
  Future<Either<Failure, List<ClassBooking>>> getMyBookings() async => const Right([]);
}

class CategoryRepo extends NoopStoreRepo {
  String? requestedCategory;
  @override
  Future<Either<Failure, List<ProductCategory>>> getCategories() async => const Right([]);
  @override
  Future<Either<Failure, models.Page<Product>>> getProducts({int page = 1, int pageSize = 20, String? categoryId, String? search}) async {
    requestedCategory = categoryId;
    return Right(models.Page<Product>(items: const [], page: 1, pageSize: 20, total: 0));
  }
}

Widget harness(Widget child, ThemeMode mode, {double scale = 1}) => MaterialApp(
  theme: AppTheme.light, darkTheme: AppTheme.dark, themeMode: mode,
  builder: (context, child) => MediaQuery(data: MediaQuery.of(context).copyWith(
    textScaler: TextScaler.linear(scale), disableAnimations: true,
  ), child: child!), home: Scaffold(body: child),
);

void main() {
  test('member requests past and upcoming classes', () async {
    final repo = ScheduleRepo();
    final bloc = ClassesBloc(getClassesUseCase: GetClassesUseCase(repo: repo),
      getMyBookingsUseCase: GetMyBookingsUseCase(repo: repo), bookClassUseCase: BookClassUseCase(repo: repo),
      cancelBookingUseCase: CancelBookingUseCase(repo: repo));
    final done = bloc.stream.firstWhere((s) => s is ClassesLoaded);
    bloc.add(const ClassesRequested());
    final state = await done as ClassesLoaded;
    expect(repo.flags, [false]); expect(state.classes, hasLength(2));
    await bloc.close();
  });

  test('offer category is used on the first store request', () async {
    final repo = CategoryRepo();
    final bloc = ProductsBloc(getCategoriesUseCase: GetCategoriesUseCase(repo: repo),
      getProductsUseCase: GetProductsUseCase(repo: repo), initialCategoryId: 'category-1');
    final done = bloc.stream.firstWhere((s) => s is ProductsLoaded);
    bloc.add(const ProductsRequested());
    final state = await done as ProductsLoaded;
    expect(repo.requestedCategory, 'category-1'); expect(state.selectedCategoryId, 'category-1');
    await bloc.close();
  });

  test('promotion edit includes targets and preserves omitted product links', () {
    expect(const PromotionUpdate(categoryIds: ['category-1'], planIds: []).toJson(),
      {'category_ids': ['category-1'], 'plan_ids': []});
    expect(const PromotionUpdate(name: 'Renamed').toJson().containsKey('category_ids'), isFalse);
  });

  test('membership displays server effective price with backward-compatible fallback', () {
    final json = {'id': 'plan-1', 'created_at': '2026-09-01T00:00:00Z', 'updated_at': '2026-09-01T00:00:00Z',
      'name': 'Monthly', 'duration_days': 30, 'price': '100.00', 'is_active': true};
    expect(MembershipPlan.fromJson(json).displayPrice, Decimal.fromInt(100));
    final discounted = MembershipPlan.fromJson({...json, 'effective_price': '80.00'});
    expect(discounted.displayPrice, Decimal.fromInt(80)); expect(discounted.hasDiscount, isTrue);
  });

  for (final mode in [ThemeMode.light, ThemeMode.dark]) {
    for (final width in [390.0, 320.0]) {
      testWidgets('member schedule and past booking guard ${mode.name} $width', (tester) async {
        tester.view.physicalSize = Size(width, 844); tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize); addTearDown(tester.view.resetDevicePixelRatio);
        await tester.pumpWidget(harness(ClassesScreen(bloc: FakeClassesBloc(ClassesLoaded(
          classes: [gymClass('Tomorrow strength', 1), gymClass('Yesterday mobility', -1)], bookings: const [],
        ))), mode, scale: 2));
        await tester.pumpAndSettle();
        expect(find.text('Tomorrow strength'), findsOneWidget);
        expect(find.text('Yesterday mobility'), findsNothing);
        await tester.ensureVisible(find.text('Past')); await tester.tap(find.text('Past')); await tester.pumpAndSettle();
        expect(find.text('Yesterday mobility'), findsOneWidget);
        expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Ended')).onPressed, isNull);
        expect(tester.takeException(), isNull);
      });

      testWidgets('offer actions ${mode.name} $width', (tester) async {
        tester.view.physicalSize = Size(width, 844); tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize); addTearDown(tester.view.resetDevicePixelRatio);
        await tester.pumpWidget(harness(PromotionDetailScreen(promotion: offer(), loadTargets: () async => const PromotionTargets(
          categories: [ProductCategory(id: 'category-1', name: 'Supplements', description: null, isActive: true)],
        )), mode, scale: 2));
        await tester.pumpAndSettle();
        await tester.scrollUntilVisible(find.text('Shop Supplements'), 180);
        await tester.tap(find.text('Shop Supplements')); await tester.pumpAndSettle();
        expect(tester.widget<StoreScreen>(find.byType(StoreScreen)).initialCategoryId, 'category-1');
        expect(tester.takeException(), isNull);
      });
    }
  }

  testWidgets('trainer can browse past classes and refresh', (tester) async {
    final repo = ScheduleRepo();
    await tester.pumpWidget(harness(ClassesBrowseScreen(getClasses: GetClassesUseCase(repo: repo)), ThemeMode.dark));
    await tester.pumpAndSettle(); expect(find.text('Tomorrow strength'), findsOneWidget);
    await tester.tap(find.text('Past')); await tester.pumpAndSettle();
    expect(find.text('Yesterday mobility'), findsOneWidget);
    await tester.tap(find.byTooltip('Refresh classes')); await tester.pumpAndSettle();
    expect(repo.flags, [false, false]); expect(tester.takeException(), isNull);
  });

  testWidgets('plan offer links only to its eligible plans', (tester) async {
    await tester.pumpWidget(harness(PromotionDetailScreen(promotion: offer(), loadTargets: () async => const PromotionTargets()), ThemeMode.light));
    await tester.pumpAndSettle(); await tester.tap(find.text('View eligible membership plans')); await tester.pumpAndSettle();
    expect(tester.widget<MembershipScreen>(find.byType(MembershipScreen)).planIds, ['plan-1']);
    expect(tester.takeException(), isNull);
  });

  testWidgets('expired and untargeted offers have no redemption action', (tester) async {
    for (final promotion in [offer(expired: true), offer(targeted: false)]) {
      await tester.pumpWidget(harness(PromotionDetailScreen(promotion: promotion), ThemeMode.light));
      await tester.pumpAndSettle();
      expect(find.text('View eligible membership plans'), findsNothing);
      expect(find.text('Shop this offer'), findsNothing);
    }
  });
}
