import 'dart:async';
import 'dart:math' as math;

import 'package:fixnum/fixnum.dart';
import 'package:uuid/uuid.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../protocol/generated/common.pb.dart';
import '../protocol/generated/device.pb.dart';
import '../protocol/generated/envelope.pb.dart';
import '../protocol/generated/heartbeat.pb.dart';
import '../protocol/generated/recording.pb.dart';
import '../protocol/generated/scheduler.pb.dart';
import 'clock_sync_sampler.dart';
import 'device_identity.dart';
import 'recording_controller.dart';

/// Explicit connection state machine (connection reliability audit §5). Every
/// reconnect/backoff/half-open decision in [ConnectionSupervisor] goes through
/// [ConnectionSupervisor._transition], so there is exactly one place that owns "what
/// state is the WS control-plane connection in and why" - not a set of independent
/// booleans reconstructable only by reading several call sites at once.
enum ConnectionState {
  stopped,
  starting,
  connecting,
  handshaking,
  syncing,
  ready,
  degraded,
  reconnecting,
  backoff,
}

/// One structured connection-lifecycle event (audit §18). Kept as a plain value type so
/// it can be handed to any sink (console log, local NDJSON file, forwarded to the
/// Director) without this class needing to know which - see [ConnectionSupervisor.onTelemetryEvent].
class ConnectionTelemetryEvent {
  ConnectionTelemetryEvent({
    required this.eventType,
    required this.state,
    this.previousState,
    this.reason = '',
    this.batteryPercent,
    this.wifi,
    this.currentIp,
  }) : timestamp = DateTime.now();

  final DateTime timestamp;
  final String eventType;
  final ConnectionState state;
  final ConnectionState? previousState;
  final String reason;
  final int? batteryPercent;
  final bool? wifi;
  final String? currentIp;

  Map<String, Object?> toJson({
    required String? deviceId,
    required String appInstanceId,
    required int connectionGeneration,
  }) => {
    'timestamp': timestamp.toIso8601String(),
    'device_id': deviceId,
    'app_instance_id': appInstanceId,
    'connection_generation': connectionGeneration,
    'connection_state': state.name,
    'previous_state': previousState?.name,
    'battery_percent': batteryPercent,
    'network_type': wifi == null ? null : (wifi! ? 'wifi' : 'other'),
    'current_ip': currentIp,
    'event_type': eventType,
    'reason': reason,
  };
}

/// Unified owner of the WS control-plane connection lifecycle to the Director
/// (connection reliability audit §5-§10, §16, §19-§20). This is the single place that:
///
///  - owns the WebSocket transport (connect / handshake / heartbeat / clock-sync /
///    reconnect / backoff) - nothing else in the app opens or closes this socket;
///  - tracks an explicit [ConnectionState] instead of scattered booleans;
///  - stamps every connection attempt with a monotonically increasing
///    `connection_generation`, captured by each attempt's own callbacks, so a stale
///    callback from a connection that has already been superseded can never mutate a
///    newer connection's state (audit §6's "late callback from #1 must NOT destroy #2");
///  - detects half-open connections via bidirectional heartbeat acks instead of waiting
///    on a TCP-level timeout (audit §8-9);
///  - de-duplicates `ScheduledCommand` execution by `command_id` across reconnects/
///    retries, so a command already executed is never executed twice (audit §19);
///  - applies a circuit breaker around repeated reconnect failure (audit §16 Layer 6),
///    instead of retrying forever at the same cadence.
///
/// Deliberately out of scope: the HTTP server and UDP discovery responder in main.dart.
/// They're plain `dart:io` primitives tightly coupled to `_CameraControlScreenState`'s
/// recording fields and already have their own narrowly-scoped, generation-guarded
/// restart logic there (`_scheduleServerRestart`/`_scheduleDiscoveryRestart`). Folding
/// them into this class would be a much larger refactor for no reliability gain, so per
/// the audit's own stated priority ("Minimal architectural changes" ranks above "Code
/// cleanliness"), they stay where they are; this class instead exposes
/// [onNetworkAvailable]/[onNetworkLost] and [onFullResetRequested] so main.dart's
/// `ConnectivityManager.NetworkCallback` listener and its own watchdogs can coordinate
/// with this one without either owning the other's resources.
class ConnectionSupervisor {
  ConnectionSupervisor({
    required this.recordingController,
    required this.deviceStatusProvider,
    required this.deviceLabel,
    required this.deviceSlot,
    this.appVersion = '0.1.0',
    this.protocolPort = 8088,
    this.onStatusChanged,
    this.onStateChanged,
    this.onTelemetryEvent,
    this.onFullResetRequested,
  }) : appInstanceId = const Uuid().v4();

