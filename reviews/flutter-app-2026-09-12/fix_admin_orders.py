from pathlib import Path

root = Path('C:/Users/ahmad/Desktop/Gym_App/gym_app')
model = root / 'lib/features/admin/data/models/admin_order_model.dart'
model.write_text('''import 'package:gym_app/features/store/data/models/order_model.dart';

/// Identity needed to fulfil an order, without the member's health profile.
class AdminOrderMember {
  const AdminOrderMember({required this.id, required this.fullName, required this.memberCode});
  final String id;
  final String fullName;
  final String memberCode;

  factory AdminOrderMember.fromJson(Map<String, dynamic> json) => AdminOrderMember(
    id: json['id'] as String,
    fullName: json['full_name'] as String,
    memberCode: json['member_code'] as String,
  );
}

class AdminOrder {
  final StoreOrder order;
  final AdminOrderMember? member;

  const AdminOrder({required this.order, required this.member});

  String get memberName => member?.fullName.trim().isNotEmpty == true
      ? member!.fullName : 'Member name unavailable';

  factory AdminOrder.fromJson(Map<String, dynamic> json) => AdminOrder(
    order: StoreOrder.fromJson(json),
    member: json['member'] is Map
        ? AdminOrderMember.fromJson(Map.from(json['member'] as Map))
        : null,
  );
}
''', encoding='utf-8', newline='\n')

path = root / 'lib/features/admin/presentation/screens/admin_orders_screen.dart'
s = path.read_text(encoding='utf-8')
s = s.replace("import 'package:intl/intl.dart';", "import 'package:intl/intl.dart';\nimport 'package:gym_app/features/store/presentation/screens/order_detail_screen.dart';")
s = s.replace('return BlocBuilder<AdminOrdersBloc, AdminOrdersState>(', '''return BlocConsumer<AdminOrdersBloc, AdminOrdersState>(
      listenWhen: (previous, current) => current is AdminOrdersLoaded && current.actionError != null &&
          (previous is! AdminOrdersLoaded || previous.actionError != current.actionError),
      listener: (context, state) => ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text((state as AdminOrdersLoaded).actionError!)),
      ),''')
s = s.replace('    final bloc = context.read<AdminOrdersBloc>();\n    return AppCard(', '''    final bloc = context.read<AdminOrdersBloc>();
    void openOrder() => Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => OrderDetailScreen(
        orderId: order.id, customerName: item.memberName, memberCode: item.member?.memberCode,
      ),
    ));
    return AppCard(
      onTap: openOrder,''')
s = s.replace('item.member?.fullName ?? order.memberId,', 'item.memberName,')
s = s.replace('''                    Text(
                      DateFormat.yMMMd()''', '''                    if (item.member != null) Text(item.member!.memberCode, style: theme.textTheme.bodySmall),
                    Text(
                      DateFormat.yMMMd()''')
s = s.replace('''              Text(formatMoney(order.total), style: theme.textTheme.titleSmall),''', '''              Flexible(child: Text(formatMoney(order.total), textAlign: TextAlign.end, style: theme.textTheme.titleSmall)),''')
s = s.replace('''              if (order.paymentStatus != PaymentStatus.paid)''', '''              TextButton.icon(
                onPressed: openOrder,
                icon: const Icon(Icons.receipt_long_outlined),
                label: Text('View items (${order.items.length})'),
              ),
              if (order.paymentStatus != PaymentStatus.paid)''')
path.write_text(s, encoding='utf-8', newline='\n')
