import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

/// Pure decision used by the fullscreen-preview widget: does the raw preview buffer
/// need its width/height swapped to correctly represent [recordingOrientation]
/// (`'landscape'`/`'portrait'`), independent of live layout constraints? Restored
/// (2026-08-19) after being removed in favor of a RotatedBox-based rotation fix that
/// had to be reverted - without this, the preview box is sized directly from the raw
/// (landscape-shaped) camera buffer regardless of the portrait target, producing large
/// letterboxing bars top/bottom instead of filling the screen. This does not rotate any
/// pixels - it only sizes the bounding box FittedBox fits the (unrotated) preview
/// Texture into, exactly like it did before the RotatedBox detour.
bool previewNeedsDimensionSwap({
  required String recordingOrientation,
  required Size previewSize,
}) {
  final targetIsLandscape = recordingOrientation == 'landscape';
  final previewIsLandscape = previewSize.width >= previewSize.height;
  return targetIsLandscape != previewIsLandscape;
}

/// Clockwise degrees of [orientation] relative to the device's natural (portraitUp)
/// orientation - the same convention Android's `Surface.ROTATION_*`/sensor-orientation
/// values use, which is what makes this composable with [previewRotationQuarterTurns].
int deviceOrientationDegrees(DeviceOrientation orientation) {
  switch (orientation) {
    case DeviceOrientation.portraitUp:
      return 0;
    case DeviceOrientation.landscapeLeft:
      return 90;
    case DeviceOrientation.portraitDown:
      return 180;
    case DeviceOrientation.landscapeRight:
      return 270;
  }
}

/// Compensating rotation (in `RotatedBox.quarterTurns` units, clockwise) needed to
/// display the back camera's live Preview `Texture` in [target] orientation.
///
/// Root cause this exists to fix: `camera_android_camerax` 0.7.2's
/// `lockCaptureOrientation()` (android_camera_camerax.dart) only calls
/// `setTargetRotation` on `imageCapture`/`imageAnalysis`/`videoCapture` - it never
/// touches the `Preview` use case. That's why the saved MP4 is always correctly
/// oriented (verified directly from a real recorded file's `tkhd` box: 1080x1920,
/// rotation_deg=0) while the live preview can still show the wrong orientation: nothing
/// tells Preview's Texture to ignore how the phone is actually physically held/mounted
/// and just show our fixed, locked target instead. This is the standard Camera2/CameraX
/// sensor-orientation compensation formula (same one Android's own camera samples use),
/// applied against the FIXED target rather than live device orientation - we want the
/// preview visually pinned to match what's being recorded (and what the other
/// CameraNodes in a Three Cam rig show), not chasing whichever way this one phone
/// happens to be mounted.
int previewRotationQuarterTurns({
  required int sensorOrientation,
  required DeviceOrientation target,
}) {
  final compensation =
      (sensorOrientation - deviceOrientationDegrees(target) + 360) % 360;
  return (compensation ~/ 90) % 4;
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
