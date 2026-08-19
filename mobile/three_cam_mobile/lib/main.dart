import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'camera_orientation_manager.dart';
import 'ws/connection_supervisor.dart';
import 'ws/recording_controller.dart';

const int controlPort = 8088;
const int discoveryPort = 8089;
const String discoveryMessage = 'THREE_CAM_DISCOVER';
const MethodChannel mediaChannel = MethodChannel('three_cam/media');
const EventChannel connectivityEventChannel = EventChannel('three_cam/connectivity');
const int stableRecordingFps = 30;
const String appVersion = '1.1.0';
const List<String> reticleModes = [
  'off',
  'dot',
  'cross',
  'splitCross',
  'frameCross',
];

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
    DeviceOrientation.landscapeLeft,
    DeviceOrientation.landscapeRight,
  ]);
  runApp(const ThreeCamApp());
}

class ThreeCamApp extends StatelessWidget {
  const ThreeCamApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Three Cam',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xffd8344f),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: const CameraControlScreen(),
    );
  }
}

class AppSettings {
  const AppSettings({
    required this.deviceSlot,
    required this.deviceLabel,
    required this.gridMode,
    required this.reticleMode,
    required this.resolutionPreset,
    required this.fps,
    required this.recordingOrientation,
    required this.enableAudio,
    required this.keepScreenOn,
    required this.saveToGallery,
    required this.filePrefix,
    required this.autoExposure,
    required this.autoFocus,
    required this.smartZoom,
    required this.zoomLevel,
  });

  final int deviceSlot;
  final String deviceLabel;
  final String gridMode;
  final String reticleMode;
  final String resolutionPreset;
  final int fps;
  final String recordingOrientation;
  final bool enableAudio;
  final bool keepScreenOn;
  final bool saveToGallery;
  final String filePrefix;
  final bool autoExposure;
  final bool autoFocus;
  final bool smartZoom;
  final double zoomLevel;

  static AppSettings defaults() {
    return const AppSettings(
      deviceSlot: 1,
      deviceLabel: 'device_1',
      gridMode: 'off',
      reticleMode: 'cross',
      resolutionPreset: 'veryHigh',
      fps: stableRecordingFps,
      recordingOrientation: 'portrait',
      enableAudio: true,
      keepScreenOn: true,
      saveToGallery: true,
      filePrefix: '',
      autoExposure: true,
      autoFocus: true,
      smartZoom: true,
      zoomLevel: 1,
    );
  }

  static Future<AppSettings> load() async {
    final prefs = await SharedPreferences.getInstance();
    final defaults = AppSettings.defaults();
    final slot = prefs.getInt('deviceSlot') ?? defaults.deviceSlot;
    return AppSettings(
      deviceSlot: slot,
      deviceLabel: prefs.getString('deviceLabel') ?? 'device_$slot',
      gridMode: prefs.getString('gridMode') ?? defaults.gridMode,
      reticleMode: prefs.getString('reticleMode') ?? defaults.reticleMode,
      resolutionPreset:
          prefs.getString('resolutionPreset') ?? defaults.resolutionPreset,
      fps: stableRecordingFps,
      recordingOrientation:
          prefs.getString('recordingOrientation') ??
          defaults.recordingOrientation,
      enableAudio: prefs.getBool('enableAudio') ?? defaults.enableAudio,
      keepScreenOn: prefs.getBool('keepScreenOn') ?? defaults.keepScreenOn,
      saveToGallery: prefs.getBool('saveToGallery') ?? defaults.saveToGallery,
      filePrefix: prefs.getString('filePrefix') ?? defaults.filePrefix,
      autoExposure: prefs.getBool('autoExposure') ?? defaults.autoExposure,
      autoFocus: prefs.getBool('autoFocus') ?? defaults.autoFocus,
      smartZoom: prefs.getBool('smartZoom') ?? defaults.smartZoom,
      zoomLevel: prefs.getDouble('zoomLevel') ?? defaults.zoomLevel,
    );
  }

  Future<void> save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('deviceSlot', deviceSlot);
    await prefs.setString('deviceLabel', deviceLabel);
    await prefs.setString('gridMode', gridMode);
    await prefs.setString('reticleMode', reticleMode);
    await prefs.setString('resolutionPreset', resolutionPreset);
    await prefs.setInt('fps', stableRecordingFps);
    await prefs.setString('recordingOrientation', recordingOrientation);
    await prefs.setBool('enableAudio', enableAudio);
    await prefs.setBool('keepScreenOn', keepScreenOn);
    await prefs.setBool('saveToGallery', saveToGallery);
    await prefs.setString('filePrefix', filePrefix);
    await prefs.setBool('autoExposure', autoExposure);
    await prefs.setBool('autoFocus', autoFocus);
    await prefs.setBool('smartZoom', smartZoom);
    await prefs.setDouble('zoomLevel', zoomLevel);
  }

  AppSettings copyWith({
    int? deviceSlot,
    String? deviceLabel,
    String? gridMode,
    String? reticleMode,
    String? resolutionPreset,
    int? fps,
    String? recordingOrientation,
    bool? enableAudio,
    bool? keepScreenOn,
    bool? saveToGallery,
    String? filePrefix,
    bool? autoExposure,
    bool? autoFocus,
    bool? smartZoom,
    double? zoomLevel,
  }) {
    final nextSlot = deviceSlot ?? this.deviceSlot;
    return AppSettings(
      deviceSlot: nextSlot,
      deviceLabel: deviceLabel ?? this.deviceLabel,
      gridMode: gridMode ?? this.gridMode,
      reticleMode: reticleMode ?? this.reticleMode,
      resolutionPreset: resolutionPreset ?? this.resolutionPreset,
      fps: stableRecordingFps,
      recordingOrientation: recordingOrientation ?? this.recordingOrientation,
      enableAudio: enableAudio ?? this.enableAudio,
      keepScreenOn: keepScreenOn ?? this.keepScreenOn,
      saveToGallery: saveToGallery ?? this.saveToGallery,
      filePrefix: filePrefix ?? this.filePrefix,
      autoExposure: autoExposure ?? this.autoExposure,
      autoFocus: autoFocus ?? this.autoFocus,
      smartZoom: smartZoom ?? this.smartZoom,
      zoomLevel: zoomLevel ?? this.zoomLevel,
    );
  }

  AppSettings normalized() {
    final safeSlot = deviceSlot.clamp(1, 99);
    final safeLabel = _cleanLabel(deviceLabel).isEmpty
        ? 'device_$safeSlot'
        : _cleanLabel(deviceLabel);
    return copyWith(
      deviceSlot: safeSlot,
      deviceLabel: safeLabel,
      filePrefix: _cleanLabel(filePrefix),
      reticleMode: reticleModes.contains(reticleMode) ? reticleMode : 'cross',
      recordingOrientation: recordingOrientation == 'landscape'
          ? 'landscape'
          : 'portrait',
      zoomLevel: zoomLevel.clamp(1, 100).toDouble(),
    );
  }

  bool needsCameraRestart(AppSettings other) {
    return resolutionPreset != other.resolutionPreset ||
        enableAudio != other.enableAudio;
  }

  List<DeviceOrientation> get preferredOrientations {
    if (recordingOrientation == 'landscape') {
      return const [
        DeviceOrientation.landscapeLeft,
        DeviceOrientation.landscapeRight,
      ];
    }
    return const [DeviceOrientation.portraitUp, DeviceOrientation.portraitDown];
  }

  DeviceOrientation get captureOrientation {
    return recordingOrientation == 'landscape'
        ? DeviceOrientation.landscapeLeft
        : DeviceOrientation.portraitUp;
  }

  String get recordingOrientationLabel {
    return recordingOrientation == 'landscape' ? 'horizontal' : 'vertical';
  }

  ResolutionPreset get cameraResolution {
    switch (resolutionPreset) {
      case 'low':
        return ResolutionPreset.low;
      case 'medium':
        return ResolutionPreset.medium;
      case 'high':
        return ResolutionPreset.high;
      case 'ultraHigh':
        return ResolutionPreset.ultraHigh;
      case 'max':
        return ResolutionPreset.max;
      case 'veryHigh':
      default:
        return ResolutionPreset.veryHigh;
    }
  }

  int get gridColumns {
    switch (gridMode) {
      case '3x4':
        return 3;
      case '4x3':
        return 4;
      default:
        return 0;
    }
  }

  int get gridRows {
    switch (gridMode) {
      case '3x4':
        return 4;
      case '4x3':
        return 3;
      default:
        return 0;
    }
  }

  bool get showReticle => reticleMode != 'off';

  String get reticleLabel {
    switch (reticleMode) {
      case 'dot':
        return 'Dot';
      case 'cross':
        return 'Cross';
      case 'splitCross':
        return 'Split cross';
      case 'frameCross':
        return 'Frame cross';
      default:
        return 'Off';
    }
  }

  Map<String, Object?> toJson() {
    final size = targetSizeForPreset(resolutionPreset);
    return {
      'deviceSlot': deviceSlot,
      'deviceLabel': deviceLabel,
      'gridMode': gridMode,
      'reticleMode': reticleMode,
      'resolutionPreset': resolutionPreset,
      'width': size.$1,
      'height': size.$2,
      'aspectRatio': '${size.$1}:${size.$2}',
      'fps': fps,
      'fpsAppliedByPlugin': true,
      'recordingOrientation': recordingOrientation,
      'enableAudio': enableAudio,
      'keepScreenOn': keepScreenOn,
      'saveToGallery': saveToGallery,
      'filePrefix': filePrefix,
      'autoExposure': autoExposure,
      'autoFocus': autoFocus,
      'smartZoom': smartZoom,
      'zoomLevel': zoomLevel,
    };
  }

  static String _cleanLabel(String value) {
    return value
        .trim()
        .replaceAll(RegExp(r'\s+'), '_')
        .replaceAll(RegExp(r'[\\/:*?"<>|]+'), '_')
        .replaceAll(RegExp(r'_+'), '_')
        .replaceAll(RegExp(r'^_|_$'), '');
  }
}

class RenamedVideo {
  const RenamedVideo(this.file, this.metadata);

  final File file;
  final Map<String, Object?> metadata;
}

class CameraControlScreen extends StatefulWidget {
  const CameraControlScreen({super.key});

  @override
  State<CameraControlScreen> createState() => _CameraControlScreenState();
}

