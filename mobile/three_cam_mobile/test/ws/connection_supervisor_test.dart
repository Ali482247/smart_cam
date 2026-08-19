import 'dart:async';
import 'dart:io';

import 'package:fixnum/fixnum.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:three_cam_mobile/protocol/generated/device.pb.dart';
import 'package:three_cam_mobile/protocol/generated/envelope.pb.dart';
import 'package:three_cam_mobile/protocol/generated/scheduler.pb.dart';
import 'package:three_cam_mobile/ws/connection_supervisor.dart';
import 'package:three_cam_mobile/ws/recording_controller.dart';

/// A minimal, real (loopback) stand-in for the Director's WS server - just enough of
/// the handshake (Hello -> Welcome) to drive [ConnectionSupervisor] through its real
/// connect/reconnect/idempotency logic against an actual socket, rather than mocking
/// the transport away. Each accepted connection gets its own generation counter on the
/// server side purely for the test's own bookkeeping (asserting how many times a fresh
/// TCP connection was actually established).
class _FakeDirector {
  _FakeDirector(this._httpServer) {
    _subscription = _httpServer.listen(_handle);
  }

  static Future<_FakeDirector> bind() async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    return _FakeDirector(server);
  }

  final HttpServer _httpServer;
  late final StreamSubscription<HttpRequest> _subscription;
  final _connections = <WebSocket>[];
  int acceptedConnections = 0;

  int get port => _httpServer.port;

  Future<void> _handle(HttpRequest request) async {
    final socket = await WebSocketTransformer.upgrade(request);
    acceptedConnections++;
    _connections.add(socket);
    socket.listen((dynamic message) {
      if (message is! List<int>) return;
      final envelope = Envelope.fromBuffer(message);
      if (envelope.whichPayload() == Envelope_Payload.hello) {
        final welcome = Envelope(
          protocolVersion: 1,
          deviceId: envelope.deviceId,
          sessionId: 'test-session',
        );
        welcome.welcome = Welcome(
          sessionId: 'test-session',
          protocolVersion: 1,
          serverTimeMs: Int64(DateTime.now().millisecondsSinceEpoch),
        );
        socket.add(welcome.writeToBuffer());
      } else if (envelope.whichPayload() == Envelope_Payload.clockReq) {
        // ConnectionSupervisor's clock-sync burst blocks reaching `ready` until this is
        // answered (or times out after 2s per sample - the fake Director must reply
        // promptly so the tests aren't stuck for the full 8-sample burst timeout).
        final now = Int64(DateTime.now().millisecondsSinceEpoch);
        final reply = Envelope(sessionId: 'test-session');
        reply.clockReply = ClockSyncReply(
          t0Ms: envelope.clockReq.t0Ms,
          t1Ms: now,
          t2Ms: now,
        );
        socket.add(reply.writeToBuffer());
      }
    });
  }

  /// Sends a `ScheduledCommand` to every currently-connected client, `executeAtMs` in
  /// the (already past) so [ConnectionSupervisor] fires it immediately instead of
  /// waiting - the test doesn't care about scheduling precision, only idempotency.
  void broadcastImmediateCommand(String commandId) {
    for (final socket in _connections) {
      final envelope = Envelope(sessionId: 'test-session');
      envelope.schedCmd = ScheduledCommand(
        type: ScheduledCommand_Type.START,
        executeAtMs: Int64(DateTime.now().millisecondsSinceEpoch - 1000),
        commandId: commandId,
        cameraName: 'one',
      );
      socket.add(envelope.writeToBuffer());
    }
  }

  /// Abruptly kills every currently-open connection - simulates the AP/socket dying out
  /// from under the client, which is exactly the case ConnectionSupervisor's generation
  /// guard and reconnect logic exist for.
  Future<void> killAllConnections() async {
    for (final socket in _connections) {
      await socket.close();
    }
    _connections.clear();
  }

  Future<void> close() async {
    await killAllConnections();
    await _subscription.cancel();
    await _httpServer.close(force: true);
  }
}

class _FakeRecordingController implements RecordingController {
  int startCount = 0;
  int stopCount = 0;
  bool _recording = false;

  @override
  bool get isRecording => _recording;

  @override
  Future<void> startRecording({
    String? cameraName,
    String? sessionId,
    String? date,
    String? time,
    int? index,
    String? signerId,
    String? signerName,
    String? signerDir,
    String? mode,
    String? word,
    String? wordId,
    String? wordDir,
    String? takeLabel,
    int? takeNumber,
    int? gestureCount,
    bool? retake,
  }) async {
    startCount++;
    _recording = true;
  }

  @override
  Future<void> stopRecording() async {
    stopCount++;
    _recording = false;
  }

  @override
  Future<Map<String, Object?>> statusJson() async => {
    'actualFps': 0,
    'activeVideoName': '',
    'recordingStartedAt': null,
  };
}