  final RecordingController recordingController;
  final Future<Map<String, Object?>> Function() deviceStatusProvider;
  String deviceLabel;
  int deviceSlot;
  final String appVersion;
  final int protocolPort;

  /// Legacy free-form status string, kept only because the existing UI label
  /// (`_TopStatus`) reads it - prefer [onStateChanged]/[state] for anything logical.
  final void Function(String status)? onStatusChanged;
  final void Function(ConnectionState state)? onStateChanged;
  final void Function(ConnectionTelemetryEvent event)? onTelemetryEvent;

  /// Invoked when the circuit breaker trips after repeated reconnect failure (audit §16
  /// Layer 6: "Full network stack reset ... must be limited"). main.dart wires this to
  /// also force-restart the HTTP server and UDP discovery socket, so when the WS path
  /// has been stuck long enough to trip the breaker, all three control-plane paths get
  /// a coordinated clean slate rather than each silently retrying forever in isolation.
  final void Function()? onFullResetRequested;

  /// Generated once per process start, in memory only - never persisted. Lets the
  /// server tell "the same install reconnecting" (device_id unchanged) apart from "the
  /// app process was killed and relaunched" (app_instance_id changed) - a persisted
  /// device_id alone cannot make that distinction (audit §7).
  final String appInstanceId;

  static const int _protocolVersion = 1;
  static const _heartbeatInterval = Duration(seconds: 5);
  // 3 missed heartbeats (5s apart) plus margin - inside the 10-15s range the audit asks
  // for. Short enough that a half-open connection (audit §9: this node still thinks
  // it's connected, the Director already dropped it) is caught well before an operator
  // would notice a stuck take, long enough that it won't false-positive on ordinary
  // Wi-Fi jitter (docs/clock_synchronization.md already treats that as expected).
  static const _heartbeatAckTimeout = Duration(seconds: 15);
  static const _clockResampleInterval = Duration(seconds: 45);
  static const _reconnectBaseDelaysSeconds = [1, 2, 4, 8];
  static const _reconnectCapSeconds = 15;
  // Circuit breaker (audit §16 Layer 6). Both conditions are required so a single bad
  // AP hiccup never escalates past the normal per-attempt backoff above - only a
  // genuinely stuck connection (this many failures inside this window) trips it.
  static const _circuitBreakerFailureThreshold = 6;
  static const _circuitBreakerWindow = Duration(seconds: 90);
  static const _circuitBreakerCooldown = Duration(seconds: 45);
  static const _maxTrackedCommandIds = 64;

  String? _deviceId;
  String? _sessionId;
  int _sequenceNumber = 0;
  int _reconnectAttempt = 0;
  int _generation = 0;
  bool _stopped = false;
  bool _connecting = false;
  String? _lastHost;
  String? _lastKnownIp;
  int? _lastKnownBatteryPercent;
  bool? _lastKnownWifi;
  ConnectionState _state = ConnectionState.stopped;
  DateTime? _firstFailureInWindow;
  int _consecutiveFailures = 0;

  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _subscription;
  Timer? _heartbeatTimer;
  Timer? _clockResampleTimer;
  Timer? _reconnectTimer;
  ClockSyncSampler? _clockSync;
  DateTime? _lastHeartbeatAckAt;
  final Map<String, Completer<ClockSyncReply>> _pendingClockSync = {};
  final Map<String, Timer> _pendingCommandTimers = {};
  final List<String> _executedCommandIds = [];

