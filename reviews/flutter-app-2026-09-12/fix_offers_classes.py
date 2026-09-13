from pathlib import Path

root = Path('C:/Users/ahmad/Desktop/Gym_App/gym_app')
changed = []

def edit(relative, old, new, count=1):
    path = root / relative
    text = path.read_text(encoding='utf-8')
    assert text.count(old) >= count, (relative, old[:80])
    path.write_text(text.replace(old, new, count), encoding='utf-8', newline='\n')
    if relative not in changed:
        changed.append(relative)

p = 'lib/features/classes/presentation/bloc/classes_bloc.dart'
edit(p, 'getClassesUseCase.call();', 'getClassesUseCase.call(upcomingOnly: false);')
p = 'lib/features/classes/presentation/screens/classes_screen.dart'
edit(p, 'length: 2,', 'length: 3,')
edit(p, """                const TabBar(
                  tabs: [Tab(text: 'Upcoming'), Tab(text: 'My bookings')],
                ),""", """                Row(children: [
                  const Expanded(child: TabBar(
                    isScrollable: true,
                    tabAlignment: TabAlignment.start,
                    tabs: [Tab(text: 'Upcoming'), Tab(text: 'My bookings'), Tab(text: 'Past')],
                  )),
                  IconButton(
                    tooltip: 'Refresh classes',
                    onPressed: state.isProcessing ? null : () => context.read<ClassesBloc>().add(const ClassesRequested()),
                    icon: const Icon(Icons.refresh_rounded),
                  ),
                ]),""")
edit(p, '_MyBookingsTab(state: state),', '_MyBookingsTab(state: state),\n                      _UpcomingTab(state: state, past: true),')
edit(p, 'const _UpcomingTab({required this.state});\n  final ClassesLoaded state;', 'const _UpcomingTab({required this.state, this.past = false});\n  final ClassesLoaded state;\n  final bool past;')
edit(p, """    if (state.classes.isEmpty) {
      return const AppEmptyState(
        icon: Icons.calendar_month_outlined,
        title: 'No upcoming classes',
      );
    }""", """    final now = DateTime.now();
    final classes = state.classes.where((c) => c.isActive && c.startTime.isBefore(now) == past).toList();
    if (past) classes.sort((a, b) => b.startTime.compareTo(a.startTime));
    if (classes.isEmpty) {
      return AppEmptyState(
        icon: Icons.calendar_month_outlined,
        title: past ? 'No past classes' : 'No upcoming classes',
        message: past ? null : 'Earlier classes are in Past. Refresh to check for new sessions.',
      );
    }""")
edit(p, 'for (final gymClass in state.classes)', 'for (final gymClass in classes)')
edit(p, 'final canBook = !alreadyBooked && !full && !started && !isProcessing;', 'final canBook = gymClass.isActive && !alreadyBooked && !full && !started && !isProcessing;')
edit(p, "child: Text(alreadyBooked ? 'Booked' : 'Book'),", "child: Text(started ? (gymClass.endTime.isBefore(DateTime.now()) ? 'Ended' : 'Started') : alreadyBooked ? 'Booked' : 'Book'),")

p = 'lib/features/classes/presentation/screens/classes_browse_screen.dart'
edit(p, 'const ClassesBrowseScreen({super.key});', 'const ClassesBrowseScreen({super.key, this.getClasses});\n  final GetClassesUseCase? getClasses;')
edit(p, 'String? _error;', 'String? _error;\n  bool _past = false;')
edit(p, 'GetClassesUseCase(repo: createClassesRepo()).call();', '(widget.getClasses ?? GetClassesUseCase(repo: createClassesRepo())).call(upcomingOnly: false);')
edit(p, """    return Scaffold(
      appBar: AppBar(title: const Text('Classes')),""", """    final now = DateTime.now();
    final visible = (_classes ?? <GymClass>[]).where((c) => c.isActive && c.startTime.isBefore(now) == _past).toList();
    if (_past) visible.sort((a, b) => b.startTime.compareTo(a.startTime));
    return Scaffold(
      appBar: AppBar(
        title: const Text('Classes'),
        actions: [IconButton(tooltip: 'Refresh classes', onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: Padding(padding: const EdgeInsets.only(bottom: 8), child: SegmentedButton<bool>(
            segments: const [ButtonSegment(value: false, label: Text('Upcoming')), ButtonSegment(value: true, label: Text('Past'))],
            selected: {_past}, onSelectionChanged: (value) => setState(() => _past = value.single),
          )),
        ),
      ),""")
