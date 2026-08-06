import 'package:fixnum/fixnum.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:three_cam_mobile/protocol/generated/envelope.pb.dart';
import 'package:three_cam_mobile/protocol/generated/scheduler.pb.dart';
import 'package:three_cam_mobile/protocol/generated/heartbeat.pb.dart';

void main() {
  test('Envelope round-trips a ScheduledCommand payload', () {
    final envelope = Envelope(
      protocolVersion: 1,
      appVersion: '0.1',
      deviceId: 'abc',
      sessionId: 's1',
      sequenceNumber: Int64(1),
      timestampMs: Int64(123),
    );
    envelope.schedCmd = ScheduledCommand(
      type: ScheduledCommand_Type.START,
      executeAtMs: Int64(999),
      commandId: 'cmd-1',
      cameraName: 'one',
    );

    final decoded = Envelope.fromBuffer(envelope.writeToBuffer());

    expect(decoded.whichPayload(), Envelope_Payload.schedCmd);
    expect(decoded.schedCmd.commandId, 'cmd-1');
    expect(decoded.schedCmd.executeAtMs, Int64(999));
    expect(decoded.deviceId, 'abc');
  });

  test('Envelope round-trips a Heartbeat payload', () {
    final envelope = Envelope(deviceId: 'abc', sessionId: 's1');
    envelope.heartbeat = Heartbeat(
      batteryPct: 87.5,
      freeStorageBytes: Int64(1024 * 1024 * 512),
      recording: true,
    );

    final decoded = Envelope.fromBuffer(envelope.writeToBuffer());

    expect(decoded.whichPayload(), Envelope_Payload.heartbeat);
    expect(decoded.heartbeat.recording, true);
    expect(decoded.heartbeat.batteryPct, closeTo(87.5, 0.01));
  });
}