  ConnectionState get state => _state;
  bool get isReady => _state == ConnectionState.ready;
  int get generation => _generation;
  String? get deviceId => _deviceId;

  /// main.dart calls this whenever it refreshes the phone's own IP, purely so
  /// telemetry events carry a meaningful `current_ip` (audit §18).
  void updateKnownIp(String ip) {
    _lastKnownIp = ip;
  }

  void _transition(ConnectionState next, {String reason = '', String eventType = ''}) {
    final previous = _state;
    _state = next;
    onStateChanged?.call(next);
    onStatusChanged?.call(next.name);
    onTelemetryEvent?.call(
      ConnectionTelemetryEvent(
        eventType: eventType.isEmpty ? '${previous.name}_TO_${next.name}'.toUpperCase() : eventType,
        state: next,
        previousState: previous,
        reason: reason,
        batteryPercent: _lastKnownBatteryPercent,
        wifi: _lastKnownWifi,
        currentIp: _lastKnownIp,
      ),
    );
  }

  void _emitTelemetry(String eventType, {String reason = ''}) {
    onTelemetryEvent?.call(
      ConnectionTelemetryEvent(
        eventType: eventType,
        state: _state,
        reason: reason,
        batteryPercent: _lastKnownBatteryPercent,
        wifi: _lastKnownWifi,
        currentIp: _lastKnownIp,
      ),
    );
  }

  /// Called by main.dart's UDP discovery responder every time it hears from the PC,
  /// giving this node the PC's address. A no-op if already connected/connecting.
  Future<void> connectTo(String host) async {
    _lastHost = host;
    await _connect(host);
  }

  /// Real OS connectivity signal (Kotlin `ConnectivityManager.NetworkCallback` via
  /// main.dart's `EventChannel` listener) instead of relying only on polling/backoff
  /// (audit §10). Cancels any pending backoff and retries immediately.
  void onNetworkAvailable({bool? wifi}) {
    if (wifi != null) _lastKnownWifi = wifi;
    if (_stopped) return;
    if (_channel != null) {
      _emitTelemetry('NETWORK_AVAILABLE', reason: 'already_connected');
      return;
    }
    final host = _lastHost;
    if (host == null) {
      _emitTelemetry('NETWORK_AVAILABLE', reason: 'no_known_director_host_yet');
      return;
    }
    _reconnectTimer?.cancel();
    _transition(ConnectionState.connecting, reason: 'network_available', eventType: 'NETWORK_AVAILABLE');
    unawaited(_connect(host));
  }

  /// Real OS connectivity-loss signal - force-closes any live connection immediately
  /// rather than waiting for it to time out on its own (audit §10).
  void onNetworkLost() {
    _lastKnownWifi = false;
    if (_stopped) return;
    if (_channel != null) {
      _forceDisconnect(reason: 'network_lost');
    } else {
      _emitTelemetry('NETWORK_LOST', reason: 'no_active_connection');
    }
  }

  Future<void> stop() async {
    _stopped = true;
    _reconnectTimer?.cancel();
    await _cleanupConnection();
    _transition(ConnectionState.stopped, reason: 'stop_called', eventType: 'WS_STOPPED');
  }

  // ---------------------------------------------------------------------------------
  // Connect / disconnect / reconnect
  // ---------------------------------------------------------------------------------