edit(p, """          : _classes!.isEmpty
          ? const AppEmptyState(
              icon: Icons.calendar_month_outlined,
              title: 'No upcoming classes',
            )""", """          : visible.isEmpty
          ? AppEmptyState(
              icon: Icons.calendar_month_outlined,
              title: _past ? 'No past classes' : 'No upcoming classes',
              message: _past ? null : 'Earlier sessions are in Past. Refresh to check for new classes.',
            )""")
edit(p, 'itemCount: _classes!.length,', 'itemCount: visible.length,')
edit(p, 'final gymClass = _classes![index];', 'final gymClass = visible[index];')

p = 'lib/features/admin/presentation/widgets/edit_class_sheet.dart'
edit(p, 'widget.gymClass?.startTime.toLocal() ?? DateTime.now();', 'widget.gymClass?.startTime.toLocal() ?? DateTime.now().add(const Duration(hours: 1));')
edit(p, 'widget.gymClass?.endTime.toLocal() ?? DateTime.now().add(const Duration(hours: 1));', 'widget.gymClass?.endTime.toLocal() ?? _startTime.add(const Duration(hours: 1));')
edit(p, 'if (time == null) return;', 'if (time == null || !mounted) return;')
edit(p, '_startTime = combined;', '_startTime = combined;\n        if (!_endTime.isAfter(combined)) _endTime = combined.add(const Duration(hours: 1));')
edit(p, """    setState(() {
      _saving = true;""", """    if (capacity < 1 || capacity > 500) {
      setState(() => _error = 'Capacity must be between 1 and 500.');
      return;
    }
    if (!_endTime.isAfter(_startTime)) {
      setState(() => _error = 'End time must be after start time.');
      return;
    }
    if (widget.gymClass == null && !_startTime.isAfter(DateTime.now())) {
      setState(() => _error = 'Choose a future start time so members can book this class.');
      return;
    }
    setState(() {
      _saving = true;""")

p = 'lib/features/admin/data/models/promotion_requests.dart'
edit(p, "/// sets are sent; the rest are omitted (not nulled). The API does not allow\n/// changing `discount_type` or the product/category/plan targets after\n/// creation — those are create-only.", "/// sets are sent; the rest are omitted. Discount type is create-only; targets can be updated.")
edit(p, '  final bool? combinable;', '  final bool? combinable;\n  final List<String>? categoryIds;\n  final List<String>? planIds;')
edit(p, '    this.isActive,', '    this.isActive,\n    this.categoryIds,\n    this.planIds,')
edit(p, "    if (isActive != null) 'is_active': isActive,", "    if (isActive != null) 'is_active': isActive,\n    if (categoryIds != null) 'category_ids': categoryIds,\n    if (planIds != null) 'plan_ids': planIds,")
p = 'lib/features/admin/presentation/widgets/edit_promotion_sheet.dart'
edit(p, """    setState(() {
      _saving = true;""", """    if (value <= Decimal.zero || ((widget.promotion?.discountType ?? _discountType) == DiscountType.percentage && value > Decimal.fromInt(100))) {
      setState(() => _error = 'Enter a positive discount. Percentages cannot exceed 100.');
      return;
    }
    if (!_endDate.isAfter(_startDate)) {
      setState(() => _error = 'End date must be after start date.');
      return;
    }
    if (_categoryIds.isEmpty && _planIds.isEmpty && (widget.promotion?.productIds.isEmpty ?? true)) {
      setState(() => _error = 'Select at least one category or membership plan.');
      return;
    }
    setState(() {
      _saving = true;""")
edit(p, """              combinable: _combinable,
            ),
          );""", """              combinable: _combinable,
              categoryIds: _categoryIds.toList(),
              planIds: _planIds.toList(),
            ),
          );""")
edit(p, 'if (isCreating) ...[', '...[', 1)
edit(p, "'Pick at least one category or plan — a promotion with no targets '\n                  'discounts nothing.'", "'Select the categories and membership plans included in this offer.'")
edit(p, """                      return Text(
                        'Unable to load categories/plans.',
                        style: TextStyle(color: colors.error),
                      );""", """                      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('Unable to load categories/plans.', style: TextStyle(color: colors.error)),
                        TextButton(onPressed: () => setState(() => _targetsFuture = _loadTargets()), child: const Text('Retry')),
                      ]);""")

