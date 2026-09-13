from pathlib import Path
root = Path('C:/Users/ahmad/Desktop/Gym_App/gym_app')
def edit(p, old, new):
    path=root/p
    s=path.read_text(encoding='utf-8')
    assert old in s, (p,old[:50])
    path.write_text(s.replace(old,new,1),encoding='utf-8',newline='\n')
edit('lib/features/admin/presentation/widgets/edit_class_sheet.dart',
     'if (!_endTime.isAfter(combined))\n          _endTime = combined.add(const Duration(hours: 1));',
     'if (!_endTime.isAfter(combined)) {\n          _endTime = combined.add(const Duration(hours: 1));\n        }')
edit('lib/features/promotions/presentation/screens/promotion_detail_screen.dart',
     'if (snapshot.hasError)\n                        return AppErrorView(',
     'if (snapshot.hasError) {\n                        return AppErrorView(')
edit('lib/features/promotions/presentation/screens/promotion_detail_screen.dart',
     '                      final targets = snapshot.data!;',
     '                      }\n                      final targets = snapshot.data!;')
# Member Home retains its state between tabs, so allow a fresh offers/classes fetch.
edit('lib/features/dashboard/presentation/screens/member_dashboard_screen.dart',
     'return SingleChildScrollView(\n            child: switch (state)',
     '''return RefreshIndicator(
            onRefresh: () async {
              final bloc = context.read<DashboardBloc>();
              final completed = bloc.stream.firstWhere((s) => s is! DashboardLoading);
              bloc.add(const DashboardRequested());
              await completed;
            },
            child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            child: switch (state)''')
edit('lib/features/dashboard/presentation/screens/member_dashboard_screen.dart',
     '            },\n          );', '            },\n          ));')