  Future<void> _connect(String host) async {
    if (_stopped || _connecting || _channel != null) return;
    _reconnectTimer?.cancel();
    _connecting = true;
    // The ONLY place `_generation` is incremented - every callback tied to this
    // connection attempt captures this value and compares against `_generation` before
    // acting, so once a newer attempt starts, every callback from this one becomes an
    // inert no-op instead of being able to touch state the newer attempt owns.
    _generation++;
    final generation = _generation;
    _transition(ConnectionState.connecting, reason: 'connect_attempt gen=$generation');
    try {
      _deviceId ??= await DeviceIdentity.getOrCreate();
      final uri = Uri.parse('ws://$host:$protocolPort');
      final channel = WebSocketChannel.connect(uri);
      await channel.ready;
      if (generation != _generation || _stopped) {
        // Superseded (or stop() called) while the socket was still opening - this
        // connection is disposable, never adopt it (audit §6 "OLD CONNECTION IS
        // DISPOSABLE, NEW CONNECTION IS CREATED FROM SCRATCH").
        unawaited(channel.sink.close());
        return;
      }
      _channel = channel;
      _subscription = channel.stream.listen(
        (message) => _onMessage(generation, message),
        onDone: () => _onDisconnected(generation, reason: 'socket_closed'),
        onError: (Object _) => _onDisconnected(generation, reason: 'socket_error'),
        cancelOnError: true,
      );
      _transition(ConnectionState.handshaking, reason: 'socket_open', eventType: 'WS_CONNECTED');
      await _sendHello(generation);
    } catch (error) {
      if (generation == _generation) {
        _channel = null;
        unawaited(
          _teardownAndScheduleReconnect(
            generation,
            reason: 'connect_failed: $error',
            eventType: 'WS_RECONNECT_FAILED',
          ),
        );
      }
    } finally {
      _connecting = false;
    }
  }

  void _onDisconnected(int generation, {required String reason}) {
    unawaited(_teardownAndScheduleReconnect(generation, reason: reason));
  }

  /// Proactive teardown of the CURRENT connection - used for half-open detection
  /// (heartbeat ack timeout) and `onNetworkLost()`, where the socket object may still
  /// look alive locally but this node has decided not to trust it any more.
  void _forceDisconnect({required String reason}) {
    final generation = _generation;
    unawaited(
      _teardownAndScheduleReconnect(generation, reason: reason, eventType: 'WS_HEARTBEAT_TIMEOUT'),
    );
  }

  Future<void> _teardownAndScheduleReconnect(
    int generation, {
    required String reason,
    String eventType = 'WS_DISCONNECTED',
  }) async {
    if (generation != _generation) return; // stale callback from an already-superseded attempt
    _transition(ConnectionState.degraded, reason: reason, eventType: eventType);
    await _cleanupConnection();
    if (_stopped) {
      _transition(ConnectionState.stopped, reason: 'stopped_during_cleanup');
      return;
    }
    _transition(ConnectionState.reconnecting, reason: 'cleanup_complete', eventType: 'WS_RECONNECT_STARTED');
    _scheduleReconnect(generation);
  }

  /// Tears down whatever the CURRENT connection's resources are. Cancelling the stream
  /// subscription before closing the sink matters: it guarantees `onDone`/`onError`
  /// never fires for a teardown WE initiated, so `_onDisconnected` can't be triggered a
  /// second time on top of the reconnect this same call is about to schedule (audit
  /// §20's "watchdog restart + ..." double-restart race).
  Future<void> _cleanupConnection() async {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
    _clockResampleTimer?.cancel();
    _clockResampleTimer = null;
    _lastHeartbeatAckAt = null;
    final channel = _channel;
    final subscription = _subscription;
    _channel = null;
    _subscription = null;
    await subscription?.cancel();
    unawaited(channel?.sink.close());
    if (!recordingController.isRecording) {
      _sessionId = null;
      for (final timer in _pendingCommandTimers.values) {
        timer.cancel();
      }
      _pendingCommandTimers.clear();
    }
  }

