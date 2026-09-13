import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';

import 'package:gym_app/core/errors/failure_message.dart';
import 'package:gym_app/core/models/money.dart';
import 'package:gym_app/core/widgets/app_card.dart';
import 'package:gym_app/core/widgets/app_error_view.dart';
import 'package:gym_app/features/membership/presentation/screens/membership_screen.dart';
import 'package:gym_app/features/promotions/data/models/promotion_model.dart';
import 'package:gym_app/features/store/data/models/product_models.dart';
import 'package:gym_app/features/store/domain/usecases/store_usecases.dart';
import 'package:gym_app/features/store/presentation/bloc/cart_bloc.dart';
import 'package:gym_app/features/store/presentation/screens/cart_screen.dart';
import 'package:gym_app/features/store/presentation/screens/product_detail_screen.dart';
import 'package:gym_app/features/store/presentation/screens/store_screen.dart';
import 'package:gym_app/features/store/store_dependencies.dart';

class PromotionTargets {
  const PromotionTargets({this.categories = const [], this.products = const []});
  final List<ProductCategory> categories;
  final List<Product> products;
}

class PromotionDetailScreen extends StatefulWidget {
  const PromotionDetailScreen({super.key, required this.promotion, this.loadTargets});
  final Promotion promotion;
  final Future<PromotionTargets> Function()? loadTargets;

  @override
  State<PromotionDetailScreen> createState() => _PromotionDetailScreenState();
}

class _PromotionDetailScreenState extends State<PromotionDetailScreen> {
  late Future<PromotionTargets> _future = _load();

  Future<PromotionTargets> _load() async {
    if (widget.loadTargets != null) return widget.loadTargets!();
    final repo = createStoreRepo();
    final promotion = widget.promotion;
    final categories = promotion.categoryIds.isEmpty
        ? <ProductCategory>[]
        : (await repo.getCategories()).fold((failure) => throw failure, (items) => items)
            .where((c) => c.isActive && promotion.categoryIds.contains(c.id)).toList();
    final products = await Future.wait(promotion.productIds.map((id) async {
      final result = await repo.getProduct(id);
      return result.fold((failure) => throw failure, (product) => product);
    }));
    return PromotionTargets(categories: categories, products: products.where((p) => p.isActive).toList());
  }

  CartBloc _createCart() {
    final repo = createStoreRepo();
    return CartBloc(
      getCartUseCase: GetCartUseCase(repo: repo),
      addToCartUseCase: AddToCartUseCase(repo: repo),
      updateCartItemUseCase: UpdateCartItemUseCase(repo: repo),
      removeCartItemUseCase: RemoveCartItemUseCase(repo: repo),
      checkoutUseCase: CheckoutUseCase(repo: repo),
    )..add(const CartRequested());
  }

  @override
  Widget build(BuildContext context) {
    final promotion = widget.promotion;
    final now = DateTime.now();
    final active = promotion.isActive && !now.isBefore(promotion.startDate) && !now.isAfter(promotion.endDate);
    final hasTargets = promotion.categoryIds.isNotEmpty || promotion.productIds.isNotEmpty || promotion.planIds.isNotEmpty;
    final theme = Theme.of(context);
    return BlocProvider(create: (_) => _createCart(), child: Builder(builder: (context) => Scaffold(
      appBar: AppBar(title: const Text('Offer details'), actions: [
        if (promotion.productIds.isNotEmpty) IconButton(
          tooltip: 'Cart', icon: const Icon(Icons.shopping_cart_outlined),
          onPressed: () => Navigator.of(context).push(MaterialPageRoute(
            builder: (_) => CartScreen(cartBloc: context.read<CartBloc>()),
          )),
        ),
      ]),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        Text(promotion.badgeLabel, style: theme.textTheme.headlineLarge?.copyWith(color: theme.colorScheme.primary)),
        const SizedBox(height: 8),
        Text(promotion.name, style: theme.textTheme.headlineSmall),
        if (promotion.description?.isNotEmpty ?? false) ...[
          const SizedBox(height: 12), Text(promotion.description!),
        ],
        const SizedBox(height: 12),
        Text('${DateFormat.yMMMd().add_jm().format(promotion.startDate.toLocal())} – ${DateFormat.yMMMd().add_jm().format(promotion.endDate.toLocal())}'),
        const SizedBox(height: 20),
        AppCard(child: Text(!active ? 'This offer is not currently active.'
            : !hasTargets ? 'This offer has no eligible items yet. Please check with the gym.'
            : 'No code needed. Eligible discounts are applied automatically. Your final price is confirmed at checkout or when you subscribe.')),
        if (active && hasTargets) ...[
          const SizedBox(height: 20),
          if (promotion.planIds.isNotEmpty) FilledButton.icon(
            icon: const Icon(Icons.card_membership_outlined),
            label: const Text('View eligible membership plans'),
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(
              builder: (_) => MembershipScreen(planIds: promotion.planIds),
            )),
          ),
          if (promotion.categoryIds.isNotEmpty || promotion.productIds.isNotEmpty)
            FutureBuilder<PromotionTargets>(future: _future, builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator()));
              }
              if (snapshot.hasError) return AppErrorView(
                message: failureMessage(snapshot.error, fallback: 'Unable to load eligible items.'),
                onRetry: () => setState(() => _future = _load()),
              );
              final targets = snapshot.data!;
              return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                const SizedBox(height: 16),
                Text('Shop this offer', style: theme.textTheme.titleLarge),
                const SizedBox(height: 8),
                if (targets.categories.isEmpty && targets.products.isEmpty) const Text('No eligible products are currently available.'),
                for (final category in targets.categories) Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.shopping_bag_outlined), label: Text('Shop ${category.name}'),
                    onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => StoreScreen(initialCategoryId: category.id),
                    )),
                  ),
                ),
                for (final product in targets.products) AppCard(
                  margin: const EdgeInsets.only(bottom: 8),
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => ProductDetailScreen(product: product, cartBloc: context.read<CartBloc>()),
                  )),
                  child: Row(children: [
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(product.name, style: theme.textTheme.titleMedium),
                      Text(formatMoney(product.effectivePrice ?? product.price)),
                    ])),
                    const Icon(Icons.chevron_right_rounded),
                  ]),
                ),
              ]);
            }),
        ],
      ]),
    )));
  }
}
