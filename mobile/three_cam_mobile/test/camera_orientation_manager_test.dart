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

  group('previewNeedsDimensionSwap', () {
    test('landscape target with a landscape-shaped sensor buffer needs no swap', () {
      final needsSwap = previewNeedsDimensionSwap(
        recordingOrientation: 'landscape',
        previewSize: const Size(1920, 1080),
      );
      expect(needsSwap, isFalse);
    });

    test('portrait target with a landscape-shaped sensor buffer needs a swap', () {
      // This is the common real-world case: the camera's native sensor buffer is
      // landscape-shaped regardless of the operator's chosen recording orientation.
      final needsSwap = previewNeedsDimensionSwap(
        recordingOrientation: 'portrait',
        previewSize: const Size(1920, 1080),
      );
      expect(needsSwap, isTrue);
    });

    test(
      'decision depends only on target orientation and buffer shape, not any live layout size',
      () {
        // Same target + same buffer shape must always give the same answer regardless
        // of what the caller's screen constraints happen to be at that moment - the
        // whole point of removing the old constraints-based heuristic.
        final a = previewNeedsDimensionSwap(
          recordingOrientation: 'portrait',
          previewSize: const Size(1280, 720),
        );
        final b = previewNeedsDimensionSwap(
          recordingOrientation: 'portrait',
          previewSize: const Size(3840, 2160),
        );
        expect(a, b);
      },
    );
  });
}
