package com.example.three_cam_mobile

import android.Manifest
import android.content.ContentValues
import android.content.ContentUris
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.net.Uri
import android.os.BatteryManager
import android.os.Build
import android.os.Environment
import android.os.PowerManager
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
                "startKeepAliveService" -> {
                    val enableAudio = call.argument<Boolean>("enableAudio") ?: true
                    startKeepAliveService(enableAudio)
                    result.success(true)
                }
                "stopKeepAliveService" -> {
                    stopKeepAliveService()
                    result.success(true)
                }
                "requestNotificationPermission" -> result.success(requestNotificationPermission())
                "isIgnoringBatteryOptimizations" -> result.success(isIgnoringBatteryOptimizations())
                "requestIgnoreBatteryOptimizations" -> {
                    result.success(requestIgnoreBatteryOptimizations())
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

    private fun startKeepAliveService(enableAudio: Boolean) {
        requestNotificationPermission()
        val intent = Intent(this, ConnectionKeepAliveService::class.java).apply {
            putExtra(ConnectionKeepAliveService.EXTRA_ENABLE_AUDIO, enableAudio)
        }
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(intent)
            } else {
                startService(intent)
            }
        } catch (_: Exception) {
        }
    }

    private fun stopKeepAliveService() {
        stopService(Intent(this, ConnectionKeepAliveService::class.java))
    }

    private fun requestNotificationPermission(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            return true
        }
        if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) {
            return true
        }
        requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), NOTIFICATION_PERMISSION_REQUEST)
        return false
    }

    private fun isIgnoringBatteryOptimizations(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            return true
        }
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        return powerManager.isIgnoringBatteryOptimizations(packageName)
    }

    private fun requestIgnoreBatteryOptimizations(): Boolean {
        if (isIgnoringBatteryOptimizations()) {
            return true
        }
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            return true
        }
        try {
            val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                data = Uri.parse("package:$packageName")
            }
            startActivity(intent)
        } catch (_: Exception) {
            startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
        }
        return false
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

    companion object {
        private const val NOTIFICATION_PERMISSION_REQUEST = 4309
    }
}
