/// The seam between the WS transport (`ws_client.dart`) and camera business logic
/// (`_CameraControlScreenState` in main.dart). `WsClient` only ever talks to this
/// interface - it never touches the `camera` plugin, `MethodChannel`, or any
/// Flutter widget state directly (network_architecture.md's strict layering rule:
/// "camera code must never know about WebSocket, and vice versa").
abstract class RecordingController {
  bool get isRecording;

  Future<void> startRecording({
    String? cameraName,
    String? sessionId,
    String? date,
    String? time,
    int? index,
  });

  Future<void> stopRecording();

  /// Same shape as the existing HTTP `/status` endpoint's JSON body - reused so the
  /// WS StatusUpdate payload and the legacy HTTP status response never drift apart.
  Future<Map<String, Object?>> statusJson();
}