class _CameraControlScreenState extends State<CameraControlScreen>
    with WidgetsBindingObserver {
  CameraController? _camera;
  final _orientationManager = CameraOrientationManager(onLog: debugPrint);
  HttpServer? _server;
  RawDatagramSocket? _discoverySocket;
  AppSettings _settings = AppSettings.defaults();
  bool _recording = false;
  bool _booted = false;
  bool _fpsStreamActive = false;
  bool _cameraAutomationReady = false;
  String _status = 'Starting camera...';
  String _ip = 'checking...';
  double _actualFps = 0;
  double _minZoom = 1;
  double _maxZoom = 1;
  double _zoom = 1;
  double _zoomAtScaleStart = 1;
  int _fpsFrameCount = 0;
  DateTime? _fpsWindowStartedAt;
  String? _nativeDeviceId;
  String? _nativeDeviceName;
  String? _lastVideoPath;
  String? _lastVideoName;
  int? _lastVideoSizeBytes;
  Map<String, Object?>? _lastVideoMetadata;
  String? _activeVideoName;
  DateTime? _recordingStartedAt;
  String? _sessionId;
  String? _sessionCameraName;
  String? _sessionDate;
  String? _sessionTime;
  int? _sessionIndex;
  String _sessionSignerId = '';
  String _sessionSignerName = '';
  String _sessionSignerDir = '';
  String _sessionMode = 'word';
  String _sessionWord = '';
  String _sessionWordId = '';
  String _sessionList = '';
  String _sessionWordDir = '';
  String _sessionTakeLabel = 'a';
  int _sessionTakeNumber = 1;
  int _sessionGestureCount = 1;
  bool _sessionRetake = false;
  String _sessionAppVersion = appVersion;
  int _localIndex = 0;
  Future<void> _operation = Future.value();
  ConnectionSupervisor? _wsClient;
  String _wsStatus = 'idle';
  bool _reticleMenuOpen = false;
  bool _disposed = false;
  Timer? _serverWatchdogTimer;
  int _serverRestartAttempts = 0;
  int _discoveryRestartAttempts = 0;
  bool _serverRestartScheduled = false;
  bool _discoveryRestartScheduled = false;
  StreamSubscription<dynamic>? _connectivitySubscription;
  IOSink? _connectionLogSink;

  // Same backoff shape as the WS reconnect table in docs/failure_recovery.md
  // (1s, 2s, 4s, 8s, then 15s repeating) - reused here for restarting the local
  // HTTP/UDP sockets when Android's Doze/battery-saver kills them out from under us.
  static const List<int> _restartBackoffSeconds = [1, 2, 4, 8, 15];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _boot();
  }

  Future<void> _boot() async {
    _settings = (await AppSettings.load()).normalized();
    await _settings.save();
    await _applyPreferredOrientations();
    await _applyKeepScreenOn();
    await _acquireWakeLocks();
    unawaited(_requestBatteryOptimizationExemption());
    await _initCamera();
    await _startServer();
    await _loadIpAddress();
    await _refreshNativeStatus();
    await _startDiscovery();
    _startWsClient();
    _startServerWatchdog();
    if (!mounted) return;
    setState(() {
      _booted = true;
    });
  }

  // Keeps the CPU (and, separately, the Wi-Fi radio) from being suspended by
  // Android's Doze/App Standby once the battery gets low - see MainActivity.kt
  // acquireWakeLocks(). Safe to call even on native builds that predate this
  // method: the channel call just fails silently and the app runs as before.
  Future<void> _acquireWakeLocks() async {
    try {
      await mediaChannel.invokeMethod<bool>('acquireWakeLocks');
    } catch (_) {
      // Older native build without this method - degrade gracefully.
    }
  }

  // Prompts (once - Android remembers the choice) to exempt this app from battery
  // optimizations, which is what actually stops the OS from throttling background
  // network sockets when the automatic Battery Saver kicks in around 15%.
  Future<void> _requestBatteryOptimizationExemption() async {
    try {
      final ignoring = await mediaChannel.invokeMethod<bool>(
        'isIgnoringBatteryOptimizations',
      );
      if (ignoring != true) {
        await mediaChannel.invokeMethod<bool>('requestIgnoreBatteryOptimizations');
      }
    } catch (_) {
      // Older native build without this method - nothing to do.
    }
  }

  // Periodically confirms the control HTTP server is actually still answering
  // requests (not just that `_server` is non-null - Doze can kill the underlying
  // socket while the Dart object reference survives). A failed self-check forces a
  // rebind, closing the gap this bug report described: previously nothing detected
  // the dead server, so only a manual app relaunch via the bat script recovered it.
  void _startServerWatchdog() {
    _serverWatchdogTimer?.cancel();
    _serverWatchdogTimer = Timer.periodic(const Duration(seconds: 20), (_) {
      unawaited(_checkServerHealth());
    });
  }

  Future<void> _checkServerHealth() async {
    if (_disposed) return;
    if (_server == null) {
      _scheduleServerRestart();
      return;
    }
    final client = HttpClient();
    try {
      final request = await client
          .getUrl(Uri.parse('http://127.0.0.1:$controlPort/status'))
          .timeout(const Duration(seconds: 5));
      final response = await request.close().timeout(const Duration(seconds: 5));
      await response.drain<void>();
      if (response.statusCode != HttpStatus.ok) {
        _scheduleServerRestart();
      }
    } catch (_) {
      _scheduleServerRestart();
    } finally {
      client.close(force: true);
    }
  }

  void _scheduleServerRestart() {
    if (_disposed || _serverRestartScheduled) return;
    _serverRestartScheduled = true;
    final server = _server;
    _server = null;
    if (server != null) {
      unawaited(server.close(force: true).catchError((_) {}));
    }
    final delaySeconds = _restartBackoffSeconds[_serverRestartAttempts.clamp(
      0,
      _restartBackoffSeconds.length - 1,
    )];
    _serverRestartAttempts++;
    _setStatus('Server unresponsive, restarting in ${delaySeconds}s...');
    Timer(Duration(seconds: delaySeconds), () {
      _serverRestartScheduled = false;
      if (_disposed || _server != null) return;
      unawaited(_startServer());
    });
  }

  void _scheduleDiscoveryRestart() {
    if (_disposed || _discoveryRestartScheduled) return;
    _discoveryRestartScheduled = true;
    final socket = _discoverySocket;
    _discoverySocket = null;
    socket?.close();
    final delaySeconds = _restartBackoffSeconds[_discoveryRestartAttempts.clamp(
      0,
      _restartBackoffSeconds.length - 1,
    )];
    _discoveryRestartAttempts++;
    Timer(Duration(seconds: delaySeconds), () {
      _discoveryRestartScheduled = false;
      if (_disposed || _discoverySocket != null) return;
      unawaited(_startDiscovery());
    });
  }

  /// New WS+protobuf networking core (network_architecture.md), run alongside the
  /// legacy HTTP server above - per the migration rules, HTTP stays fully operational
  /// until the WS path is verified with real devices; this does not replace it yet.
  void _startWsClient() {
    _wsClient = ConnectionSupervisor(
      recordingController: _ScreenRecordingController(this),
      deviceStatusProvider: _nativeStatus,
      deviceLabel: _settings.deviceLabel,
      deviceSlot: _settings.deviceSlot,
      appVersion: appVersion,
      onStatusChanged: (status) {
        if (!mounted) return;
        setState(() {
          _wsStatus = status;
        });
      },
      onTelemetryEvent: _logConnectionTelemetry,
      // Circuit breaker tripped (audit §16 Layer 6): the WS path alone has failed
      // enough times to give up on the normal per-attempt backoff. Nudge the HTTP
      // server and UDP discovery socket too, so all three control-plane paths get a
      // coordinated clean slate instead of only WS quietly retrying forever.
      onFullResetRequested: () {
        _scheduleServerRestart();
        _scheduleDiscoveryRestart();
      },
    );
    _startConnectivityListener();
  }

  /// Bridges Kotlin's `ConnectivityManager.NetworkCallback` (MainActivity.kt
  /// registerNetworkCallback()) to [ConnectionSupervisor.onNetworkAvailable]/
  /// [ConnectionSupervisor.onNetworkLost] - audit §10: real OS connectivity events
  /// instead of polling as the primary signal.
  void _startConnectivityListener() {
    _connectivitySubscription?.cancel();
    _connectivitySubscription = connectivityEventChannel.receiveBroadcastStream().listen(
      (dynamic event) {
        if (event is! String) return;
        Map<String, dynamic> payload;
        try {
          payload = jsonDecode(event) as Map<String, dynamic>;
        } catch (_) {
          return;
        }
        final available = payload['available'] == true;
        final wifi = payload['wifi'] == true;
        if (available) {
          _wsClient?.onNetworkAvailable(wifi: wifi);
        } else {
          _wsClient?.onNetworkLost();
        }
      },
      onError: (_) {
        // The platform channel itself failing shouldn't take anything else down -
        // ConnectionSupervisor's own backoff/heartbeat-timeout paths still work as a
        // fallback, just without the immediate-retry-on-Wi-Fi-restore optimization.
      },
    );
  }

  /// Structured connection telemetry (audit §18) - appended as NDJSON, one file per day
  /// like the existing dashboard recording log convention (dashboard/three_cam_controller.py
  /// recording_event_write), so a connection-reliability incident can be reconstructed
  /// after the fact from the phone's own local file even if it never reached the Director.
  void _logConnectionTelemetry(ConnectionTelemetryEvent event) {
    final payload = event.toJson(
      deviceId: _wsClient?.deviceId ?? _nativeDeviceId,
      appInstanceId: _wsClient?.appInstanceId ?? '',
      connectionGeneration: _wsClient?.generation ?? 0,
    );
    unawaited(_appendConnectionLogLine(jsonEncode(payload)));
  }

  Future<void> _appendConnectionLogLine(String line) async {
    try {
      var sink = _connectionLogSink;
      if (sink == null) {
        final dir = await getApplicationDocumentsDirectory();
        final stamp = DateTime.now().toIso8601String().substring(0, 10);
        final file = File('${dir.path}/connection_log_$stamp.ndjson');
        sink = file.openWrite(mode: FileMode.append);
        _connectionLogSink = sink;
      }
      sink.writeln(line);
    } catch (_) {
      // Best-effort local diagnostics only - must never affect the connection itself.
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      unawaited(_applyKeepScreenOn());
      unawaited(_acquireWakeLocks());
      unawaited(_loadIpAddress());
      unawaited(_refreshNativeStatus());
      unawaited(_applyAutoExposureAndFocus());
      unawaited(_startFpsStream());
      // Coming back from background/screen-off is exactly when a Doze-killed
      // server/discovery socket would otherwise stay dead until a manual relaunch.
      unawaited(_checkServerHealth());
      if (_discoverySocket == null) {
        unawaited(_startDiscovery());
      }
    }
  }

  Future<void> _initCamera() async {
    try {
      final oldCamera = _camera;
      if (oldCamera != null) {
        await _stopFpsStream(oldCamera);
        _camera = null;
        await oldCamera.dispose();
      }
      _cameraAutomationReady = false;

      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        _setStatus('No camera found');
        return;
      }

      final backCamera = cameras.firstWhere(
        (camera) => camera.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first,
      );

      final controller = CameraController(
        backCamera,
        _settings.cameraResolution,
        enableAudio: _settings.enableAudio,
        fps: _settings.fps,
      );
      await controller.initialize();
      // A brand-new CameraController has no lock of its own regardless of what the
      // manager last applied to a previous (now-disposed) controller instance.
      _orientationManager.reset();
      await _orientationManager.apply(
        camera: controller,
        target: _settings.captureOrientation,
        preferredUiOrientations: _settings.preferredOrientations,
        force: true,
      );
      await _configureCameraAutomation(controller);
      await _startFpsStream(controller);

      if (!mounted) return;
      setState(() {
        _camera = controller;
        _status = 'Ready';
      });
    } catch (error) {
      _setStatus('Camera error: $error');
    }
  }

  Future<void> _configureCameraAutomation(CameraController camera) async {
    try {
      _minZoom = await camera.getMinZoomLevel();
      _maxZoom = await camera.getMaxZoomLevel();
      _zoom = _settings.zoomLevel.clamp(_minZoom, _maxZoom).toDouble();
      await camera.setZoomLevel(_zoom);
    } catch (_) {
      _minZoom = 1;
      _maxZoom = 1;
      _zoom = 1;
    }

    await _applyAutoExposureAndFocus(camera);
    _cameraAutomationReady = true;
  }

  Future<void> _applyAutoExposureAndFocus([
    CameraController? controller,
  ]) async {
    final camera = controller ?? _camera;
    if (camera == null || !camera.value.isInitialized) return;

    try {
      await camera.setExposureMode(
        _settings.autoExposure ? ExposureMode.auto : ExposureMode.locked,
      );
    } catch (_) {}

    try {
      await camera.setFocusMode(
        _settings.autoFocus ? FocusMode.auto : FocusMode.locked,
      );
    } catch (_) {}

    if (_settings.autoExposure) {
      try {
        await camera.setExposurePoint(null);
      } catch (_) {}
    }
    if (_settings.autoFocus) {
      try {
        await camera.setFocusPoint(null);
      } catch (_) {}
    }
  }

  Future<void> _startFpsStream([CameraController? controller]) async {
    final camera = controller ?? _camera;
    if (camera == null || !camera.value.isInitialized) return;
    if (_recording ||
        camera.value.isRecordingVideo ||
        camera.value.isStreamingImages) {
      return;
    }
    if (!camera.supportsImageStreaming()) return;

    try {
      _resetFpsCounter();
      await camera.startImageStream((_) => _trackFrame());
      _fpsStreamActive = true;
    } catch (_) {
      _fpsStreamActive = false;
    }
  }

  Future<void> _stopFpsStream([CameraController? controller]) async {
    final camera = controller ?? _camera;
    if (camera == null || !camera.value.isInitialized) return;
    if (!_fpsStreamActive && !camera.value.isStreamingImages) return;

    try {
      await camera.stopImageStream();
    } catch (_) {
      // The plugin can already have stopped the stream while switching modes.
    } finally {
      _fpsStreamActive = false;
    }
  }

  void _resetFpsCounter() {
    _fpsFrameCount = 0;
    _fpsWindowStartedAt = DateTime.now();
  }

  void _trackFrame() {
    final now = DateTime.now();
    final started = _fpsWindowStartedAt ?? now;
    _fpsWindowStartedAt ??= now;
    _fpsFrameCount++;

    final elapsedMs = now.difference(started).inMilliseconds;
    if (elapsedMs < 650) return;

    final nextFps = _fpsFrameCount * 1000 / elapsedMs;
    _fpsFrameCount = 0;
    _fpsWindowStartedAt = now;
    if (!mounted) return;
    setState(() {
      _actualFps = nextFps;
    });
  }

  Future<void> _startServer() async {
    try {
      final server = await HttpServer.bind(
        InternetAddress.anyIPv4,
        controlPort,
        shared: true,
      );
      _server = server;
      _serverRestartAttempts = 0;
      unawaited(_serve(server));
    } catch (error) {
      _setStatus('Server error: $error');
      _scheduleServerRestart();
    }
  }

  Future<void> _startDiscovery() async {
    try {
      final socket = await RawDatagramSocket.bind(
        InternetAddress.anyIPv4,
        discoveryPort,
        reuseAddress: true,
        reusePort: true,
      );
      _discoverySocket = socket;
      _discoveryRestartAttempts = 0;
      socket.listen(
        (event) {
          if (event != RawSocketEvent.read) return;
          final datagram = socket.receive();
          if (datagram == null) return;

          final message = utf8.decode(datagram.data, allowMalformed: true).trim();
          if (message != discoveryMessage) return;

          final payload = jsonEncode({
            'app': 'three_cam',
            'name': _settings.deviceLabel,
            'deviceId': _nativeDeviceId ?? Platform.localHostname,
            'deviceName': _nativeDeviceName ?? Platform.localHostname,
            'deviceSlot': _settings.deviceSlot,
            'deviceLabel': _settings.deviceLabel,
            'ip': _ip,
            'port': controlPort,
            'recording': _recording,
            'actualFps': _actualFps,
            'zoom': _zoom,
            'settings': _settings.toJson(),
          });
          socket.send(utf8.encode(payload), datagram.address, datagram.port);

          // The discovery probe's sender is the PC - this is also the address the new
          // WS client connects out to (network_architecture.md §Discovery Layer: the
          // wire format is unchanged, but the same packet now also bootstraps the WS
          // connection instead of requiring a separate discovery step for it).
          unawaited(_wsClient?.connectTo(datagram.address.address));
        },
        onError: (_) {
          if (identical(_discoverySocket, socket)) {
            _scheduleDiscoveryRestart();
          }
        },
        onDone: () {
          if (identical(_discoverySocket, socket)) {
            _discoverySocket = null;
            _scheduleDiscoveryRestart();
          }
        },
      );
    } catch (error) {
      _setStatus('Discovery error: $error');
      _scheduleDiscoveryRestart();
    }
  }

  Future<void> _serve(HttpServer server) async {
    try {
      await for (final request in server) {
        try {
        final path = request.uri.path;
        if (path == '/start') {
          final params = request.uri.queryParameters;
          await _queue(
            () => _startRecording(
              cameraName: params['camera'],
              sessionId: params['session'],
              date: params['date'],
              time: params['time'],
              index: int.tryParse(params['index'] ?? ''),
              signerId: params['signer_id'],
              signerName: params['signer_name'],
              signerDir: params['signer_dir'],
              mode: params['mode'],
              word: params['word'],
              wordId: params['word_id'],
              listName: params['list'],
              wordDir: params['word_dir'],
              takeLabel: params['take_label'],
              takeNumber: int.tryParse(params['take_number'] ?? ''),
              gestureCount: int.tryParse(params['gesture_count'] ?? ''),
              retake: params['retake'] == '1',
              controllerAppVersion: params['app_version'],
            ),
          );
          _sendJson(request, {
            'ok': true,
            'recording': _recording,
            'activeVideoName': _activeVideoName,
            'sessionId': _sessionId,
            'deviceId': _nativeDeviceId,
            'deviceSlot': _settings.deviceSlot,
            'deviceLabel': _settings.deviceLabel,
          });
        } else if (path == '/stop') {
          await _queue(_stopRecording);
          _sendJson(request, {
            'ok': true,
            'recording': _recording,
            'lastVideoPath': _lastVideoPath,
            'lastVideoName': _lastVideoName,
            'lastVideoSizeBytes': _lastVideoSizeBytes,
            'lastVideoMetadata': _lastVideoMetadata,
            'recordIndex': _lastVideoMetadata?['recordIndex'],
            'startedAt': _lastVideoMetadata?['started_at'],
            'stoppedAt': _lastVideoMetadata?['stopped_at'],
            'sessionId': _sessionId,
            'deviceId': _nativeDeviceId,
            'deviceSlot': _settings.deviceSlot,
            'deviceLabel': _settings.deviceLabel,
          });
        } else if (path == '/toggle') {
          await _queue(_toggleRecording);
          _sendJson(request, {
            'ok': true,
            'recording': _recording,
            'lastVideoPath': _lastVideoPath,
            'lastVideoName': _lastVideoName,
            'lastVideoSizeBytes': _lastVideoSizeBytes,
            'lastVideoMetadata': _lastVideoMetadata,
            'recordIndex': _lastVideoMetadata?['recordIndex'],
            'startedAt': _lastVideoMetadata?['started_at'],
            'stoppedAt': _lastVideoMetadata?['stopped_at'],
            'sessionId': _sessionId,
            'deviceId': _nativeDeviceId,
            'deviceSlot': _settings.deviceSlot,
            'deviceLabel': _settings.deviceLabel,
          });
        } else if (path == '/status') {
          _sendJson(request, await _statusJson());
        } else if (path == '/videos') {
          final videos = await _listVideos();
          _sendJson(request, {'ok': true, 'videos': videos});
        } else if (path == '/clear-videos') {
          final deleted = await _clearVideos();
          _sendJson(request, {'ok': true, 'deleted': deleted});
        } else if (path == '/reset-index') {
          await _resetIndex();
          _sendJson(request, {'ok': true, 'nextIndex': _localIndex});
        } else if (path == '/mark-video-error') {
          final updated = await _markVideoError(
            request.uri.queryParameters['path'] ?? '',
            superseded: request.uri.queryParameters['superseded'] == '1',
          );
          _sendJson(request, {'ok': true, 'video': updated});
        } else if (path == '/mark-video-superseded') {
          final updated = await _markVideoSuperseded(
            request.uri.queryParameters['path'] ?? '',
          );
          _sendJson(request, {'ok': true, 'video': updated});
        } else if (path == '/download') {
          await _sendVideoFile(request);
        } else {
          request.response.statusCode = HttpStatus.notFound;
          _sendJson(request, {'ok': false, 'error': 'unknown endpoint'});
        }
      } catch (error) {
        request.response.statusCode = HttpStatus.internalServerError;
        _sendJson(request, {'ok': false, 'error': '$error'});
      }
      }
    } catch (error) {
      _setStatus('Server loop error: $error');
    } finally {
      // The await-for loop above only returns when the server's socket closes -
      // either we closed it on purpose (dispose(), or _scheduleServerRestart()
      // replacing a dead one - both already null out `_server` before doing so, so
      // `identical` below is false for those and we correctly skip re-restarting),
      // or Android's Doze/battery-saver silently killed the underlying socket, which
      // is exactly the case this should recover from.
      if (!_disposed && identical(_server, server)) {
        _server = null;
        _scheduleServerRestart();
      }
    }
  }

  Future<void> _queue(Future<void> Function() action) {
    _operation = _operation.then((_) => action());
    return _operation;
  }

  Future<Map<String, Object?>> _statusJson() async {
    final nativeStatus = await _nativeStatus();
    return {
      'ok': true,
      'deviceId': nativeStatus['deviceId'] ?? _nativeDeviceId,
      'deviceName': nativeStatus['deviceName'] ?? _nativeDeviceName,
      'deviceSlot': _settings.deviceSlot,
      'deviceLabel': _settings.deviceLabel,
      'recording': _recording,
      'status': _status,
      'ip': _ip,
      'port': controlPort,
      'actualFps': _actualFps,
      'zoom': _zoom,
      'minZoom': _minZoom,
      'maxZoom': _maxZoom,
      'autoExposure': _settings.autoExposure,
      'autoFocus': _settings.autoFocus,
      'cameraAutomationReady': _cameraAutomationReady,
      'freeStorageBytes': nativeStatus['freeStorageBytes'],
      'totalStorageBytes': nativeStatus['totalStorageBytes'],
      'batteryPercent': nativeStatus['batteryPercent'],
      'batteryCharging': nativeStatus['batteryCharging'],
      'sessionId': _sessionId,
      'activeVideoName': _activeVideoName,
      'recordingStartedAt': _recordingStartedAt?.toIso8601String(),
      'targetVideo': _settings.toJson(),
      'lastVideoPath': _lastVideoPath,
      'lastVideoName': _lastVideoName,
      'lastVideoSizeBytes': _lastVideoSizeBytes,
      'sessionSignerId': _sessionSignerId,
      'sessionMode': _sessionMode,
      'sessionWord': _sessionWord,
      'sessionTakeLabel': _sessionTakeLabel,
    };
  }

  Future<Map<String, Object?>> _nativeStatus() async {
    try {
      final result = await mediaChannel.invokeMapMethod<String, Object?>(
        'getDeviceStatus',
      );
      final status = result ?? {};
      _nativeDeviceId = '${status['deviceId'] ?? Platform.localHostname}';
      _nativeDeviceName = '${status['deviceName'] ?? Platform.localHostname}';
      return status;
    } catch (_) {
      return {
        'deviceId': Platform.localHostname,
        'deviceName': Platform.localHostname,
        'freeStorageBytes': null,
      };
    }
  }

  Future<void> _refreshNativeStatus() async {
    await _nativeStatus();
  }

  Future<void> _applyKeepScreenOn() async {
    try {
      await mediaChannel.invokeMethod<bool>('setKeepScreenOn', {
        'enabled': _settings.keepScreenOn,
      });
    } catch (_) {
      // Older builds without the native method still run; Android will just use
      // the system's normal screen timeout.
    }
  }

  Future<void> _applyPreferredOrientations() {
    return SystemChrome.setPreferredOrientations(
      _settings.preferredOrientations,
    );
  }

  void _sendJson(HttpRequest request, Map<String, Object?> payload) {
    request.response.headers.contentType = ContentType.json;
    request.response.write(jsonEncode(payload));
    unawaited(request.response.close());
  }

  Future<void> _loadIpAddress() async {
    try {
      final interfaces = await NetworkInterface.list(
        includeLoopback: false,
        type: InternetAddressType.IPv4,
      );
      final addresses = interfaces
          .expand((interface) => interface.addresses)
          .map((address) => address.address)
          .where((address) => !address.startsWith('127.'))
          .toList();
      final ip = addresses.isEmpty ? 'not connected' : addresses.first;
      _wsClient?.updateKnownIp(ip);
      if (!mounted) return;
      setState(() {
        _ip = ip;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _ip = 'unknown';
      });
    }
  }

  Future<void> _toggleRecording() async {
    if (_recording) {
      await _stopRecording();
    } else {
      await _startRecording();
    }
  }

  Future<void> _startRecording({
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
    String? listName,
    String? wordDir,
    String? takeLabel,
    int? takeNumber,
    int? gestureCount,
    bool? retake,
    String? controllerAppVersion,
  }) async {
    final camera = _camera;
    if (camera == null || !camera.value.isInitialized) {
      throw StateError('Camera is not ready');
    }
    if (_recording || camera.value.isRecordingVideo) {
      throw StateError('Already recording session ${_sessionId ?? 'unknown'}');
    }

    final now = DateTime.now();
    _lastVideoPath = null;
    _lastVideoName = null;
    _lastVideoSizeBytes = null;
    _lastVideoMetadata = null;
    _sessionCameraName = _cleanName(cameraName ?? _settings.deviceLabel);
    _sessionDate = date ?? _dateStamp(now);
    _sessionTime = time ?? _timeStamp(now);
    _sessionIndex = index ?? await _nextLocalIndex();
    _localIndex = _sessionIndex! + 1;
    _sessionSignerId = _cleanName(signerId ?? 'signer');
    _sessionSignerName = (signerName ?? _sessionSignerId).trim();
    _sessionSignerDir = _cleanName(signerDir ?? _sessionSignerName);
    _sessionMode = _cleanName(mode ?? 'word');
    _sessionWord =
        (word ?? (_sessionMode == 'background' ? 'background' : 'word')).trim();
    _sessionWordId = (wordId ?? '').trim();
    _sessionList = (listName ?? '').trim();
    _sessionWordDir = _cleanName(wordDir ?? _sessionWord);
    _sessionTakeNumber = (takeNumber ?? 1).clamp(1, 9999);
    _sessionTakeLabel = _cleanName(takeLabel ?? _takeLabel(_sessionTakeNumber));
    _sessionGestureCount = (gestureCount ?? 1).clamp(1, 9999);
    _sessionRetake = retake ?? false;
    _sessionAppVersion = (controllerAppVersion ?? appVersion).trim().isEmpty
        ? appVersion
        : controllerAppVersion!.trim();
    _sessionId =
        sessionId ??
        '${_compactDateStamp(now)}_${_timeStamp(now)}_$_sessionIndex';
    _activeVideoName = _recordingFileName(
      cameraName: _sessionCameraName!,
      date: _sessionDate!,
      time: _sessionTime!,
      index: _sessionIndex!,
      mode: _sessionMode,
      word: _sessionWord,
      wordDir: _sessionWordDir,
      takeLabel: _sessionTakeLabel,
      retake: _sessionRetake,
    );
    _recordingStartedAt = now;

    await _stopFpsStream(camera);
    _resetFpsCounter();
    // Deliberately NOT re-locking capture orientation here. Orientation is now always
    // established the instant it's decided - at camera init and at settings save (see
    // CameraOrientationManager) - never deferred to this point. A native
    // lockCaptureOrientation call sitting on the record-start path was the actual root
    // cause of the visible rotation-on-START bug (it was often the first time a changed
    // orientation setting actually reached the camera) and would also add avoidable
    // jitter right on the ScheduledCommand execute_at path. This is a read-only check.
    _orientationManager.logPreRecordState(camera);
    await camera.startVideoRecording(onAvailable: (_) => _trackFrame());
    debugPrint(
      'ThreeCam: after startVideoRecording deviceOrientation=${camera.value.deviceOrientation} '
      'lockedCaptureOrientation=${camera.value.lockedCaptureOrientation}',
    );
    _fpsStreamActive = true;
    _recording = true;
    _status = 'Recording';
    if (mounted) {
      setState(() {});
    }
  }

  Future<void> _stopRecording() async {
    final camera = _camera;
    if (camera == null || !camera.value.isInitialized) {
      throw StateError('Camera is not ready');
    }
    if (!_recording && !camera.value.isRecordingVideo) {
      throw StateError('Camera is not recording');
    }

    final file = await camera.stopVideoRecording();
    final stoppedCameraName = _sessionCameraName;
    final stoppedDate = _sessionDate;
    final stoppedTime = _sessionTime;
    final stoppedIndex = _sessionIndex;
    _fpsStreamActive = false;
    _recording = false;
    _status = 'Saving';
    if (mounted) {
      setState(() {});
    }
    await _saveStoppedVideo(
      file,
      cameraName: stoppedCameraName,
      date: stoppedDate,
      time: stoppedTime,
      index: stoppedIndex,
    );
    unawaited(_startFpsStream(camera));
  }

  Future<void> _saveStoppedVideo(
    XFile file, {
    String? cameraName,
    String? date,
    String? time,
    int? index,
  }) async {
    try {
      final savedPath = await _saveVideo(
        file,
        cameraName: cameraName,
        date: date,
        time: time,
        index: index,
      );
      _lastVideoPath = savedPath;
      if (!mounted) return;
      setState(() {
        _status = 'Saved';
      });
    } catch (error) {
      if (mounted) {
        setState(() {
          _status = 'Save error: $error';
        });
      }
      rethrow;
    }
  }

  Future<String> _saveVideo(
    XFile file, {
    String? cameraName,
    String? date,
    String? time,
    int? index,
  }) async {
    final now = DateTime.now();
    final savedCameraName = _cleanName(cameraName ?? _settings.deviceLabel);
    final savedDate = date ?? _dateStamp(now);
    final savedTime = time ?? _timeStamp(now);
    final savedIndex = index ?? await _nextLocalIndex();
    _localIndex = savedIndex + 1;
    final fileName = _recordingFileName(
      cameraName: savedCameraName,
      date: savedDate,
      time: savedTime,
      index: savedIndex,
      mode: _sessionMode,
      word: _sessionWord,
      wordDir: _sessionWordDir,
      takeLabel: _sessionTakeLabel,
      retake: _sessionRetake,
    );
    final mirrorDir = await _videoDir(
      signerDir: _sessionSignerDir,
      wordDir: _sessionMode == 'background' ? 'background' : _sessionWordDir,
    );
    final mirrorPath = '${mirrorDir.path}/$fileName';
    await File(file.path).copy(mirrorPath);
    _lastVideoName = fileName;
    final copiedVideo = File(mirrorPath);
    _lastVideoSizeBytes = await copiedVideo.length();
    if ((_lastVideoSizeBytes ?? 0) <= 0) {
      if (await copiedVideo.exists()) {
        await copiedVideo.delete();
      }
      throw StateError('Saved video is empty: $fileName');
    }
    final metadata = _videoMetadataPayload(
      savedCameraName: savedCameraName,
      savedIndex: savedIndex,
      sizeBytes: _lastVideoSizeBytes ?? 0,
    );
    _lastVideoMetadata = metadata;
    try {
      await _writeVideoMetadata(copiedVideo, metadata);
    } catch (_) {
      if (await copiedVideo.exists()) {
        await copiedVideo.delete();
      }
      _lastVideoMetadata = null;
      rethrow;
    }
    _activeVideoName = null;
    _recordingStartedAt = null;

    if (!_settings.saveToGallery) {
      return mirrorPath;
    }

    try {
      final path = await mediaChannel.invokeMethod<String>('saveVideoToDcim', {
        'sourcePath': mirrorPath,
        'displayName': fileName,
        'relativeDir':
            'ThreeCam/$_sessionSignerDir/${_sessionMode == 'background' ? 'background' : _sessionWordDir}',
      });
      return path ?? 'DCIM/ThreeCam/$fileName';
    } catch (_) {
      return mirrorPath;
    }
  }

  Map<String, Object?> _videoMetadataPayload({
    required String savedCameraName,
    required int savedIndex,
    required int sizeBytes,
  }) {
    final startedAt = _recordingStartedAt;
    final finishedAt = DateTime.now();
    final durationMs = startedAt == null
        ? null
        : finishedAt.difference(startedAt).inMilliseconds;
    final signerNumber = _signerNumber(_sessionSignerId);
    final globalIndex = int.tryParse(_sessionWordId);
    final status = sizeBytes > 0 ? 'ok' : 'error';
    return {
      'record': savedIndex,
      'signer': _sessionSignerId,
      'word_id': globalIndex,
      'word': _sessionWord,
      'take': _sessionTakeLabel,
      'device': _settings.deviceSlot,
      'started_at': startedAt?.toIso8601String(),
      'stopped_at': finishedAt.toIso8601String(),
      'duration_ms': durationMs,
      'size_bytes': sizeBytes,
      'status': status,
      'app_version': _sessionAppVersion,
      'session_id': _sessionId,
      'signer_id': signerNumber,
      'signer_name': _sessionSignerName,
      'list': _sessionList,
      'global_index': globalIndex ?? savedIndex,
      'gloss_uz': _sessionWord,
      'takeNumberValue': _sessionTakeNumber,
      'camera': savedCameraName,
      'sync_offset_ms': 0,
      'mobile_app_version': appVersion,
      'device_id': _nativeDeviceId ?? _settings.deviceLabel,
      'device_name': _nativeDeviceName,
      'superseded': false,
      'created_at': finishedAt.toIso8601String(),
      'signerId': _sessionSignerId,
      'signerName': _sessionSignerName,
      'signerDir': _sessionSignerDir,
      'mode': _sessionMode,
      'wordId': _sessionWordId,
      'wordDir': _sessionWordDir,
      'takeLabel': _sessionTakeLabel,
      'takeNumber': _sessionTakeNumber,
      'gestureCount': _sessionGestureCount,
      'recordIndex': savedIndex,
      'deviceId': _nativeDeviceId,
      'deviceName': _nativeDeviceName,
      'deviceLabel': _settings.deviceLabel,
      'cameraName': savedCameraName,
      'sessionId': _sessionId,
      'createdAt': finishedAt.toIso8601String(),
    };
  }

  Future<Directory> _videoDir({String? signerDir, String? wordDir}) async {
    final baseDir = await getExternalStorageDirectory();
    var path = '${baseDir?.path ?? Directory.systemTemp.path}/ThreeCamVideos';
    if (signerDir != null && signerDir.isNotEmpty) {
      path = '$path/${_cleanName(signerDir)}';
    }
    if (wordDir != null && wordDir.isNotEmpty) {
      path = '$path/${_cleanName(wordDir)}';
    }
    final dir = Directory(path);
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  String _dateStamp(DateTime value) {
    return [
      value.year.toString().padLeft(4, '0'),
      value.month.toString().padLeft(2, '0'),
      value.day.toString().padLeft(2, '0'),
    ].join(' ');
  }

  String _timeStamp(DateTime value) {
    return [
      value.hour.toString().padLeft(2, '0'),
      value.minute.toString().padLeft(2, '0'),
      value.second.toString().padLeft(2, '0'),
    ].join();
  }

  String _compactDateStamp(DateTime value) {
    return [
      value.year.toString().padLeft(4, '0'),
      value.month.toString().padLeft(2, '0'),
      value.day.toString().padLeft(2, '0'),
    ].join();
  }

  int? _signerNumber(String value) {
    final match = RegExp(r'(\d+)').firstMatch(value);
    return match == null ? null : int.tryParse(match.group(1)!);
  }

  String _cleanName(String value) {
    final cleaned = value
        .trim()
        .replaceAll(RegExp(r'\s+'), '_')
        .replaceAll(RegExp(r'[\\/:*?"<>|]+'), '_')
        .replaceAll(RegExp(r'_+'), '_')
        .replaceAll(RegExp(r'^_|_$'), '');
    return cleaned.isEmpty ? 'camera' : cleaned;
  }

  String _recordingFileName({
    required String cameraName,
    required String date,
    required String time,
    required int index,
    String mode = 'word',
    String word = 'word',
    String wordDir = 'word',
    String takeLabel = 'a',
    bool retake = false,
  }) {
    final prefix = _settings.filePrefix.isEmpty
        ? ''
        : '${_cleanName(_settings.filePrefix)}_';
    final compactDate = date.replaceAll(RegExp(r'\s+'), '');
    final base = mode == 'background'
        ? 'background'
        : _cleanName(wordDir.isEmpty ? word : wordDir);
    final retakePart = retake ? '_retake' : '';
    return '$prefix${base}_${_cleanName(takeLabel)}${retakePart}_${_cleanName(cameraName)}_${compactDate}_${time}_$index.mp4';
  }

  String _takeLabel(int takeNumber) {
    var value = takeNumber < 1 ? 1 : takeNumber;
    var label = '';
    while (value > 0) {
      value -= 1;
      label = String.fromCharCode('a'.codeUnitAt(0) + (value % 26)) + label;
      value ~/= 26;
    }
    return label;
  }

  Future<int> _nextLocalIndex() async {
    final dir = await _videoDir();
    if (!await dir.exists()) return _localIndex < 0 ? 0 : _localIndex;
    final indexes = <int>[];
    await for (final entity in dir.list(recursive: true)) {
      if (entity is! File || !entity.path.endsWith('.mp4')) continue;
      final name = entity.uri.pathSegments.last;
      final match = RegExp(r'_(\d+)\.mp4$').firstMatch(name);
      if (match == null) continue;
      final index = int.tryParse(match.group(1)!);
      if (index != null) indexes.add(index);
    }
    if (indexes.isEmpty) return _localIndex < 0 ? 0 : _localIndex;
    indexes.sort();
    final nextFromFiles = indexes.last + 1;
    return nextFromFiles > _localIndex ? nextFromFiles : _localIndex;
  }

  Future<void> _writeVideoMetadata(
    File videoFile,
    Map<String, Object?> data,
  ) async {
    final metadata = File(
      videoFile.path.replaceFirst(RegExp(r'\.mp4$'), '.json'),
    );
    final payload = {
      ...data,
      'fileName': videoFile.uri.pathSegments.last,
      'relativePath': await _relativeVideoPath(videoFile),
    };
    await metadata.writeAsString(jsonEncode(payload), flush: true);
  }

  Future<Map<String, Object?>> _readVideoMetadata(File videoFile) async {
    final metadata = File(
      videoFile.path.replaceFirst(RegExp(r'\.mp4$'), '.json'),
    );
    if (!await metadata.exists()) {
      return {};
    }
    try {
      final decoded = jsonDecode(await metadata.readAsString());
      return decoded is Map<String, Object?> ? decoded : {};
    } catch (_) {
      return {};
    }
  }

  Future<String> _relativeVideoPath(File file) async {
    final root = await _videoDir();
    final rootPath = root.path.endsWith(Platform.pathSeparator)
        ? root.path
        : '${root.path}${Platform.pathSeparator}';
    if (file.path.startsWith(rootPath)) {
      return file.path.substring(rootPath.length).replaceAll('\\', '/');
    }
    return file.uri.pathSegments.last;
  }

  Future<File> _videoFileFromRelativePath(String relativePath) async {
    if (relativePath.isEmpty ||
        relativePath.contains('..') ||
        relativePath.startsWith('/') ||
        relativePath.startsWith('\\')) {
      throw ArgumentError('bad path');
    }
    final root = await _videoDir();
    final parts = relativePath
        .split(RegExp(r'[\\/]'))
        .where((part) => part.isNotEmpty);
    return File([root.path, ...parts].join(Platform.pathSeparator));
  }

  Future<int> _clearVideos() async {
    if (_recording) {
      throw StateError('Stop recording before clearing videos');
    }

    final dir = await _videoDir();
    if (!await dir.exists()) {
      final galleryDeleted = await _deleteDcimVideos();
      _localIndex = 0;
      return galleryDeleted;
    }

    var deleted = 0;
    await for (final entity in dir.list(recursive: true)) {
      if (entity is! File) {
        continue;
      }
      if (!entity.path.endsWith('.mp4') && !entity.path.endsWith('.json')) {
        continue;
      }
      await entity.delete();
      deleted++;
    }
    deleted += await _deleteDcimVideos();

    _localIndex = 0;
    _lastVideoPath = null;
    _lastVideoName = null;
    _lastVideoSizeBytes = null;
    _activeVideoName = null;
    _recordingStartedAt = null;
    _sessionIndex = null;
    return deleted;
  }

  Future<int> _deleteDcimVideos() async {
    try {
      return await mediaChannel.invokeMethod<int>('deleteThreeCamDcimVideos') ??
          0;
    } catch (_) {
      return 0;
    }
  }

  Future<void> _resetIndex() async {
    if (_recording) {
      throw StateError('Stop recording before resetting index');
    }
    _localIndex = 0;
    _sessionIndex = null;
  }

  Future<List<Map<String, Object?>>> _listVideos() async {
    final dir = await _videoDir();
    final files = await dir
        .list(recursive: true)
        .where((entity) => entity is File && entity.path.endsWith('.mp4'))
        .cast<File>()
        .toList();
    files.sort(
      (a, b) => b.statSync().modified.compareTo(a.statSync().modified),
    );
    final result = <Map<String, Object?>>[];
    for (final file in files) {
      result.add(await _videoListItem(file));
    }
    return result;
  }

  Future<Map<String, Object?>> _videoListItem(File file) async {
    final stat = await file.stat();
    final metadata = await _readVideoMetadata(file);
    final relativePath = await _relativeVideoPath(file);
    final fallbackStatus =
        metadata['superseded'] == true ||
            file.uri.pathSegments.last.startsWith('RETAKE_') ||
            file.uri.pathSegments.last.endsWith('_SUPERSEDED.mp4')
        ? 'superseded'
        : (file.uri.pathSegments.last.startsWith('BAD_') ||
                  file.uri.pathSegments.last.startsWith('ERROR_') ||
                  file.uri.pathSegments.last.endsWith('_BAD.mp4') ||
                  file.uri.pathSegments.last.endsWith('_INCOMPLETE.mp4')
              ? 'error'
              : 'ok');
    final status = '${metadata['status'] ?? fallbackStatus}';
    return {
      ...metadata,
      'name': file.uri.pathSegments.last,
      'relativePath': relativePath,
      'size': stat.size,
      'modified': stat.modified.toIso8601String(),
      'deviceSlot': _settings.deviceSlot,
      'deviceLabel': _settings.deviceLabel,
      'status': status,
      'isError': status == 'error',
    };
  }

  Future<Map<String, Object?>> _markVideoError(
    String relativePath, {
    bool superseded = false,
  }) async {
    if (_recording) {
      throw StateError('Stop recording before marking errors');
    }
    final file = await _videoFileFromRelativePath(relativePath);
    if (!await file.exists() || !file.path.endsWith('.mp4')) {
      throw StateError('Video not found');
    }
    final renamed = await _renameVideoWithMetadata(file, '_BAD');
    final updatedFile = renamed.file;
    final metadata = renamed.metadata;
    await _renameDcimVideo(relativePath, updatedFile.uri.pathSegments.last);
    metadata['status'] = 'error';
    metadata['superseded'] = superseded;
    metadata['errorMarkedAt'] = DateTime.now().toIso8601String();
    metadata['error_marked_at'] = metadata['errorMarkedAt'];
    if (superseded) {
      metadata['superseded_at'] = metadata['errorMarkedAt'];
      metadata['supersededAt'] = metadata['superseded_at'];
    }
    await _writeVideoMetadata(updatedFile, metadata);
    return _videoListItem(updatedFile);
  }

  Future<Map<String, Object?>> _markVideoSuperseded(String relativePath) async {
    if (_recording) {
      throw StateError('Stop recording before marking retakes');
    }
    final file = await _videoFileFromRelativePath(relativePath);
    if (!await file.exists() || !file.path.endsWith('.mp4')) {
      throw StateError('Video not found');
    }
    final renamed = await _renameVideoWithMetadata(file, '_SUPERSEDED');
    final updatedFile = renamed.file;
    final metadata = renamed.metadata;
    await _renameDcimVideo(relativePath, updatedFile.uri.pathSegments.last);
    metadata['status'] = 'superseded';
    metadata['superseded'] = true;
    metadata['superseded_at'] = DateTime.now().toIso8601String();
    metadata['supersededAt'] = metadata['superseded_at'];
    await _writeVideoMetadata(updatedFile, metadata);
    return _videoListItem(updatedFile);
  }

  Future<RenamedVideo> _renameVideoWithMetadata(
    File file,
    String suffix,
  ) async {
    final name = file.uri.pathSegments.last;
    final alreadyMarked =
        name.startsWith('BAD_') ||
        name.startsWith('RETAKE_') ||
        name.startsWith('ERROR_') ||
        name.endsWith('_BAD.mp4') ||
        name.endsWith('_SUPERSEDED.mp4') ||
        name.endsWith('_INCOMPLETE.mp4');
    final stem = name.replaceFirst(RegExp(r'\.mp4$'), '');
    final target = alreadyMarked
        ? file
        : File('${file.parent.path}${Platform.pathSeparator}$stem$suffix.mp4');
    final metadata = await _readVideoMetadata(file);
    final oldMetadata = File(
      file.path.replaceFirst(RegExp(r'\.mp4$'), '.json'),
    );
    final updatedFile = target.path == file.path
        ? file
        : await file.rename(target.path);
    final newMetadata = File(
      updatedFile.path.replaceFirst(RegExp(r'\.mp4$'), '.json'),
    );
    if (await oldMetadata.exists() && oldMetadata.path != newMetadata.path) {
      await oldMetadata.rename(newMetadata.path);
    }
    return RenamedVideo(updatedFile, metadata);
  }

  Future<void> _renameDcimVideo(
    String relativePath,
    String newDisplayName,
  ) async {
    try {
      await mediaChannel.invokeMethod<bool>('markDcimVideoError', {
        'relativePath': relativePath,
        'newDisplayName': newDisplayName,
      });
    } catch (_) {
      // App-storage remains the source of truth if the gallery mirror is gone.
    }
  }

  Future<void> _sendVideoFile(HttpRequest request) async {
    final name =
        request.uri.queryParameters['path'] ??
        request.uri.queryParameters['name'];
    if (name == null) {
      request.response.statusCode = HttpStatus.badRequest;
      _sendJson(request, {'ok': false, 'error': 'bad name'});
      return;
    }

    final file = await _videoFileFromRelativePath(name);
    if (!await file.exists()) {
      request.response.statusCode = HttpStatus.notFound;
      _sendJson(request, {'ok': false, 'error': 'not found'});
      return;
    }

    request.response.headers.contentType = ContentType('video', 'mp4');
    request.response.headers.set(
      'Content-Disposition',
      'attachment; filename="$name"',
    );
    await file.openRead().pipe(request.response);
  }

  Future<void> _openSettings() async {
    if (_recording) {
      _showSnack('Stop recording before changing settings');
      return;
    }

    final next = await Navigator.of(context).push<AppSettings>(
      MaterialPageRoute(
        builder: (_) => SettingsScreen(initialSettings: _settings),
      ),
    );
    if (next == null) return;

    final normalized = next.normalized();
    final shouldRestart = _settings.needsCameraRestart(normalized);
    setState(() {
      _settings = normalized;
      _status = shouldRestart ? 'Applying settings...' : _status;
    });
    await _settings.save();
    await _applyPreferredOrientations();
    await _applyKeepScreenOn();
    if (shouldRestart) {
      // _initCamera() re-locks orientation on the fresh controller by itself.
      await _initCamera();
    } else {
      await _applyAutoExposureAndFocus();
      await _setZoom(normalized.zoomLevel, persist: false);
      // needsCameraRestart() deliberately does NOT cover recordingOrientation (a full
      // camera reinit is unnecessary just to change orientation) - but the capture-
      // orientation lock still has to be re-applied right here, immediately, whenever
      // it changed. Without this, the camera silently kept recording under the OLD
      // orientation until the next START, where a leftover redundant lock call used to
      // apply the new orientation for the first time - a visible rotation snap exactly
      // when the operator pressed START. See CameraOrientationManager's doc comment.
      final camera = _camera;
      if (camera != null && camera.value.isInitialized) {
        await _orientationManager.apply(
          camera: camera,
          target: _settings.captureOrientation,
          preferredUiOrientations: _settings.preferredOrientations,
        );
      }
    }
    _showSnack('Settings saved');
  }

  Future<void> _setZoom(double value, {bool persist = true}) async {
    final camera = _camera;
    if (camera == null || !camera.value.isInitialized) return;

    final next = value.clamp(_minZoom, _maxZoom).toDouble();
    try {
      await camera.setZoomLevel(next);
      if (!mounted) return;
      setState(() {
        _zoom = next;
        _settings = _settings.copyWith(zoomLevel: next).normalized();
      });
      if (persist) {
        await _settings.save();
      }
    } catch (_) {
      _showSnack('Zoom is not supported on this camera');
    }
  }

  Future<void> _zoomBy(double delta) async {
    final step = _settings.smartZoom ? _smartZoomStep() : 0.25;
    await _setZoom(_zoom + (delta * step));
  }

  Future<void> _setReticleMode(String mode) async {
    final nextSettings = _settings.copyWith(reticleMode: mode).normalized();
    setState(() {
      _settings = nextSettings;
      _reticleMenuOpen = false;
    });
    await nextSettings.save();
  }

  double _smartZoomStep() {
    final range = (_maxZoom - _minZoom).abs();
    if (range <= 1) return 0.1;
    if (_zoom < 2) return 0.15;
    if (_zoom < 5) return 0.35;
    return range / 12;
  }

  void _handleScaleStart(ScaleStartDetails details) {
    _zoomAtScaleStart = _zoom;
  }

  void _handleScaleUpdate(ScaleUpdateDetails details) {
    if (details.pointerCount < 2) return;
    final target = _settings.smartZoom
        ? _zoomAtScaleStart * details.scale
        : _zoomAtScaleStart + (details.scale - 1);
    unawaited(_setZoom(target));
  }

  Future<void> _handleFocusTap(
    TapUpDetails details,
    BoxConstraints constraints,
  ) async {
    final camera = _camera;
    if (camera == null || !camera.value.isInitialized) return;

    final point = Offset(
      (details.localPosition.dx / constraints.maxWidth).clamp(0, 1),
      (details.localPosition.dy / constraints.maxHeight).clamp(0, 1),
    );

    try {
      if (_settings.autoExposure) {
        await camera.setExposureMode(ExposureMode.auto);
        await camera.setExposurePoint(point);
      }
      if (_settings.autoFocus) {
        await camera.setFocusMode(FocusMode.auto);
        await camera.setFocusPoint(point);
      }
      _showSnack('Focus and brightness adjusted');
    } catch (_) {
      _showSnack('Focus point is not supported on this camera');
    }
  }

  void _showSnack(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  void _setStatus(String value) {
    if (!mounted) return;
    setState(() {
      _status = value;
    });
  }

  @override
  void dispose() {
    _disposed = true;
    _serverWatchdogTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    unawaited(_server?.close(force: true));
    _server = null;
    _discoverySocket?.close();
    _discoverySocket = null;
    unawaited(_wsClient?.stop());
    unawaited(_connectivitySubscription?.cancel());
    unawaited(_connectionLogSink?.close());
    unawaited(_stopFpsStream());
    unawaited(_camera?.dispose());
    unawaited(
      mediaChannel.invokeMethod<bool>('setKeepScreenOn', {'enabled': false}),
    );
    unawaited(mediaChannel.invokeMethod<bool>('releaseWakeLocks'));
    super.dispose();
  }

  Widget _buildFullscreenPreview(
    CameraController camera,
    BoxConstraints constraints,
  ) {
    final previewSize = camera.value.previewSize;
    if (previewSize == null) {
      return Center(child: camera.buildPreview());
    }

    // The swap decision is derived from the DECIDED target orientation
    // (_settings.recordingOrientation, owned by CameraOrientationManager), not by
    // re-comparing live `previewSize` against the current layout `constraints` on every
    // build. previewSize reflects the camera's native sensor buffer shape and can
    // legitimately fluctuate for a moment around a platform-side session
    // reconfiguration (e.g. when recording starts); deriving the swap from it directly
    // made this box's aspect ratio - and therefore what looked like the preview's
    // rotation - depend on that transient timing instead of the operator's actual
    // orientation choice. See previewNeedsDimensionSwap's doc comment.
    final needsSwap = previewNeedsDimensionSwap(
      recordingOrientation: _settings.recordingOrientation,
      previewSize: previewSize,
    );
    final previewWidth = needsSwap ? previewSize.height : previewSize.width;
    final previewHeight = needsSwap ? previewSize.width : previewSize.height;

    return ColoredBox(
      color: Colors.black,
      child: Center(
        child: FittedBox(
          fit: BoxFit.contain,
          child: SizedBox(
            width: previewWidth,
            height: previewHeight,
            child: camera.buildPreview(),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final camera = _camera;
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: [
          LayoutBuilder(
            builder: (context, constraints) {
              if (camera == null || !camera.value.isInitialized) {
                return Center(
                  child: _booted
                      ? const Text('Camera is not ready')
                      : const CircularProgressIndicator(),
                );
              }

              return GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTapUp: (details) =>
                    unawaited(_handleFocusTap(details, constraints)),
                onScaleStart: _handleScaleStart,
                onScaleUpdate: _handleScaleUpdate,
                child: _buildFullscreenPreview(camera, constraints),
              );
            },
          ),
          if (_settings.gridColumns > 0 && _settings.gridRows > 0)
            IgnorePointer(
              child: CustomPaint(
                painter: GridOverlayPainter(
                  columns: _settings.gridColumns,
                  rows: _settings.gridRows,
                ),
              ),
            ),
          if (_settings.showReticle)
            IgnorePointer(
              child: CustomPaint(
                painter: ReticleOverlayPainter(mode: _settings.reticleMode),
              ),
            ),
          Positioned(
            left: 16,
            right: 16,
            top: 36,
            child: SafeArea(
              bottom: false,
              child: _TopStatus(
                ip: _ip,
                status: _status,
                recording: _recording,
                lastVideoPath: _lastVideoPath,
                settings: _settings,
                actualFps: _actualFps,
                zoom: _zoom,
                wsStatus: _wsStatus,
              ),
            ),
          ),
          Positioned(
            left: 16,
            bottom: 96,
            child: SafeArea(
              top: false,
              child: FpsBadge(
                actualFps: _actualFps,
                targetFps: _settings.fps,
                recording: _recording,
              ),
            ),
          ),
          Positioned(
            right: 16,
            bottom: 92,
            child: SafeArea(
              top: false,
              child: ZoomControls(
                zoom: _zoom,
                minZoom: _minZoom,
                maxZoom: _maxZoom,
                onZoomOut: () => unawaited(_zoomBy(-1)),
                onZoomIn: () => unawaited(_zoomBy(1)),
              ),
            ),
          ),
          if (_reticleMenuOpen)
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.translucent,
                onTap: () => setState(() => _reticleMenuOpen = false),
                child: const SizedBox.expand(),
              ),
            ),
          Positioned(
            left: 16,
            bottom: 28,
            child: SafeArea(
              top: false,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (_reticleMenuOpen)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: ReticleModePicker(
                        selectedMode: _settings.reticleMode,
                        onSelected: (mode) => unawaited(_setReticleMode(mode)),
                      ),
                    ),
                  IconButton.filledTonal(
                    tooltip: 'Reticle: ${_settings.reticleLabel}',
                    onPressed: () {
                      setState(() => _reticleMenuOpen = !_reticleMenuOpen);
                    },
                    icon: CustomPaint(
                      size: const Size.square(26),
                      painter: ReticleIconPainter(mode: _settings.reticleMode),
                    ),
                  ),
                ],
              ),
            ),
          ),
          Positioned(
            right: 16,
            bottom: 28,
            child: SafeArea(
              top: false,
              child: IconButton.filledTonal(
                tooltip: 'Settings',
                onPressed: _openSettings,
                icon: const Icon(Icons.settings),
              ),
            ),
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 28,
            child: SafeArea(
              top: false,
              child: Center(
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(
                    backgroundColor: _recording
                        ? Colors.white
                        : const Color(0xffe0233d),
                    foregroundColor: _recording ? Colors.black : Colors.white,
                    minimumSize: const Size(190, 56),
                  ),
                  onPressed: () => _queue(_toggleRecording),
                  icon: Icon(
                    _recording ? Icons.stop : Icons.fiber_manual_record,
                  ),
                  label: Text(_recording ? 'STOP' : 'REC'),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Adapts `_CameraControlScreenState`'s existing start/stop/status methods (already
/// used by the legacy HTTP handlers) to the `RecordingController` interface
/// `ConnectionSupervisor` depends on - this is the only bridge between the two;
/// `ConnectionSupervisor` itself never references `_CameraControlScreenState` or the
/// `camera` plugin.
class _ScreenRecordingController implements RecordingController {
  _ScreenRecordingController(this._state);

  final _CameraControlScreenState _state;

  @override
  bool get isRecording => _state._recording;

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
  }) {
    return _state._queue(
      () => _state._startRecording(
        cameraName: cameraName,
        sessionId: sessionId,
        date: date,
        time: time,
        index: index,
        signerId: signerId,
        signerName: signerName,
        signerDir: signerDir,
        mode: mode,
        word: word,
        wordId: wordId,
        wordDir: wordDir,
        takeLabel: takeLabel,
        takeNumber: takeNumber,
        gestureCount: gestureCount,
        retake: retake,
      ),
    );
  }

  @override
  Future<void> stopRecording() {
    return _state._queue(() => _state._stopRecording());
  }

  @override
  Future<Map<String, Object?>> statusJson() => _state._statusJson();
}

class _TopStatus extends StatelessWidget {
  const _TopStatus({
    required this.ip,
    required this.status,
    required this.recording,
    required this.lastVideoPath,
    required this.settings,
    required this.actualFps,
    required this.zoom,
    required this.wsStatus,
  });

  final String ip;
  final String status;
  final bool recording;
  final String? lastVideoPath;
  final AppSettings settings;
  final double actualFps;
  final double zoom;
  final String wsStatus;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.68),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white24),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Icon(
                  recording
                      ? Icons.radio_button_checked
                      : Icons.radio_button_unchecked,
                  color: recording ? const Color(0xffff3852) : Colors.white70,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    status,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text('${settings.deviceSlot}: ${settings.deviceLabel}'),
            Text('http://$ip:$controlPort'),
            Text(
              'WS: $wsStatus',
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
            Text(
              '${settings.resolutionPreset} / ${settings.recordingOrientationLabel} / target ${settings.fps}fps / real ${actualFps.toStringAsFixed(1)}fps',
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
            Text(
              'grid ${settings.gridMode} / zoom ${zoom.toStringAsFixed(1)}x / AE ${settings.autoExposure ? 'auto' : 'lock'} / AF ${settings.autoFocus ? 'auto' : 'lock'}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
            if (lastVideoPath != null) ...[
              const SizedBox(height: 6),
              Text(
                lastVideoPath!,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white70, fontSize: 12),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class FpsBadge extends StatelessWidget {
  const FpsBadge({
    super.key,
    required this.actualFps,
    required this.targetFps,
    required this.recording,
  });

  final double actualFps;
  final int targetFps;
  final bool recording;

  @override
  Widget build(BuildContext context) {
    final shownFps = actualFps <= 0 ? '--' : actualFps.toStringAsFixed(1);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: const Color(0xff062d16).withValues(alpha: 0.86),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xff32d46b), width: 1.2),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.speed, size: 18, color: Color(0xff32d46b)),
            const SizedBox(width: 8),
            Text(
              '$shownFps FPS',
              style: const TextStyle(
                color: Color(0xff32d46b),
                fontSize: 16,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(width: 8),
            Text(
              recording ? 'REC' : 'LIVE',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.76),
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ZoomControls extends StatelessWidget {
  const ZoomControls({
    super.key,
    required this.zoom,
    required this.minZoom,
    required this.maxZoom,
    required this.onZoomOut,
    required this.onZoomIn,
  });

  final double zoom;
  final double minZoom;
  final double maxZoom;
  final VoidCallback onZoomOut;
  final VoidCallback onZoomIn;

  @override
  Widget build(BuildContext context) {
    final canZoom = maxZoom > minZoom;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.66),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white24),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              tooltip: 'Zoom out',
              onPressed: canZoom ? onZoomOut : null,
              icon: const Icon(Icons.remove),
              visualDensity: VisualDensity.compact,
            ),
            SizedBox(
              width: 58,
              child: Text(
                '${zoom.toStringAsFixed(1)}x',
                textAlign: TextAlign.center,
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
            ),
            IconButton(
              tooltip: 'Zoom in',
              onPressed: canZoom ? onZoomIn : null,
              icon: const Icon(Icons.add),
              visualDensity: VisualDensity.compact,
            ),
          ],
        ),
      ),
    );
  }
}

class ReticleModePicker extends StatelessWidget {
  const ReticleModePicker({
    super.key,
    required this.selectedMode,
    required this.onSelected,
  });

  final String selectedMode;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white24),
      ),
      child: Padding(
        padding: const EdgeInsets.all(6),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final mode in reticleModes)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 2),
                child: IconButton(
                  tooltip: _label(mode),
                  onPressed: () => onSelected(mode),
                  style: IconButton.styleFrom(
                    backgroundColor: selectedMode == mode
                        ? const Color(0xff39a2ff)
                        : Colors.white.withValues(alpha: 0.08),
                    foregroundColor: Colors.white,
                    fixedSize: const Size.square(44),
                    padding: EdgeInsets.zero,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  icon: CustomPaint(
                    size: const Size.square(24),
                    painter: ReticleIconPainter(
                      mode: mode,
                      selected: selectedMode == mode,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  static String _label(String mode) {
    switch (mode) {
      case 'off':
        return 'Off';
      case 'dot':
        return 'Dot';
      case 'cross':
        return 'Cross';
      case 'splitCross':
        return 'Split cross';
      case 'frameCross':
        return 'Frame cross';
      default:
        return mode;
    }
  }
}

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key, required this.initialSettings});

  final AppSettings initialSettings;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late int _deviceSlot;
  late String _gridMode;
  late String _reticleMode;
  late String _resolutionPreset;
  late int _fps;
  late String _recordingOrientation;
  late bool _enableAudio;
  late bool _keepScreenOn;
  late bool _saveToGallery;
  late bool _autoExposure;
  late bool _autoFocus;
  late bool _smartZoom;
  late double _zoomLevel;
  late TextEditingController _labelController;
  late TextEditingController _prefixController;

  @override
  void initState() {
    super.initState();
    final settings = widget.initialSettings;
    _deviceSlot = settings.deviceSlot;
    _gridMode = settings.gridMode;
    _reticleMode = settings.reticleMode;
    _resolutionPreset = settings.resolutionPreset;
    _fps = stableRecordingFps;
    _recordingOrientation = settings.recordingOrientation;
    _enableAudio = settings.enableAudio;
    _keepScreenOn = settings.keepScreenOn;
    _saveToGallery = settings.saveToGallery;
    _autoExposure = settings.autoExposure;
    _autoFocus = settings.autoFocus;
    _smartZoom = settings.smartZoom;
    _zoomLevel = settings.zoomLevel;
    _labelController = TextEditingController(text: settings.deviceLabel);
    _prefixController = TextEditingController(text: settings.filePrefix);
  }

  @override
  void dispose() {
    _labelController.dispose();
    _prefixController.dispose();
    super.dispose();
  }

  void _save() {
    Navigator.of(context).pop(
      AppSettings(
        deviceSlot: _deviceSlot,
        deviceLabel: _labelController.text,
        gridMode: _gridMode,
        reticleMode: _reticleMode,
        resolutionPreset: _resolutionPreset,
        fps: stableRecordingFps,
        recordingOrientation: _recordingOrientation,
        enableAudio: _enableAudio,
        keepScreenOn: _keepScreenOn,
        saveToGallery: _saveToGallery,
        filePrefix: _prefixController.text,
        autoExposure: _autoExposure,
        autoFocus: _autoFocus,
        smartZoom: _smartZoom,
        zoomLevel: _zoomLevel,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        actions: [
          TextButton.icon(
            onPressed: _save,
            icon: const Icon(Icons.check),
            label: const Text('Save'),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Device', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          DropdownButtonFormField<int>(
            initialValue: _deviceSlot,
            decoration: const InputDecoration(
              labelText: 'Device number',
              border: OutlineInputBorder(),
            ),
            items: List.generate(
              12,
              (index) => DropdownMenuItem(
                value: index + 1,
                child: Text('${index + 1} device'),
              ),
            ),
            onChanged: (value) {
              if (value == null) return;
              setState(() {
                _deviceSlot = value;
                final current = _labelController.text.trim();
                if (current.isEmpty ||
                    RegExp(r'^device_\d+$').hasMatch(current)) {
                  _labelController.text = 'device_$value';
                }
              });
            },
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _labelController,
            decoration: const InputDecoration(
              labelText: 'Device label / camera name',
              border: OutlineInputBorder(),
            ),
            textInputAction: TextInputAction.next,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _prefixController,
            decoration: const InputDecoration(
              labelText: 'File prefix',
              border: OutlineInputBorder(),
            ),
            textInputAction: TextInputAction.done,
          ),
          const SizedBox(height: 24),
          Text('Camera', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _resolutionPreset,
            decoration: const InputDecoration(
              labelText: 'Resolution',
              border: OutlineInputBorder(),
            ),
            items: const [
              DropdownMenuItem(value: 'low', child: Text('Low')),
              DropdownMenuItem(value: 'medium', child: Text('Medium')),
              DropdownMenuItem(value: 'high', child: Text('High')),
              DropdownMenuItem(value: 'veryHigh', child: Text('Very high')),
              DropdownMenuItem(value: 'ultraHigh', child: Text('Ultra high')),
              DropdownMenuItem(value: 'max', child: Text('Max')),
            ],
            onChanged: (value) {
              if (value == null) return;
              setState(() => _resolutionPreset = value);
            },
          ),
          const SizedBox(height: 12),
          TextFormField(
            initialValue: '$_fps fps',
            enabled: false,
            decoration: const InputDecoration(
              labelText: 'Target FPS',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _recordingOrientation,
            decoration: const InputDecoration(
              labelText: 'Recording format',
              border: OutlineInputBorder(),
            ),
            items: const [
              DropdownMenuItem(value: 'portrait', child: Text('Vertical')),
              DropdownMenuItem(value: 'landscape', child: Text('Horizontal')),
            ],
            onChanged: (value) {
              if (value == null) return;
              setState(() => _recordingOrientation = value);
            },
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _gridMode,
            decoration: const InputDecoration(
              labelText: 'Grid',
              border: OutlineInputBorder(),
            ),
            items: const [
              DropdownMenuItem(value: 'off', child: Text('Off')),
              DropdownMenuItem(value: '3x4', child: Text('3 x 4')),
              DropdownMenuItem(value: '4x3', child: Text('4 x 3')),
            ],
            onChanged: (value) {
              if (value == null) return;
              setState(() => _gridMode = value);
            },
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _reticleMode,
            decoration: const InputDecoration(
              labelText: 'Reticle',
              border: OutlineInputBorder(),
            ),
            items: const [
              DropdownMenuItem(value: 'off', child: Text('Off')),
              DropdownMenuItem(value: 'dot', child: Text('Dot')),
              DropdownMenuItem(value: 'cross', child: Text('Cross')),
              DropdownMenuItem(value: 'splitCross', child: Text('Split cross')),
              DropdownMenuItem(value: 'frameCross', child: Text('Frame cross')),
            ],
            onChanged: (value) {
              if (value == null) return;
              setState(() => _reticleMode = value);
            },
          ),
          const SizedBox(height: 12),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Auto brightness'),
            subtitle: const Text('Camera auto exposure'),
            value: _autoExposure,
            onChanged: (value) => setState(() => _autoExposure = value),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Auto focus'),
            subtitle: const Text('Continuous focus with tap point'),
            value: _autoFocus,
            onChanged: (value) => setState(() => _autoFocus = value),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Smart zoom'),
            subtitle: const Text('Smooth pinch and adaptive zoom steps'),
            value: _smartZoom,
            onChanged: (value) => setState(() => _smartZoom = value),
          ),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text('Start zoom ${_zoomLevel.toStringAsFixed(1)}x'),
            subtitle: Slider(
              min: 1,
              max: 10,
              divisions: 90,
              value: _zoomLevel.clamp(1, 10).toDouble(),
              onChanged: (value) => setState(() => _zoomLevel = value),
            ),
          ),
          const SizedBox(height: 12),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Audio'),
            value: _enableAudio,
            onChanged: (value) => setState(() => _enableAudio = value),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Keep screen on'),
            value: _keepScreenOn,
            onChanged: (value) => setState(() => _keepScreenOn = value),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Save to gallery'),
            value: _saveToGallery,
            onChanged: (value) => setState(() => _saveToGallery = value),
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: _save,
            icon: const Icon(Icons.save),
            label: const Text('Save settings'),
          ),
        ],
      ),
    );
  }
}

