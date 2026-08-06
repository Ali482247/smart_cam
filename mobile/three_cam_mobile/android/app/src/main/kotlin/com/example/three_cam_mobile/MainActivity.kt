package com.example.three_cam_mobile

import android.content.ContentValues
import android.content.Context
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.provider.Settings
import android.view.WindowManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File

class MainActivity : FlutterActivity() {
    private val channelName = "three_cam/media"
    private var keepScreenOn = false

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
                    if (sourcePath.isNullOrBlank() || displayName.isNullOrBlank()) {
                        result.error("bad_args", "sourcePath and displayName are required", null)
                        return@setMethodCallHandler
                    }

                    try {
                        val savedPath = saveVideoToDcim(sourcePath, displayName)
                        result.success(savedPath)
                    } catch (error: Exception) {
                        result.error("save_failed", error.message, null)
                    }
                }
                "getDeviceStatus" -> result.success(deviceStatus())
                "setKeepScreenOn" -> {
                    val enabled = call.argument<Boolean>("enabled") ?: false
                    setKeepScreenOn(enabled)
                    result.success(true)
                }
                else -> result.notImplemented()
            }
        }
    }

    override fun onDestroy() {
        setKeepScreenOn(false)
        super.onDestroy()
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
            "batteryCharging" to isBatteryCharging()
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

    private fun saveVideoToDcim(sourcePath: String, displayName: String): String {
        val source = File(sourcePath)
        require(source.exists()) { "Source video does not exist: $sourcePath" }

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
                    "${Environment.DIRECTORY_DCIM}/ThreeCam"
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

        return "DCIM/ThreeCam/$displayName"
    }
}