  void _scheduleReconnect(int generation) {
    if (_stopped) return;
    _reconnectTimer?.cancel();

    final now = DateTime.now();
    _firstFailureInWindow ??= now;
    if (now.difference(_firstFailureInWindow!) > _circuitBreakerWindow) {
      _firstFailureInWindow = now;
      _consecutiveFailures = 0;
    }
    _consecutiveFailures++;

    final circuitTripped = _consecutiveFailures >= _circuitBreakerFailureThreshold;
    final delay = circuitTripped ? _circuitBreakerCooldown : _backoffDelay(_reconnectAttempt);
    _reconnectAttempt++;

    _transition(
      circuitTripped ? ConnectionState.backoff : ConnectionState.reconnecting,
      reason: circuitTripped
          ? 'circuit_breaker_tripped ($_consecutiveFailures failures in ${_circuitBreakerWindow.inSeconds}s)'
          : 'scheduling retry #$_reconnectAttempt in ${delay.inSeconds}s',
      eventType: circuitTripped ? 'FULL_NETWORK_RESET' : 'WS_RECONNECT_STARTED',
    );
    if (circuitTripped) {
      _consecutiveFailures = 0;
      _firstFailureInWindow = null;
      onFullResetRequested?.call();
    }

    _reconnectTimer = Timer(delay, () {
      if (_stopped || generation != _generation || _channel != null) return;
      final host = _lastHost;
      if (host == null) return;
      unawaited(_connect(host));
    });
  }

  Duration _backoffDelay(int attempt) {
    final baseSeconds = attempt < _reconnectBaseDelaysSeconds.length
        ? _reconnectBaseDelaysSeconds[attempt]
        : _reconnectCapSeconds;
    final jitterFraction = (math.Random().nextDouble() * 2 - 1) * 0.2; // +-20%
    final seconds = (baseSeconds * (1 + jitterFraction)).clamp(
      0.5,
      _reconnectCapSeconds * 1.2,
    );
    return Duration(milliseconds: (seconds * 1000).round());
  }

  // ---------------------------------------------------------------------------------
  // Envelope plumbing
  // ---------------------------------------------------------------------------------

  Envelope _newEnvelope() {
    _sequenceNumber += 1;
    return Envelope(
      protocolVersion: _protocolVersion,
      appVersion: appVersion,
      deviceId: _deviceId,
      sessionId: _sessionId,
      sequenceNumber: Int64(_sequenceNumber),
      timestampMs: Int64(DateTime.now().millisecondsSinceEpoch),
    );
  }

  void _send(Envelope envelope) {
    _channel?.sink.add(envelope.writeToBuffer());
  }

  Future<void> _sendHello(int generation) async {
    if (generation != _generation) return;
    final status = await deviceStatusProvider();
    if (generation != _generation) return;
    final envelope = _newEnvelope();
    envelope.hello = Hello(
      deviceId: _deviceId,
      deviceName: '${status['deviceName'] ?? ''}',
      manufacturer: '${status['manufacturer'] ?? ''}',
      osVersion: '${status['osVersion'] ?? ''}',
      deviceSlot: deviceSlot,
      deviceLabel: deviceLabel,
      androidId: '${status['deviceId'] ?? ''}',
      appVersion: appVersion,
      appInstanceId: appInstanceId,
      connectionGeneration: Int64(generation),
    );
    _send(envelope);
  }

  void _onMessage(int generation, dynamic message) {
    if (generation != _generation) return; // stale connection's socket, ignore entirely
    if (message is! List<int>) return;
    Envelope envelope;
    try {
      envelope = Envelope.fromBuffer(message);
    } catch (_) {
      return;
    }

    switch (envelope.whichPayload()) {
      case Envelope_Payload.welcome:
        _onWelcome(generation, envelope.welcome);
        break;
      case Envelope_Payload.clockReply:
        _onClockReply(envelope.clockReply);
        break;
      case Envelope_Payload.heartbeatAck:
        _onHeartbeatAck(envelope.heartbeatAck);
        break;
      case Envelope_Payload.schedCmd:
        if (envelope.sessionId == _sessionId) {
          _onScheduledCommand(generation, envelope.schedCmd);
        }
        break;
      default:
        break;
    }
  }

  void _onWelcome(int generation, Welcome welcome) {
    if (generation != _generation) return;
    if (welcome.error.isNotEmpty) {
      unawaited(
        _teardownAndScheduleReconnect(generation, reason: 'rejected: ${welcome.error}'),
      );
      return;
    }
    _sessionId = welcome.sessionId;
    _transition(ConnectionState.syncing, reason: 'welcome_received', eventType: 'WS_HANDSHAKE_COMPLETE');
    _clockSync = ClockSyncSampler(_exchangeClockSync);
    unawaited(_startClockSyncAndHeartbeat(generation));
  }