class GridOverlayPainter extends CustomPainter {
  const GridOverlayPainter({required this.columns, required this.rows});

  final int columns;
  final int rows;

  @override
  void paint(Canvas canvas, Size size) {
    if (columns <= 0 || rows <= 0) return;

    final paint = Paint()
      ..color = Colors.white.withValues(alpha: 0.42)
      ..strokeWidth = 1;

    for (var column = 1; column < columns; column++) {
      final x = size.width * column / columns;
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }

    for (var row = 1; row < rows; row++) {
      final y = size.height * row / rows;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant GridOverlayPainter oldDelegate) {
    return columns != oldDelegate.columns || rows != oldDelegate.rows;
  }
}

class ReticleOverlayPainter extends CustomPainter {
  const ReticleOverlayPainter({required this.mode});

  final String mode;

  @override
  void paint(Canvas canvas, Size size) {
    if (mode == 'off' || size.isEmpty) return;

    final center = size.center(Offset.zero);
    final unit = size.shortestSide;
    final paint = Paint()
      ..color = _reticleColor(mode).withValues(alpha: _reticleAlpha(mode))
      ..strokeWidth = (unit * 0.0046).clamp(2.0, 4.0)
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    switch (mode) {
      case 'dot':
        canvas.drawCircle(center, (unit * 0.0065).clamp(2.2, 5.0), paint);
        break;
      case 'splitCross':
        _drawSplitCross(canvas, center, unit, paint);
        break;
      case 'frameCross':
        _drawFrameCross(canvas, center, unit, paint);
        break;
      case 'cross':
      default:
        _drawCross(canvas, center, unit, paint);
        break;
    }
  }