p = 'lib/features/store/presentation/bloc/products_bloc.dart'
edit(p, 'final GetProductsUseCase getProductsUseCase;', 'final GetProductsUseCase getProductsUseCase;\n  final String? initialCategoryId;')
edit(p, '    required this.getProductsUseCase,', '    required this.getProductsUseCase,\n    this.initialCategoryId,')
edit(p, 'final productsResult = await getProductsUseCase.call();', 'final productsResult = await getProductsUseCase.call(categoryId: initialCategoryId);')
edit(p, 'categories: categories,', 'categories: categories,\n            selectedCategoryId: initialCategoryId,')
p = 'lib/features/store/presentation/screens/store_screen.dart'
edit(p, 'this.productsBloc, this.cartBloc});', 'this.productsBloc, this.cartBloc, this.initialCategoryId});\n  final String? initialCategoryId;')
edit(p, 'getProductsUseCase: GetProductsUseCase(repo: repo),', 'getProductsUseCase: GetProductsUseCase(repo: repo),\n                initialCategoryId: initialCategoryId,')

p = 'lib/features/membership/data/models/membership_plan_model.dart'
edit(p, 'final bool isActive;', 'final bool isActive;\n  final Decimal? effectivePrice;\n  Decimal get displayPrice => effectivePrice ?? price;\n  bool get hasDiscount => displayPrice < price;')
edit(p, 'required this.isActive,', 'required this.isActive,\n    this.effectivePrice,')
edit(p, "isActive: json['is_active'] as bool,", "isActive: json['is_active'] as bool,\n    effectivePrice: parseMoneyOrNull(json['effective_price']),")
p = 'lib/features/membership/presentation/screens/membership_screen.dart'
edit(p, 'const MembershipScreen({super.key, this.bloc});', 'const MembershipScreen({super.key, this.bloc, this.planIds});\n  final List<String>? planIds;')
edit(p, 'child: const _MembershipView(),', 'child: _MembershipView(planIds: planIds),')
edit(p, 'const _MembershipView();', 'const _MembershipView({this.planIds});\n  final List<String>? planIds;')
edit(p, "Text('Plans', style: Theme.of(context).textTheme.titleMedium),", "Text(planIds == null ? 'Plans' : 'Eligible plans', style: Theme.of(context).textTheme.titleMedium),\n                  if (planIds != null) const Text('Active offers are applied automatically when you subscribe.'),\n                  if (plans.where((p) => planIds == null || planIds!.contains(p.id)).isEmpty) const Text('No eligible plans are currently available.'),")
edit(p, '...plans.map(', '...plans.where((p) => planIds == null || planIds!.contains(p.id)).map(')
edit(p, "formatMoney(plan.price)", "formatMoney(plan.displayPrice)")
edit(p, '                const SizedBox(height: 6),', "                if (plan.hasDiscount) Text(formatMoney(plan.price), style: theme.textTheme.bodySmall?.copyWith(decoration: TextDecoration.lineThrough)),\n                const SizedBox(height: 6),")

p = 'lib/features/dashboard/presentation/screens/member_dashboard_screen.dart'
edit(p, "import 'package:flutter/material.dart';", "import 'package:flutter/material.dart';\nimport 'package:gym_app/features/promotions/presentation/screens/promotion_detail_screen.dart';")
start = root / p
text = start.read_text(encoding='utf-8')
pos = text.index('    return Container(', text.index('class _PromotionBanner'))
text = text[:pos] + '''    return TextButton.icon(
      style: TextButton.styleFrom(
        backgroundColor: colors.primaryContainer,
        foregroundColor: colors.onPrimaryContainer,
        minimumSize: const Size(48, 48),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      ),
      onPressed: () => Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => PromotionDetailScreen(promotion: promotion),
      )),
      icon: const Icon(Icons.local_offer_rounded, size: 18),
      label: Text('${promotion.name} · ${promotion.badgeLabel}'),
    );
  }
}
'''
start.write_text(text, encoding='utf-8', newline='\n')
print('\n'.join(changed))
