package com.example.three_cam_mobile

import android.content.ContentValues
import android.content.ContentUris
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.Uri
import android.net.wifi.WifiManager
import android.os.BatteryManager
import android.os.Build
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.provider.MediaStore
import android.provider.Settings
import android.util.Log
import android.view.WindowManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel
import java.io.File
import org.json.JSONObject

class MainActivity : FlutterActivity() {
    private val channelName = "three_cam/media"
    private val connectivityEventChannelName = "three_cam/connectivity"
    private var keepScreenOn = false

    // Held while the app is running so Android's Doze/App Standby (and aggressive
    // OEM battery savers below ~15% battery on Xiaomi/Huawei/Samsung) can't suspend
    // the local HTTP/UDP sockets from lib/main.dart out from under us. Without these,
    // the phone silently stops answering the controller and needs a manual relaunch.
    private var wakeLock: PowerManager.WakeLock? = null
    private var wifiLock: WifiManager.WifiLock? = null

    // Pushes real OS connectivity transitions (Wi-Fi lost/restored, capability changes)
    // to Dart's ConnectionSupervisor instead of it relying only on polling/backoff -
    // see lib/ws/ws_client.dart onNetworkAvailable()/onNetworkLost(). Registered in
    // configureFlutterEngine() (once the EventChannel sink exists) and unregistered in
    // onDestroy() - a NetworkCallback leaked past Activity lifetime is a real leak, not
    // just untidy, since ConnectivityManager holds a reference to it indefinitely.
    private var connectivityManager: ConnectivityManager? = null
    private var networkCallback: ConnectivityManager.NetworkCallback? = null
    private var connectivityEventSink: EventChannel.EventSink? = null
    private val mainHandler = Handler(Looper.getMainLooper())

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            channelName
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "saveVideoToDcim" -> {
                    val sourcePath = call.argument<String>("sourcePath")
                    val displayName = call.argument<String>("displayName")
                    val relativeDir = call.argument<String>("relativeDir")
                    if (sourcePath.isNullOrBlank() || displayName.isNullOrBlank()) {
                        result.error("bad_args", "sourcePath and displayName are required", null)
                        return@setMethodCallHandler
                    }

                    try {
                        val savedPath = saveVideoToDcim(sourcePath, displayName, relativeDir)
                        result.success(savedPath)
                    } catch (error: Exception) {
                        result.error("save_failed", error.message, null)
                    }
                }
                "deleteThreeCamDcimVideos" -> {
                    try {
                        result.success(deleteThreeCamDcimVideos())
                    } catch (error: Exception) {
                        result.error("delete_failed", error.message, null)
                    }
                }
                "markDcimVideoError" -> {
                    val relativePath = call.argument<String>("relativePath")
                    val newDisplayName = call.argument<String>("newDisplayName")
                    if (relativePath.isNullOrBlank() || newDisplayName.isNullOrBlank()) {
                        result.error("bad_args", "relativePath and newDisplayName are required", null)
                        return@setMethodCallHandler
                    }

                    try {
                        result.success(markDcimVideoError(relativePath, newDisplayName))
                    } catch (error: Exception) {
                        result.error("mark_failed", error.message, null)
                    }
                }
                "getDeviceStatus" -> result.success(deviceStatus())
                "setKeepScreenOn" -> {
                    val enabled = call.argument<Boolean>("enabled") ?: false
                    setKeepScreenOn(enabled)
                    result.success(true)
                }
                "acquireWakeLocks" -> {
                    acquireWakeLocks()
                    result.success(true)
                }
                "releaseWakeLocks" -> {
                    releaseWakeLocks()
                    result.success(true)
                }
                "isIgnoringBatteryOptimizations" -> result.success(isIgnoringBatteryOptimizations())
                "requestIgnoreBatteryOptimizations" -> {
                    requestIgnoreBatteryOptimizations()
                    result.success(true)
                }
                else -> result.notImplemented()
            }
        }

        EventChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            connectivityEventChannelName
        ).setStreamHandler(
            object : EventChannel.StreamHandler {
                override fun onListen(arguments: Any?, events: EventChannel.EventSink) {
                    connectivityEventSink = events
                    registerNetworkCallback()
                    // Deliver the current state immediately so a Dart-side listener that
                    // attaches after boot (e.g. following a hot restart) doesn't have to
                    // wait for the next actual transition to know where things stand.
                    emitConnectivityEvent(currentNetworkSnapshot())
                }

                override fun onCancel(arguments: Any?) {
                    unregisterNetworkCallback()
                    connectivityEventSink = null
                }
            }
        )
    }

    override fun onDestroy() {
        setKeepScreenOn(false)
        releaseWakeLocks()
        unregisterNetworkCallback()
        super.onDestroy()
    }

    // NetworkCallback pushes real Wi-Fi lost/restored transitions to Dart instead of
    // ConnectionSupervisor having to infer them from failed socket operations alone -
    // section 10 of the audit: "Не используй polling как основной источник сетевых
    // событий, если Android может дать event." registerDefaultNetworkCallback() tracks
    // whatever network the OS considers "the" active one, which is the right scope here
    // (this app only ever talks to the Director over the currently active Wi-Fi).
    private fun registerNetworkCallback() {
        if (networkCallback != null) return
        val manager = getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return
        connectivityManager = manager
        val callback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                emitConnectivityEvent(currentNetworkSnapshot())
            }

            override fun onLost(network: Network) {
                // onLost fires for the network that went away; re-derive from the
                // manager's current active network rather than assuming "no network at
                // all" - Android may already be mid-handover to another one (e.g.
                // Wi-Fi -> Wi-Fi after a roam, or Wi-Fi -> mobile data).
                emitConnectivityEvent(currentNetworkSnapshot())
            }

            override fun onCapabilitiesChanged(
                network: Network,
                capabilities: NetworkCapabilities
            ) {
                emitConnectivityEvent(currentNetworkSnapshot())
            }

            override fun onLinkPropertiesChanged(
                network: Network,
                linkProperties: android.net.LinkProperties
            ) {
                emitConnectivityEvent(currentNetworkSnapshot())
            }
        }
        try {
            manager.registerDefaultNetworkCallback(callback)
            networkCallback = callback
        } catch (error: Exception) {
            Log.w("ThreeCam", "registerNetworkCallback failed", error)
        }
    }

    private fun unregisterNetworkCallback() {
        val manager = connectivityManager
        val callback = networkCallback
        if (manager != null && callback != null) {
            try {
                manager.unregisterNetworkCallback(callback)
            } catch (error: Exception) {
                Log.w("ThreeCam", "unregisterNetworkCallback failed", error)
            }
        }
        networkCallback = null
    }

    private fun currentNetworkSnapshot(): JSONObject {
        val manager = connectivityManager
            ?: (getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager)
        val network = manager?.activeNetwork
        val capabilities = network?.let { manager.getNetworkCapabilities(it) }
        val hasInternet = capabilities?.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED) == true
        val isWifi = capabilities?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true
        return JSONObject().apply {
            put("available", network != null && hasInternet)
            put("wifi", isWifi)
        }
    }

    private fun emitConnectivityEvent(payload: JSONObject) {
        // NetworkCallback methods can run on a binder thread; EventChannel.EventSink
        // must only be touched from the platform (UI) thread.
        mainHandler.post {
            connectivityEventSink?.success(payload.toString())
        }
    }

    // PARTIAL_WAKE_LOCK keeps the CPU running (so the Dart isolate and its
    // HttpServer/RawDatagramSocket keep servicing requests) without keeping the
    // screen on - that's handled separately by setKeepScreenOn(). WIFI_MODE_FULL_HIGH_PERF
    // keeps the Wi-Fi radio from entering its own power-save sleep, which is a
    // separate throttle from CPU Doze and just as capable of silently dropping the
    // control-plane connection.
    private fun acquireWakeLocks() {
        if (wakeLock == null) {
            val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
            wakeLock = powerManager.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                "ThreeCam:RecordingWakeLock"
            ).apply {
                setReferenceCounted(false)
                try {
                    acquire()
                } catch (error: Exception) {
                    Log.w("ThreeCam", "acquireWakeLocks: wake lock acquire failed", error)
                }
            }
        }
        if (wifiLock == null) {
            val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            // WIFI_MODE_FULL_HIGH_PERF has been deprecated since API 31 (the platform
            // manages that performance mode automatically for a plain full lock now);
            // WIFI_MODE_FULL_LOW_LATENCY is the documented replacement and is what this
            // app actually wants (low-latency control-plane traffic), but it only exists
            // from API 29 - fall back to the old constant below that so this still works
            // on any minSdk this project supports.
            val lockMode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                WifiManager.WIFI_MODE_FULL_LOW_LATENCY
            } else {
                @Suppress("DEPRECATION")
                WifiManager.WIFI_MODE_FULL_HIGH_PERF
            }
            wifiLock = wifiManager.createWifiLock(
                lockMode,
                "ThreeCam:WifiLock"
            ).apply {
                setReferenceCounted(false)
                try {
                    acquire()
                } catch (error: Exception) {
                    Log.w("ThreeCam", "acquireWakeLocks: wifi lock acquire failed", error)
                }
            }
        }
    }

    private fun releaseWakeLocks() {
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        wifiLock?.let { if (it.isHeld) it.release() }
        wifiLock = null
    }

    private fun isIgnoringBatteryOptimizations(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return true
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        return powerManager.isIgnoringBatteryOptimizations(packageName)
    }

    // Tri-state surfaced to the operator (section 13 of the audit): "protected" (this
    // app is whitelisted - the common/desired case after requestIgnoreBatteryOptimizations()
    // succeeds), "not_protected" (the operator dismissed/denied the prompt, or an OEM
    // blocked it - the app still runs, just without this specific safety net; the
    // WakeLock/WifiLock protections above are independent of this), or "unknown" (API
    // level too old to have the concept at all).
    private fun batteryOptimizationStatus(): String {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return "unknown"
        return if (isIgnoringBatteryOptimizations()) "protected" else "not_protected"
    }

    // Prompts the operator once per phone (Android remembers the choice) to whitelist
    // this app from battery optimizations. Without this, Android's automatic Battery
    // Saver (commonly configured to switch on at 15% battery) can restrict background
    // network activity for the app even while wake/wifi locks are held.
    private fun requestIgnoreBatteryOptimizations() {
        if (isIgnoringBatteryOptimizations()) return
        try {
            startActivity(
                Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                    data = Uri.parse("package:$packageName")
                }
            )
        } catch (error: Exception) {
            // Some OEMs (e.g. MIUI) block the direct request intent - fall back to the
            // general battery-optimization list so the operator can whitelist it by hand.
            Log.w("ThreeCam", "requestIgnoreBatteryOptimizations: direct request failed", error)
            try {
                startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
            } catch (fallbackError: Exception) {
                Log.w("ThreeCam", "requestIgnoreBatteryOptimizations: settings fallback failed", fallbackError)
            }
        }
    }

    private fun setKeepScreenOn(enabled: Boolean) {
        keepScreenOn = enabled
        runOnUiThread {
            if (enabled) {
                window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            } else {
                window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            }
        }
    }

    private fun deviceStatus(): Map<String, Any?> {
        val storageDir = getExternalFilesDir(null) ?: filesDir
        val deviceId = Settings.Secure.getString(
            applicationContext.contentResolver,
            Settings.Secure.ANDROID_ID
        ) ?: Build.MODEL

        return mapOf(
            "deviceId" to deviceId,
            "deviceName" to Build.MODEL,
            "manufacturer" to Build.MANUFACTURER,
            "osVersion" to Build.VERSION.RELEASE,
            "keepScreenOn" to keepScreenOn,
            "freeStorageBytes" to storageDir.usableSpace,
            "totalStorageBytes" to storageDir.totalSpace,
            "batteryPercent" to batteryPercent(),
            "batteryCharging" to isBatteryCharging(),
            "batteryOptimizationStatus" to batteryOptimizationStatus()
        )
    }

    private fun batteryPercent(): Int? {
        val batteryManager = getSystemService(Context.BATTERY_SERVICE) as? BatteryManager
        val level = batteryManager?.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        return if (level != null && level in 0..100) level else null
    }

    private fun isBatteryCharging(): Boolean {
        val status = registerReceiver(null, IntentFilter(android.content.Intent.ACTION_BATTERY_CHANGED))
        val plugged = status?.getIntExtra(BatteryManager.EXTRA_PLUGGED, -1) ?: -1
        return plugged != -1 && plugged != 0
    }

    private fun saveVideoToDcim(sourcePath: String, displayName: String, relativeDir: String?): String {
        val source = File(sourcePath)
        require(source.exists()) { "Source video does not exist: $sourcePath" }
        val safeRelativeDir = relativeDir
            ?.trim('/')
            ?.replace("\\", "/")
            ?.takeIf { it.isNotBlank() }
            ?: "ThreeCam"

        val resolver = applicationContext.contentResolver
        val collection = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
        } else {
            MediaStore.Video.Media.EXTERNAL_CONTENT_URI
        }

        val values = ContentValues().apply {
            put(MediaStore.Video.Media.DISPLAY_NAME, displayName)
            put(MediaStore.Video.Media.MIME_TYPE, "video/mp4")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(
                    MediaStore.Video.Media.RELATIVE_PATH,
                    "${Environment.DIRECTORY_DCIM}/$safeRelativeDir"
                )
                put(MediaStore.Video.Media.IS_PENDING, 1)
            }
        }

        val uri = resolver.insert(collection, values)
            ?: error("Could not create MediaStore item")

        resolver.openOutputStream(uri).use { output ->
            requireNotNull(output) { "Could not open MediaStore output stream" }
            source.inputStream().use { input ->
                input.copyTo(output)
            }
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val doneValues = ContentValues().apply {
                put(MediaStore.Video.Media.IS_PENDING, 0)
            }
            resolver.update(uri, doneValues, null, null)
        }

        return "DCIM/$safeRelativeDir/$displayName"
    }

    private fun deleteThreeCamDcimVideos(): Int {
        val resolver = applicationContext.contentResolver
        val collection = videoCollection()
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            resolver.delete(
                collection,
                "${MediaStore.Video.Media.RELATIVE_PATH} LIKE ?",
                arrayOf("${Environment.DIRECTORY_DCIM}/ThreeCam/%")
            )
        } else {
            resolver.delete(
                collection,
                "${MediaStore.Video.Media.DATA} LIKE ?",
                arrayOf("%/${Environment.DIRECTORY_DCIM}/ThreeCam/%")
            )
        }
    }

    private fun markDcimVideoError(relativePath: String, newDisplayName: String): Boolean {
        val normalized = relativePath.trim('/').replace("\\", "/")
        val oldDisplayName = normalized.substringAfterLast('/')
        val parent = normalized.substringBeforeLast('/', "")
        val resolver = applicationContext.contentResolver
        val collection = videoCollection()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val dcimRelativePath = buildString {
                append(Environment.DIRECTORY_DCIM)
                append("/ThreeCam/")
                if (parent.isNotBlank()) {
                    append(parent)
                    append("/")
                }
            }
            val values = ContentValues().apply {
                put(MediaStore.Video.Media.DISPLAY_NAME, newDisplayName)
            }
            return resolver.update(
                collection,
                values,
                "${MediaStore.Video.Media.RELATIVE_PATH} = ? AND ${MediaStore.Video.Media.DISPLAY_NAME} = ?",
                arrayOf(dcimRelativePath, oldDisplayName)
            ) > 0
        }

        val cursor = resolver.query(
            collection,
            arrayOf(MediaStore.Video.Media._ID, MediaStore.Video.Media.DATA),
            "${MediaStore.Video.Media.DATA} LIKE ?",
            arrayOf("%/${Environment.DIRECTORY_DCIM}/ThreeCam/$normalized"),
            null
        ) ?: return false
        cursor.use {
            if (!it.moveToFirst()) {
                return false
            }
            val id = it.getLong(0)
            val dataPath = it.getString(1)
            val source = File(dataPath)
            val target = File(source.parentFile, newDisplayName)
            val renamed = source.renameTo(target)
            if (renamed) {
                val uri = ContentUris.withAppendedId(collection, id)
                val values = ContentValues().apply {
                    put(MediaStore.Video.Media.DISPLAY_NAME, newDisplayName)
                    put(MediaStore.Video.Media.DATA, target.absolutePath)
                }
                resolver.update(uri, values, null, null)
            }
            return renamed
        }
    }

    private fun videoCollection() = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
        MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
    } else {
        MediaStore.Video.Media.EXTERNAL_CONTENT_URI
    }
}