  Future<void> _startClockSyncAndHeartbeat(int generation) async {
    await _clockSync?.sampleBurst();
    if (generation != _generation) return;
    _reconnectAttempt = 0;
    _consecutiveFailures = 0;
    _firstFailureInWindow = null;
    _transition(ConnectionState.ready, reason: 'clock_sync_complete', eventType: 'WS_RECONNECT_SUCCESS');
    await _startHeartbeatLoop(generation);
    _clockResampleTimer?.cancel();
    _clockResampleTimer = Timer.periodic(_clockResampleInterval, (_) {
      if (generation != _generation) return;
      unawaited(_clockSync?.sampleBurst());
    });
  }

  Future<ClockSyncReply> _exchangeClockSync(ClockSyncRequest request) async {
    final key = request.t0Ms.toString();
    final completer = Completer<ClockSyncReply>();
    _pendingClockSync[key] = completer;
    final envelope = _newEnvelope();
    envelope.clockReq = request;
    _send(envelope);
    try {
      return await completer.future.timeout(const Duration(seconds: 2));
    } finally {
      _pendingClockSync.remove(key);
    }
  }

  void _onClockReply(ClockSyncReply reply) {
    final key = reply.t0Ms.toString();
    _pendingClockSync.remove(key)?.complete(reply);
  }

  // ---------------------------------------------------------------------------------
  // Bidirectional heartbeat (half-open detection - audit §8-9)
  // ---------------------------------------------------------------------------------