  static Color _reticleColor(String mode) {
    switch (mode) {
      case 'cross':
      case 'splitCross':
        return const Color(0xff85c8ff);
      default:
        return Colors.white;
    }
  }

  static double _reticleAlpha(String mode) {
    switch (mode) {
      case 'dot':
        return 0.55;
      case 'frameCross':
        return 0.42;
      default:
        return 0.72;
    }
  }

  static void _drawCross(
    Canvas canvas,
    Offset center,
    double unit,
    Paint paint,
  ) {
    final half = unit * 0.105;
    canvas.drawLine(
      Offset(center.dx - half, center.dy),
      Offset(center.dx + half, center.dy),
      paint,
    );
    canvas.drawLine(
      Offset(center.dx, center.dy - half),
      Offset(center.dx, center.dy + half),
      paint,
    );
  }

  static void _drawSplitCross(
    Canvas canvas,
    Offset center,
    double unit,
    Paint paint,
  ) {
    final inner = unit * 0.034;
    final outer = unit * 0.086;
    canvas.drawLine(
      Offset(center.dx - outer, center.dy),
      Offset(center.dx - inner, center.dy),
      paint,
    );
    canvas.drawLine(
      Offset(center.dx + inner, center.dy),
      Offset(center.dx + outer, center.dy),
      paint,
    );
    canvas.drawLine(
      Offset(center.dx, center.dy - outer),
      Offset(center.dx, center.dy - inner),
      paint,
    );
    canvas.drawLine(
      Offset(center.dx, center.dy + inner),
      Offset(center.dx, center.dy + outer),
      paint,
    );
  }

