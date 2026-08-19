import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

/// Pure decision used by the fullscreen-preview widget: does the raw preview buffer
/// need its width/height swapped to correctly represent [recordingOrientation]
/// (`'landscape'`/`'portrait'`), independent of live layout constraints? Extracted as a
/// free function - no `BuildContext`/`CameraController` involved - specifically so it's
/// unit-testable without a device: this is the piece that used to re-derive orientation
/// from live `previewSize` vs. screen `constraints` on every rebuild, which made the
/// preview's apparent rotation depend on transient timing instead of the operator's
/// actual orientation choice (see the widget's call site in main.dart).
bool previewNeedsDimensionSwap({
  required String recordingOrientation,
  required Size previewSize,
}) {
  final targetIsLandscape = recordingOrientation == 'landscape';
  final previewIsLandscape = previewSize.width >= previewSize.height;
  return targetIsLandscape != previewIsLandscape;
}

/// Single owner of every camera-orientation decision (camera orientation audit):
/// target orientation, UI orientation restriction, and `CameraController` capture-
/// orientation locking. Nothing else in the app should call
/// `CameraController.lockCaptureOrientation` directly.
///
/// Root cause this exists to fix: `AppSettings.needsCameraRestart()` only triggers a
/// full camera reinit for resolution/audio changes, not for a changed recording
/// orientation - so when an operator changed the orientation setting mid-session, the
/// camera's actual capture-orientation lock silently stayed stale (still the OLD
/// orientation) because nothing re-applied it. The only place that ever re-applied
/// `lockCaptureOrientation` with the (by-then-current) setting value was a second,
/// redundant call sitting immediately before `startVideoRecording()` - meaning the new
/// orientation was often applied for the very first time at the exact moment recording
/// started, producing a visible rotation snap right on START. This class closes that
/// gap by being the only caller of `lockCaptureOrientation`, applying it the instant the
/// target orientation is decided (camera init, or a settings change) rather than
/// deferring it to the next recording start.
class CameraOrientationManager {
  CameraOrientationManager({required this.onLog});

  final void Function(String message) onLog;

  DeviceOrientation? _lockedOrientation;

  /// The orientation this manager believes is currently locked on the camera it was
  /// last applied to. `null` before the first successful [apply].
  DeviceOrientation? get lockedOrientation => _lockedOrientation;

  /// Pure idempotency decision, extracted from [apply] so it's unit-testable without a
  /// real `CameraController`/platform channel: does calling the native lock actually
  /// need to happen? This is the check that keeps a settings save which didn't change
  /// orientation - or a duplicate [apply] call - from issuing a redundant native call.
  bool shouldReapply(DeviceOrientation target, {bool force = false}) {
    return force || _lockedOrientation != target;
  }

  /// Applies [target] as both the app's allowed UI orientations and the camera's
  /// locked capture orientation, and remembers it. A no-op if [target] already matches
  /// the last-applied orientation and [force] is false - safe to call on every settings
  /// save without worrying about redundant native calls.
  ///
  /// Must be called as soon as the target orientation is known or changes (camera
  /// init, settings save) - never deferred until a recording is about to start. Per the
  /// project's synchronized-start requirement (ScheduledCommand/clock sync), orientation
  /// must already be stable well before `execute_at`; putting a native orientation call
  /// on that critical path would only add jitter for no benefit, since by the time a
  /// recording starts the orientation this method establishes is already correct.
  Future<void> apply({
    required CameraController camera,
    required DeviceOrientation target,
    required List<DeviceOrientation> preferredUiOrientations,
    bool force = false,
  }) async {
    if (!shouldReapply(target, force: force)) return;
    await SystemChrome.setPreferredOrientations(preferredUiOrientations);
    try {
      await camera.lockCaptureOrientation(target);
      _lockedOrientation = target;
      onLog(
        'orientation applied: target=$target '
        'sensorOrientation=${camera.description.sensorOrientation} '
        'previewSize=${camera.value.previewSize} '
        'deviceOrientation=${camera.value.deviceOrientation} '
        'lockedCaptureOrientation=${camera.value.lockedCaptureOrientation}',
      );
    } catch (error) {
      // Some CameraX backends/devices ignore or reject capture orientation locks -
      // this must not crash camera init or settings save.
      onLog('orientation apply FAILED: $error');
    }
  }

  /// Read-only diagnostic snapshot for immediately before `startVideoRecording()`.
  /// Deliberately does NOT call `lockCaptureOrientation` - orientation must already be
  /// locked and stable by this point via [apply]; re-locking here is exactly the "blind
  /// fix right before startVideoRecording()" anti-pattern that caused the original bug.
  void logPreRecordState(CameraController camera) {
    final mismatch = _lockedOrientation != camera.value.lockedCaptureOrientation;
    onLog(
      'pre-record orientation check: managerLocked=$_lockedOrientation '
      'controllerLocked=${camera.value.lockedCaptureOrientation} '
      '${mismatch ? '(MISMATCH - camera was relocked outside the manager)' : '(consistent)'} '
      'sensorOrientation=${camera.description.sensorOrientation} '
      'previewSize=${camera.value.previewSize} '
      'deviceOrientation=${camera.value.deviceOrientation}',
    );
  }

  /// Call when a `CameraController` is disposed/replaced - the new controller starts
  /// with no lock of its own, so this manager's cached state must not be trusted to
  /// still be applied until the next [apply] call (with `force: true`) confirms it.
  void reset() {
    _lockedOrientation = null;
  }

  /// Test-only seam: `apply()` requires a real `CameraController`, which isn't
  /// available in plain unit tests, so idempotency tests set up the "an orientation is
  /// already locked" precondition directly instead. Never call this from app code.
  @visibleForTesting
  void debugSetLockedOrientationForTest(DeviceOrientation orientation) {
    _lockedOrientation = orientation;
  }
}