  Future<void> _startHeartbeatLoop(int generation) async {
    _lastHeartbeatAckAt = DateTime.now(); // optimistic baseline at connect time
    await _sendHeartbeat(generation);
    if (generation != _generation) return;
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (_) {
      if (generation != _generation) return;
      if (_isHeartbeatStale()) {
        _forceDisconnect(reason: 'heartbeat_ack_timeout');
        return;
      }
      unawaited(_sendHeartbeat(generation));
    });
  }

  bool _isHeartbeatStale() {
    final lastAck = _lastHeartbeatAckAt;
    if (lastAck == null) return false;
    return DateTime.now().difference(lastAck) > _heartbeatAckTimeout;
  }

  Future<void> _sendHeartbeat(int generation) async {
    if (generation != _generation) return;
    final status = await deviceStatusProvider();
    if (generation != _generation) return;
    final batteryPercent = status['batteryPercent'];
    if (batteryPercent is num) {
      _lastKnownBatteryPercent = batteryPercent.round();
    }
    final estimate = _clockSync?.latest ?? ClockSyncEstimate.unknown;
    final envelope = _newEnvelope();
    envelope.heartbeat = Heartbeat(
      // Previously hardcoded to 0 regardless of actual battery level - the server-side
      // Session.battery_pct (server/connection/models.py) never reflected reality over
      // the WS path, which is exactly the data the audit's "ONLINE + LOW_BATTERY, not
      // OFFLINE" distinction (audit §17) depends on. Fixed here.
      batteryPct: batteryPercent is num ? batteryPercent.toDouble() : 0,
      freeStorageBytes: Int64(_asInt(status['freeStorageBytes'])),
      totalStorageBytes: Int64(_asInt(status['totalStorageBytes'])),
      temperatureC: 0,
      recording: recordingController.isRecording,
      clockOffsetMs: Int64(estimate.offsetMs.round()),
      clockUncertaintyMs: estimate.uncertaintyMs.isFinite
          ? estimate.uncertaintyMs.round()
          : 0,
      lastRttMs: (_clockSync?.lastRttMs ?? 0).toDouble(),
    );
    _send(envelope);
  }

  void _onHeartbeatAck(HeartbeatAck ack) {
    _lastHeartbeatAckAt = DateTime.now();
  }

  int _asInt(Object? value) {
    if (value is int) return value;
    if (value is num) return value.round();
    return 0;
  }

  // ---------------------------------------------------------------------------------
  // Scheduled commands (idempotent - audit §19)
  // ---------------------------------------------------------------------------------

  void _onScheduledCommand(int generation, ScheduledCommand command) {
    if (generation != _generation) return;
    if (_executedCommandIds.contains(command.commandId)) {
      // Already executed this exact command_id in a previous delivery (e.g. the
      // Director re-sent it after a reconnect raced with the original Ack). Ack it
      // again so the Director's retry bookkeeping is satisfied, but never execute the
      // recording action a second time.
      _sendAck(command.commandId, ResultCode.RESULT_OK);
      return;
    }

    _pendingCommandTimers.remove(command.commandId)?.cancel();

    final clockSync = _clockSync;
    final localExecuteAtMs = clockSync != null
        ? clockSync.serverTimeToLocalMs(command.executeAtMs.toInt())
        : command.executeAtMs.toInt();
    final delayMs = localExecuteAtMs - DateTime.now().millisecondsSinceEpoch;
    final delay = delayMs > 0 ? Duration(milliseconds: delayMs) : Duration.zero;

    _sendAck(command.commandId, ResultCode.RESULT_OK);

    final timer = Timer(delay, () {
      _pendingCommandTimers.remove(command.commandId);
      unawaited(_executeCommand(command));
    });
    _pendingCommandTimers[command.commandId] = timer;
  }

  void _sendAck(String commandId, ResultCode result) {
    final envelope = _newEnvelope();
    envelope.ack = Ack(commandId: commandId, result: result);
    _send(envelope);
  }

  Future<void> _executeCommand(ScheduledCommand command) async {
    _markCommandExecuted(command.commandId);
    try {
      switch (command.type) {
        case ScheduledCommand_Type.START:
          await recordingController.startRecording(
            cameraName: command.cameraName.isEmpty ? null : command.cameraName,
            sessionId: command.sessionLabel.isEmpty
                ? null
                : command.sessionLabel,
            index: command.recordIndex == 0 ? null : command.recordIndex,
          );
          _sendEvent(Event_Type.RECORDING_STARTED);
          break;
        case ScheduledCommand_Type.STOP:
          await recordingController.stopRecording();
          _sendEvent(Event_Type.RECORDING_STOPPED);
          break;
        case ScheduledCommand_Type.TOGGLE:
          if (recordingController.isRecording) {
            await recordingController.stopRecording();
            _sendEvent(Event_Type.RECORDING_STOPPED);
          } else {
            await recordingController.startRecording();
            _sendEvent(Event_Type.RECORDING_STARTED);
          }
          break;
        default:
          break;
      }
      await _sendStatusUpdate();
    } catch (error) {
      _sendEvent(
        Event_Type.CONNECTION_LOST,
        detail: 'command execution failed: $error',
      );
    }
  }

  void _markCommandExecuted(String commandId) {
    _executedCommandIds.add(commandId);
    if (_executedCommandIds.length > _maxTrackedCommandIds) {
      _executedCommandIds.removeAt(0);
    }
  }

  void _sendEvent(Event_Type type, {String detail = ''}) {
    final envelope = _newEnvelope();
    envelope.event = Event(type: type, detail: detail);
    _send(envelope);
  }

  Future<void> _sendStatusUpdate() async {
    final statusJson = await recordingController.statusJson();
    final recordingStartedAtIso = statusJson['recordingStartedAt'] as String?;
    final recordingStartedAtMs = recordingStartedAtIso != null
        ? DateTime.parse(recordingStartedAtIso).millisecondsSinceEpoch
        : 0;
    final envelope = _newEnvelope();
    envelope.status = StatusUpdate(
      recording: recordingController.isRecording,
      actualFps: (statusJson['actualFps'] as num?)?.toDouble() ?? 0,
      activeVideoName: '${statusJson['activeVideoName'] ?? ''}',
      recordingStartedAtMs: Int64(recordingStartedAtMs),
    );
    _send(envelope);
  }
}