  static void _drawFrameCross(
    Canvas canvas,
    Offset center,
    double unit,
    Paint paint,
  ) {
    final halfLength = unit * 0.105;
    final halfGap = unit * 0.017;
    final verticalHalf = unit * 0.102;
    final horizontalGap = unit * 0.022;
    canvas.drawLine(
      Offset(center.dx - halfLength, center.dy - halfGap),
      Offset(center.dx + halfLength, center.dy - halfGap),
      paint,
    );
    canvas.drawLine(
      Offset(center.dx - halfLength, center.dy + halfGap),
      Offset(center.dx + halfLength, center.dy + halfGap),
      paint,
    );
    canvas.drawLine(
      Offset(center.dx - horizontalGap, center.dy - verticalHalf),
      Offset(center.dx - horizontalGap, center.dy + verticalHalf),
      paint,
    );
    canvas.drawLine(
      Offset(center.dx + horizontalGap, center.dy - verticalHalf),
      Offset(center.dx + horizontalGap, center.dy + verticalHalf),
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant ReticleOverlayPainter oldDelegate) {
    return mode != oldDelegate.mode;
  }
}

class ReticleIconPainter extends CustomPainter {
  const ReticleIconPainter({required this.mode, this.selected = false});

  final String mode;
  final bool selected;

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final unit = size.shortestSide;
    final paint = Paint()
      ..color = selected
          ? Colors.white
          : (mode == 'off' ? Colors.white70 : const Color(0xff39a2ff))
      ..strokeWidth = (unit * 0.08).clamp(1.8, 2.4)
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;
    final boxPaint = Paint()
      ..color = paint.color
      ..strokeWidth = paint.strokeWidth
      ..style = PaintingStyle.stroke;

