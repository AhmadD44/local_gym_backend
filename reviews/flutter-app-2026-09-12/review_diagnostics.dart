// Diagnostic probes: these assertions document observed bugs, not desired behavior.
// Run a temporary copy in gym_app/test to resolve its existing test-support imports.
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:dartz/dartz.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gym_app/app/app.dart';
import 'package:gym_app/core/auth/user_role.dart';
import 'package:gym_app/core/constants/endpoints.dart';
import 'package:gym_app/core/errors/failures.dart';
import 'package:gym_app/core/network/api_client.dart';
import 'package:gym_app/core/storage/token_storage.dart';
import 'package:gym_app/core/theme/app_theme.dart';
import 'package:gym_app/features/admin/data/datasources/admin_memberships_remote_datasource.dart';
import 'package:gym_app/features/auth/data/repositories/account_repo.dart';
import 'package:gym_app/features/auth/presentation/bloc/auth_bloc.dart';
import 'package:gym_app/features/auth/presentation/screens/auth_screen.dart';
import 'package:gym_app/features/navigation/app_shell.dart';
import 'package:gym_app/features/store/presentation/bloc/cart_bloc.dart';
import 'package:gym_app/features/store/presentation/screens/cart_screen.dart';
import 'support/auth_fakes.dart';
import 'support/store_fakes.dart';

class Adapter implements HttpClientAdapter {
  Adapter(this.handler);
  final Future<ResponseBody> Function(RequestOptions) handler;
  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? requestStream, Future<void>? cancelFuture) => handler(options);
  @override
  void close({bool force = false}) {}
}
ResponseBody jsonBody(Map<String, dynamic> body, int status) => ResponseBody.fromString(jsonEncode(body), status, headers: {Headers.contentTypeHeader:[Headers.jsonContentType]});
Future<void> seed() => const TokenStorage().saveTokenPair(accessToken:'old-access',refreshToken:'old-refresh',tokenType:'bearer',role:'MEMBER');
class FailedLogoutRemote extends FakeAuthRemote {
  @override
  Future<Either<Failure,void>> logoutAll({required String accessToken}) async => Left(OfflineFailure());
}

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  test('OBSERVED: membership cash confirmation sends no body', () async {
    dynamic seen='unset';
    final client=ApiClient(dio:Dio()..httpClientAdapter=Adapter((options) async {
      seen=options.data;
      return jsonBody({'error':{'code':'validation_error','message':'Body required'}},422);
    }));
    final result=await AdminMembershipsRemoteDataSourceImpl(apiClient:client).confirmPayment('subscription-id');
    expect(seen,isNull);
    expect(result.isLeft(),isTrue);
  });
  test('OBSERVED: temporary refresh 503 deletes session', () async {
    await seed();
    final client=ApiClient(dio:Dio()..httpClientAdapter=Adapter((_) async => jsonBody({},401)), refreshDio:Dio()..httpClientAdapter=Adapter((_) async => jsonBody({},503)));
    await expectLater(client.dio.get('https://example.invalid/me'),throwsA(isA<DioException>()));
    expect(await const TokenStorage().readRefreshToken(),isNull);
  });
  test('OBSERVED: multipart upload cannot be replayed after refresh', () async {
    await seed();var calls=0;
    final client=ApiClient(dio:Dio()..httpClientAdapter=Adapter((_) async => jsonBody({},++calls==1?401:200)),refreshDio:Dio()..httpClientAdapter=Adapter((_) async=>jsonBody({'access_token':'new','refresh_token':'new-refresh','token_type':'bearer','role':'MEMBER'},200)));
    final form=FormData.fromMap({'file':MultipartFile.fromBytes([1,2,3],filename:'photo.jpg')});
    Object? error;
    try { await client.dio.post('https://example.invalid/photo',data:form).timeout(const Duration(seconds:3)); } catch(e) {error=e;}
    expect(error,isNotNull);
    expect(calls,1);
    print('Multipart replay error: $error');
  });
  test('OBSERVED: logout-all reports success after remote failure', () async {
    final local=MemoryAuthLocal()..session=sessionFor(UserRole.member);
    final repo=AccountRepoImpl(remoteDataSource:FailedLogoutRemote(),localDataSource:local,networkInfo:OnlineNetwork());
    final result=await repo.logoutAll();
    expect(result.isRight(),isTrue);
    expect(local.session,isNull);
  });
  testWidgets('OBSERVED: pushed protected route survives auth ending', (tester) async {
    final local=MemoryAuthLocal();
    final bloc=TestAuthBloc(local:local,remote:FakeAuthRemote(),role:UserRole.member);
    await tester.pumpWidget(MyApp(authBloc:bloc));
    await tester.pumpAndSettle();
    final context=tester.element(find.byType(AppShell));
    unawaited(Navigator.of(context).push(MaterialPageRoute<void>(builder:(_)=>const Scaffold(body:Text('PROTECTED DETAIL')))));
    await tester.pumpAndSettle();
    bloc.add(const AuthSessionRequested());
    await tester.pumpAndSettle();
    expect(find.byType(AuthScreen,skipOffstage:false),findsOneWidget);
    expect(find.text('PROTECTED DETAIL'),findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());unawaited(bloc.close());
  });
  testWidgets('OBSERVED: cart request failure displays spinner without error', (tester) async {
    final bloc=FakeCartBloc(const CartError(message:'Network unavailable'));
    await tester.pumpWidget(MaterialApp(theme:AppTheme.light,home:CartScreen(cartBloc:bloc)));
    await tester.pump();
    expect(find.byType(CircularProgressIndicator),findsOneWidget);
    expect(find.text('Network unavailable'),findsNothing);
    await tester.pumpWidget(const SizedBox.shrink());unawaited(bloc.close());
  });
}

