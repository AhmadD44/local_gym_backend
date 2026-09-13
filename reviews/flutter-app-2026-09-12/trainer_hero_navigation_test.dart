import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gym_app/core/auth/user_role.dart';
import 'package:gym_app/core/theme/app_theme.dart';
import 'package:gym_app/features/chat/presentation/bloc/conversations_bloc.dart';
import 'package:gym_app/features/chat/presentation/screens/conversations_screen.dart';
import 'package:gym_app/features/exercises/presentation/bloc/exercises_bloc.dart';
import 'package:gym_app/features/exercises/presentation/screens/exercises_screen.dart';
import 'package:gym_app/features/profile/data/models/member_profile_model.dart';
import 'package:gym_app/features/trainers/domain/usecases/trainer_profile_usecases.dart';
import 'package:gym_app/features/trainers/presentation/bloc/trainer_programs_bloc.dart';
import 'package:gym_app/features/trainers/presentation/screens/trainer_programs_screen.dart';
import 'package:gym_app/features/workouts/domain/usecases/workouts_usecases.dart';

import 'support/chat_fakes.dart' show FakeConversationsBloc;
import 'support/navigation_test_app.dart';
import 'support/trainer_fakes.dart';
import 'support/workouts_fakes.dart';

class LoadedProgramsBloc extends TrainerProgramsBloc {
  LoadedProgramsBloc()
    : super(
        getMyMembersUseCase: GetMyMembersUseCase(repo: NoopTrainersRepo()),
        getMemberProgramsUseCase: GetMemberProgramsUseCase(repo: NoopWorkoutsRepo()),
      ) {
    emit(TrainerProgramsLoaded(members: [MemberProfile.fromJson({
      'id': 'member-1', 'user_id': 'user-1', 'full_name': 'Member One', 'member_code': 'M001',
    })], entries: const []));
  }
}

void main() {
  for (final mode in [ThemeMode.light, ThemeMode.dark]) {
    testWidgets('retained trainer buttons allow Exercises push/pop in ${mode.name}', (tester) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final navigator = GlobalKey<NavigatorState>();
      await tester.pumpWidget(MaterialApp(
        navigatorKey: navigator, theme: AppTheme.light, darkTheme: AppTheme.dark, themeMode: mode,
        home: Scaffold(body: IndexedStack(index: 1, children: [
          TrainerProgramsScreen(bloc: LoadedProgramsBloc()),
          ConversationsScreen(embedded: true, bloc: FakeConversationsBloc(
            const ConversationsLoaded(conversations: []),
          )),
        ])),
      ));
      await tester.pumpAndSettle();
      unawaited(navigator.currentState!.push(MaterialPageRoute<void>(builder: (_) => ExercisesScreen(
        canManage: true, bloc: FakeExercisesBloc(const ExercisesLoaded(exercises: [])),
      ))));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(find.text('Exercises'), findsOneWidget);
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();
      expect(find.byType(TextFormField), findsWidgets);
      expect(tester.takeException(), isNull);
      navigator.currentState!.pop();
      await tester.pumpAndSettle();
      navigator.currentState!.pop();
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(find.text('New message'), findsOneWidget);
    });
  }

  testWidgets('only selected shell tab enables Hero animations', (tester) async {
    await tester.pumpWidget(const NavigationTestApp(role: UserRole.trainer));
    await tester.pumpAndSettle();
    for (final tab in ['programs', 'messages']) {
      await tester.tap(find.byKey(ValueKey('nav-$tab')));
      await tester.pumpAndSettle();
    }
    final stack = tester.widget<IndexedStack>(find.byType(IndexedStack));
    for (var i = 0; i < stack.children.length; i++) {
      final ticker = stack.children[i] as TickerMode;
      expect(ticker.child, isA<HeroMode>());
      expect((ticker.child as HeroMode).enabled, i == stack.index);
    }
    expect(tester.takeException(), isNull);
  });
}
