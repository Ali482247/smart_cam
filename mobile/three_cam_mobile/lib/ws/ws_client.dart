import 'dart:async';
import 'dart:math' as math;

import 'package:fixnum/fixnum.dart';
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

/// WebSocket client for the new networking core (network_architecture.md,
/// connection_lifecycle.md). Runs alongside the existing HTTP server/UDP responder in
/// main.dart - per the migration rules, the legacy HTTP path stays untouched and
/// operational while this is validated. This class never touches the `camera` plugin
/// or any widget state directly; it only calls [RecordingController] (strict layering).
///
/// Connection lifecycle (connection_lifecycle.md §States): the PC's existing UDP
/// discovery probe already tells this node the PC's IP (it's the packet's sender
/// address) - main.dart's UDP responder calls [connectTo] with that address after
/// sending its existing JSON reply, so no wire-format change was needed to discovery
/// to bootstrap the new WS connection.
class WsClient {
  WsClient({
    required this.recordingController,
    required this.deviceStatusProvider,
    required this.deviceLabel,
    required this.deviceSlot,
    this.appVersion = '0.1.0',
    this.protocolPort = 8088,
    this.onStatusChanged,
  });

  final RecordingController recordingController;
  final Future<Map<String, Object?>> Function() deviceStatusProvider;
  String deviceLabel;
  int deviceSlot;
  final String appVersion;
  final int protocolPort;
  final void Function(String status)? onStatusChanged;

  static const int _protocolVersion = 1;
  static const _heartbeatInterval = Duration(seconds: 5);
  static const _clockResampleInterval = Duration(seconds: 45);
  static const _reconnectBaseDelaysSeconds = [1, 2, 4, 8];
  static const _reconnectCapSeconds = 15;

  String? _deviceId;
  String? _sessionId;
  int _sequenceNumber = 0;
  int _reconnectAttempt = 0;
  bool _stopped = false;
  bool _connecting = false;
  String? _lastHost;

  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _subscription;
  Timer? _heartbeatTimer;
  Timer? _clockResampleTimer;
  Timer? _reconnectTimer;
  ClockSyncSampler? _clockSync;
  final Map<String, Completer<ClockSyncReply>> _pendingClockSync = {};
  final Map<String, Timer> _pendingCommandTimers = {};

  bool get isConnected => _channel != null;

  void _setStatus(String status) {
    onStatusChanged?.call(status);
  }

  /// Called by main.dart's UDP discovery responder every time it hears from the PC,
  /// giving this node the PC's address. A no-op if already connected/connecting.
  Future<void> connectTo(String host) async {
    _lastHost = host;
    if (_stopped || _connecting || _channel != null) return;
    _connecting = true;
    _setStatus('connecting');
    try {
      _deviceId ??= await DeviceIdentity.getOrCreate();
      final uri = Uri.parse('ws://$host:$protocolPort');
      final channel = WebSocketChannel.connect(uri);
      await channel.ready;
      await _subscription?.cancel();
      _channel = channel;
      _reconnectAttempt = 0;
      _subscription = channel.stream.listen(
        _onMessage,
        onDone: () => _onDisconnected(),
        onError: (Object error) => _onDisconnected(detail: '$error'),
        cancelOnError: true,
      );
      await _sendHello();
      _setStatus('handshaking');
    } catch (_) {
      _channel = null;
      _setStatus('disconnected');
      _scheduleReconnect();
    } finally {
      _connecting = false;
    }
  }

  Future<void> stop() async {
    _stopped = true;
    _reconnectTimer?.cancel();
    _heartbeatTimer?.cancel();
    _clockResampleTimer?.cancel();
    for (final timer in _pendingCommandTimers.values) {
      timer.cancel();
    }
    _pendingCommandTimers.clear();
    await _subscription?.cancel();
    await _channel?.sink.close();
    _channel = null;
    _setStatus('stopped');
  }

  void _onDisconnected({String detail = ''}) {
    _heartbeatTimer?.cancel();
    _clockResampleTimer?.cancel();
    _channel = null;
    _subscription = null;
    for (final completer in _pendingClockSync.values) {
      if (!completer.isCompleted) {
        completer.completeError(StateError('connection closed'));
      }
    }
    _pendingClockSync.clear();
    if (!recordingController.isRecording) {
      _sessionId = null;
      for (final timer in _pendingCommandTimers.values) {
        timer.cancel();
      }
      _pendingCommandTimers.clear();
    }
    _setStatus(detail.isEmpty ? 'disconnected' : 'disconnected: $detail');
    if (!_stopped) {
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    final host = _lastHost;
    if (_stopped || host == null) return;
    _reconnectTimer?.cancel();
    final delay = _backoffDelay(_reconnectAttempt);
    _reconnectAttempt++;
    _reconnectTimer = Timer(delay, () {
      if (!_stopped && _channel == null) {
        unawaited(connectTo(host));
      }
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
    try {
      _channel?.sink.add(envelope.writeToBuffer());
    } catch (error) {
      _onDisconnected(detail: '$error');
    }
  }

  Future<void> _sendHello() async {
    final status = await deviceStatusProvider();
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
    );
    _send(envelope);
  }

  void _onMessage(dynamic message) {
    if (message is! List<int>) return;
    Envelope envelope;
    try {
      envelope = Envelope.fromBuffer(message);
    } catch (_) {
      return;
    }

    switch (envelope.whichPayload()) {
      case Envelope_Payload.welcome:
        _onWelcome(envelope.welcome);
        break;
      case Envelope_Payload.clockReply:
        _onClockReply(envelope.clockReply);
        break;
      case Envelope_Payload.schedCmd:
        if (envelope.sessionId == _sessionId) {
          _onScheduledCommand(envelope.schedCmd);
        }
        break;
      default:
        break;
    }
  }

  void _onWelcome(Welcome welcome) {
    if (welcome.error.isNotEmpty) {
      _setStatus('rejected: ${welcome.error}');
      unawaited(_channel?.sink.close());
      return;
    }
    _sessionId = welcome.sessionId;
    _setStatus('ready');
    _clockSync = ClockSyncSampler(_exchangeClockSync);
    unawaited(_startClockSyncAndHeartbeat());
  }

  Future<void> _startClockSyncAndHeartbeat() async {
    await _clockSync?.sampleBurst();
    await _sendHeartbeat();
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (_) {
      unawaited(_sendHeartbeat());
    });
    _clockResampleTimer?.cancel();
    _clockResampleTimer = Timer.periodic(_clockResampleInterval, (_) {
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

  Future<void> _sendHeartbeat() async {
    try {
      final status = await deviceStatusProvider();
      final estimate = _clockSync?.latest ?? ClockSyncEstimate.unknown;
      final envelope = _newEnvelope();
      envelope.heartbeat = Heartbeat(
        batteryPct: _asDouble(status['batteryPercent']),
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
    } catch (error) {
      _setStatus('heartbeat error: $error');
    }
  }

  int _asInt(Object? value) {
    if (value is int) return value;
    if (value is num) return value.round();
    return 0;
  }

  double _asDouble(Object? value) {
    if (value is num) return value.toDouble();
    return 0;
  }

  void _onScheduledCommand(ScheduledCommand command) {
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
