import 'package:decimal/decimal.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';

import 'package:gym_app/core/models/money.dart';
import 'package:gym_app/core/widgets/app_card.dart';
import 'package:gym_app/core/widgets/app_error_view.dart';
import 'package:gym_app/core/widgets/app_section_loading.dart';
import 'package:gym_app/core/widgets/status_tone_mapping.dart';
import 'package:gym_app/features/store/data/models/order_model.dart';
import 'package:gym_app/features/store/domain/usecases/store_usecases.dart';
import 'package:gym_app/features/store/presentation/bloc/order_detail_bloc.dart';
import 'package:gym_app/features/store/store_dependencies.dart';

class OrderDetailScreen extends StatelessWidget {
  const OrderDetailScreen({super.key, required this.orderId, this.bloc, this.customerName, this.memberCode});

  final String orderId;
  final OrderDetailBloc? bloc;
  final String? customerName;
  final String? memberCode;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Order')),
    body: BlocProvider(
      create: (_) => bloc ?? (OrderDetailBloc(getOrderUseCase: GetOrderUseCase(repo: createStoreRepo()))
        ..add(OrderDetailRequested(orderId: orderId))),
      child: BlocBuilder<OrderDetailBloc, OrderDetailState>(builder: (context, state) {
        void reload() => context.read<OrderDetailBloc>().add(OrderDetailRequested(orderId: orderId));
        return switch (state) {
          OrderDetailLoading() => const Padding(padding: EdgeInsets.all(24), child: AppSectionLoading(count: 3, height: 70)),
          OrderDetailError(:final message) => Padding(padding: const EdgeInsets.all(24), child: AppErrorView(message: message, onRetry: reload)),
          OrderDetailLoaded(:final order) => _OrderContent(order: order, customerName: customerName, memberCode: memberCode),
        };
      }),
    ),
  );
}

class _OrderContent extends StatelessWidget {
  const _OrderContent({required this.order, this.customerName, this.memberCode});
  final StoreOrder order;
  final String? customerName;
  final String? memberCode;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final quantity = order.items.fold<int>(0, (count, item) => count + item.quantity);
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        AppCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (customerName != null) ...[
            Text(customerName!, style: theme.textTheme.titleLarge),
            if (memberCode?.isNotEmpty ?? false) Text(memberCode!, style: theme.textTheme.bodySmall),
            const SizedBox(height: 12),
          ],
          Text(DateFormat.yMMMd().add_jm().format(order.createdAt.toLocal()), style: theme.textTheme.titleSmall),
          const SizedBox(height: 8),
          SelectableText('Order ${order.id}', style: theme.textTheme.bodySmall),
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: [
            statusChipFor(order.status.label, orderStatusVisual(order.status)),
            statusChipFor('Payment ${order.paymentStatus.label}', paymentStatusVisual(order.paymentStatus)),
          ]),
        ])),
        const SizedBox(height: 20),
        Text('Items', style: theme.textTheme.titleLarge),
        Text('$quantity units · ${order.items.length} product lines', style: theme.textTheme.bodySmall),
        const SizedBox(height: 8),
        if (order.items.isEmpty) const Text('No items are recorded for this order.'),
        for (final item in order.items) AppCard(
          margin: const EdgeInsets.only(bottom: 10),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text(item.productNameSnapshot, style: theme.textTheme.titleMedium),
            const SizedBox(height: 6),
            Text('Quantity: ${item.quantity}'),
            _AmountLine(label: 'Unit price', value: item.unitPrice),
            _AmountLine(label: 'Line total', value: item.subtotal, emphasize: true),
          ]),
        ),
        const SizedBox(height: 12),
        AppCard(child: Column(children: [
          _AmountLine(label: 'Subtotal', value: order.subtotal),
          if (order.discountTotal > Decimal.zero) _AmountLine(label: 'Discount', value: order.discountTotal, discount: true),
          const Divider(height: 24),
          _AmountLine(label: 'Total', value: order.total, emphasize: true),
        ])),
        const SizedBox(height: 20),
        Text('Delivery details', style: theme.textTheme.titleLarge),
        const SizedBox(height: 8),
        AppCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Address', style: theme.textTheme.labelLarge),
          SelectableText(order.deliveryAddress),
          const SizedBox(height: 12),
          Text('Phone', style: theme.textTheme.labelLarge),
          SelectableText(order.phone),
          if (order.notes?.trim().isNotEmpty ?? false) ...[
            const SizedBox(height: 12),
            Text('Notes', style: theme.textTheme.labelLarge),
            Text(order.notes!),
          ],
        ])),
      ]),
    );
  }
}

class _AmountLine extends StatelessWidget {
  const _AmountLine({required this.label, required this.value, this.emphasize = false, this.discount = false});
  final String label;
  final Decimal value;
  final bool emphasize;
  final bool discount;

  @override
  Widget build(BuildContext context) {
    final style = emphasize ? Theme.of(context).textTheme.titleMedium : Theme.of(context).textTheme.bodyMedium;
    return Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: Row(children: [
      Expanded(child: Text(label, style: style)),
      const SizedBox(width: 12),
      Flexible(child: Text('${discount ? '-' : ''}${formatMoney(value)}', textAlign: TextAlign.end, style: style)),
    ]));
  }
}