void main() {
  // ConnectionSupervisor persists device_id via DeviceIdentity -> SharedPreferences on
  // first connect; without a mock store, the plugin's method channel has no test-time
  // implementation and every connect attempt fails before it ever reaches the socket.
  SharedPreferences.setMockInitialValues({});

  // web_socket_channel's default `WebSocketChannel.connect` uses an HTML/JS backend
  // under `flutter test`'s VM runner unless explicitly pointed at the IO
  // implementation - these tests want the real dart:io WebSocket against the loopback
  // fake Director above, so ConnectionSupervisor's own `WebSocketChannel.connect` call
  // (which resolves to the IO implementation when running on the Dart VM, as `flutter
  // test` does by default) is exercised as-is; no override needed here, this comment
  // just documents why a plain loopback HttpServer is sufficient as the fake Director.

  test('reaches ready after Hello/Welcome handshake', () async {
    final director = await _FakeDirector.bind();
    addTearDown(director.close);

    final controller = _FakeRecordingController();
    final states = <ConnectionState>[];
    final supervisor = ConnectionSupervisor(
      recordingController: controller,
      deviceStatusProvider: () async => {
        'deviceName': 'test-phone',
        'batteryPercent': 42,
        'freeStorageBytes': 1000,
        'totalStorageBytes': 2000,
      },
      deviceLabel: 'one',
      deviceSlot: 1,
      protocolPort: director.port,
      onStateChanged: states.add,
    );
    addTearDown(supervisor.stop);

    await supervisor.connectTo(InternetAddress.loopbackIPv4.address);
    // connectTo() doesn't await the full handshake by design (it's fire-and-forget from
    // the UDP discovery responder's call site) - poll for readiness instead.
    await _waitUntil(() => supervisor.state == ConnectionState.ready);

    expect(supervisor.state, ConnectionState.ready);
    expect(supervisor.generation, 1);
    expect(states, contains(ConnectionState.ready));
  }, timeout: const Timeout(Duration(seconds: 10)));

  test('executes a ScheduledCommand exactly once even if delivered twice', () async {
    final director = await _FakeDirector.bind();
    addTearDown(director.close);

    final controller = _FakeRecordingController();
    final supervisor = ConnectionSupervisor(
      recordingController: controller,
      deviceStatusProvider: () async => {
        'deviceName': 'test-phone',
        'batteryPercent': 80,
        'freeStorageBytes': 1000,
        'totalStorageBytes': 2000,
      },
      deviceLabel: 'one',
      deviceSlot: 1,
      protocolPort: director.port,
    );
    addTearDown(supervisor.stop);

    await supervisor.connectTo(InternetAddress.loopbackIPv4.address);
    await _waitUntil(() => supervisor.state == ConnectionState.ready);

    director.broadcastImmediateCommand('cmd-duplicate-test');
    await _waitUntil(() => controller.startCount >= 1);
    // Re-delivery of the SAME command_id (audit §19: Director retry racing a reconnect)
    // must not execute the recording action again.
    director.broadcastImmediateCommand('cmd-duplicate-test');
    await Future<void>.delayed(const Duration(milliseconds: 300));

    expect(controller.startCount, 1);
  }, timeout: const Timeout(Duration(seconds: 10)));

  test('reconnects with a new generation after the connection dies', () async {
    final director = await _FakeDirector.bind();
    addTearDown(director.close);

    final controller = _FakeRecordingController();
    final supervisor = ConnectionSupervisor(
      recordingController: controller,
      deviceStatusProvider: () async => {
        'deviceName': 'test-phone',
        'batteryPercent': 80,
        'freeStorageBytes': 1000,
        'totalStorageBytes': 2000,
      },
      deviceLabel: 'one',
      deviceSlot: 1,
      protocolPort: director.port,
    );
    addTearDown(supervisor.stop);

    await supervisor.connectTo(InternetAddress.loopbackIPv4.address);
    await _waitUntil(() => supervisor.state == ConnectionState.ready);
    expect(supervisor.generation, 1);

    await director.killAllConnections();
    await _waitUntil(
      () => supervisor.state == ConnectionState.ready && supervisor.generation == 2,
      timeout: const Duration(seconds: 8),
    );

    expect(supervisor.generation, 2);
    expect(director.acceptedConnections, 2);
  }, timeout: const Timeout(Duration(seconds: 15)));
}

Future<void> _waitUntil(
  bool Function() condition, {
  Duration timeout = const Duration(seconds: 5),
}) async {
  final deadline = DateTime.now().add(timeout);
  while (!condition()) {
    if (DateTime.now().isAfter(deadline)) {
      fail('condition not met within $timeout');
    }
    await Future<void>.delayed(const Duration(milliseconds: 20));
  }
}