    canvas.drawRRect(
      RRect.fromRectAndRadius(Offset.zero & size, Radius.circular(unit * 0.18)),
      boxPaint,
    );

    switch (mode) {
      case 'off':
        canvas.drawLine(
          Offset(unit * 0.22, unit * 0.78),
          Offset(unit * 0.78, unit * 0.22),
          paint,
        );
        break;
      case 'dot':
        canvas.drawCircle(center, unit * 0.08, paint);
        break;
      case 'splitCross':
        ReticleOverlayPainter._drawSplitCross(canvas, center, unit, paint);
        break;
      case 'frameCross':
        ReticleOverlayPainter._drawFrameCross(canvas, center, unit, paint);
        break;
      case 'cross':
      default:
        ReticleOverlayPainter._drawCross(canvas, center, unit, paint);
        break;
    }
  }

  @override
  bool shouldRepaint(covariant ReticleIconPainter oldDelegate) {
    return mode != oldDelegate.mode || selected != oldDelegate.selected;
  }
}

(int, int) targetSizeForPreset(String preset) {
  switch (preset) {
    case 'low':
      return (320, 240);
    case 'medium':
      return (720, 480);
    case 'high':
      return (1280, 720);
    case 'ultraHigh':
      return (3840, 2160);
    case 'max':
      return (3840, 2160);
    case 'veryHigh':
    default:
      return (1920, 1080);
  }
}
