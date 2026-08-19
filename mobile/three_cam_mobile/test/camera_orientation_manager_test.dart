import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:three_cam_mobile/camera_orientation_manager.dart';

void main() {
  group('CameraOrientationManager.shouldReapply', () {
    test('is true before any orientation has ever been applied', () {
      final manager = CameraOrientationManager(onLog: (_) {});

      expect(manager.lockedOrientation, isNull);
      expect(manager.shouldReapply(DeviceOrientation.landscapeLeft), isTrue);
    });

    test('is false once the same orientation has been applied (idempotent)', () {
      // A settings save that leaves recordingOrientation unchanged must be a no-op:
      // this is the exact idempotency that keeps a redundant lockCaptureOrientation
      // call from ever reaching the camera plugin.
      final manager = CameraOrientationManager(onLog: (_) {})
        ..debugSetLockedOrientationForTest(DeviceOrientation.portraitUp);

      expect(manager.shouldReapply(DeviceOrientation.portraitUp), isFalse);
    });

    test('is true when the target orientation actually changed', () {
      final manager = CameraOrientationManager(onLog: (_) {})
        ..debugSetLockedOrientationForTest(DeviceOrientation.portraitUp);

      expect(manager.shouldReapply(DeviceOrientation.landscapeLeft), isTrue);
    });

    test('force:true always reapplies even if unchanged', () {
      final manager = CameraOrientationManager(onLog: (_) {})
        ..debugSetLockedOrientationForTest(DeviceOrientation.landscapeLeft);

      expect(
        manager.shouldReapply(DeviceOrientation.landscapeLeft, force: true),
        isTrue,
      );
    });

    test('reset() forgets the locked orientation, forcing the next reapply', () {
      final manager = CameraOrientationManager(onLog: (_) {})
        ..debugSetLockedOrientationForTest(DeviceOrientation.landscapeLeft);
      expect(manager.shouldReapply(DeviceOrientation.landscapeLeft), isFalse);

      manager.reset();

      expect(manager.lockedOrientation, isNull);
      expect(manager.shouldReapply(DeviceOrientation.landscapeLeft), isTrue);
    });
  });

  group('previewRotationQuarterTurns', () {
    // sensorOrientation=90 is the standard value for a back-facing camera (confirmed
    // live via debug logging on a real device: "sensorOrientation=90").
    test('sensorOrientation=90, target=portraitUp needs 1 quarter turn (90 CW)', () {
      final turns = previewRotationQuarterTurns(
        sensorOrientation: 90,
        target: DeviceOrientation.portraitUp,
      );
      expect(turns, 1);
    });

    test('sensorOrientation=90, target=landscapeLeft needs no rotation', () {
      // Camera2/CameraX's rotation-compensation formula: when sensorOrientation
      // equals the target's degrees, no compensation is needed - the raw buffer
      // already matches what we want to show.
      final turns = previewRotationQuarterTurns(
        sensorOrientation: 90,
        target: DeviceOrientation.landscapeLeft,
      );
      expect(turns, 0);
    });

    test('sensorOrientation=90, target=portraitDown needs 3 quarter turns (270 CW)', () {
      final turns = previewRotationQuarterTurns(
        sensorOrientation: 90,
        target: DeviceOrientation.portraitDown,
      );
      expect(turns, 3);
    });

    test('sensorOrientation=90, target=landscapeRight needs 2 quarter turns', () {
      final turns = previewRotationQuarterTurns(
        sensorOrientation: 90,
        target: DeviceOrientation.landscapeRight,
      );
      expect(turns, 2);
    });

    test('result is always in 0..3', () {
      for (final sensorOrientation in [0, 90, 180, 270]) {
        for (final target in DeviceOrientation.values) {
          final turns = previewRotationQuarterTurns(
            sensorOrientation: sensorOrientation,
            target: target,
          );
          expect(turns, inInclusiveRange(0, 3));
        }
      }
    });
  });

  group('deviceOrientationDegrees', () {
    test('matches the standard clockwise Android rotation convention', () {
      expect(deviceOrientationDegrees(DeviceOrientation.portraitUp), 0);
      expect(deviceOrientationDegrees(DeviceOrientation.landscapeLeft), 90);
      expect(deviceOrientationDegrees(DeviceOrientation.portraitDown), 180);
      expect(deviceOrientationDegrees(DeviceOrientation.landscapeRight), 270);
    });
  });
}
