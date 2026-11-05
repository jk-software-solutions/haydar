package com.jawadsites.haydar

import android.Manifest
import android.app.Notification
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.net.wifi.WifiManager
import android.os.Build
import androidx.core.content.ContextCompat
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterFragmentActivity() {
    private val channelName = "hadir/wifi"
    private val notificationChannelName = "hadir/notifications"
    private val notificationChannelId = "hadir_notifications_v2"
    private val wifiPermissionRequestCode = 4101
    private var pendingWifiPermissionResult: MethodChannel.Result? = null
    private var nextNotificationId = 1000

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        createNotificationChannel()
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "requestAccess" -> requestWifiAccess(result)
                    "scanNetworks" -> scanNetworks(result)
                    "currentConnection" -> {
                        val manager = getSystemService(Context.WIFI_SERVICE) as WifiManager
                        val info = manager.connectionInfo
                        val ssid = info?.ssid?.trim('"')
                        val bssid = info?.bssid
                        if (ssid.isNullOrBlank() || ssid == "<unknown ssid>" || bssid.isNullOrBlank()) {
                            result.success(null)
                        } else {
                            result.success(mapOf("ssid" to ssid, "bssid" to bssid))
                        }
                    }
                    else -> result.notImplemented()
                }
            }

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, notificationChannelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "playNotificationSound" -> {
                        val ringtone = RingtoneManager.getRingtone(
                            this,
                            RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION),
                        )
                        ringtone?.play()
                        result.success(null)
                    }
                    "showNotification" -> {
                        val title = call.argument<String>("title") ?: "HADIR"
                        val body = call.argument<String>("body") ?: "لديك إشعار جديد"
                        showLocalNotification(title, body)
                        result.success(null)
                    }
                    else -> result.notImplemented()
                }
            }
    }

    private fun showLocalNotification(title: String, body: String) {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val sound = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, notificationChannelId)
        } else {
            Notification.Builder(this)
                .setSound(sound)
                .setPriority(Notification.PRIORITY_HIGH)
        }
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(Notification.BigTextStyle().bigText(body))
            .setAutoCancel(true)
            .setCategory(Notification.CATEGORY_MESSAGE)
        manager.notify(nextNotificationId++, builder.build())
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = getSystemService(NotificationManager::class.java)
        val sound = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)
        val attributes = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_NOTIFICATION)
            .build()
        val channel = NotificationChannel(
            notificationChannelId,
            "HADIR notifications",
            NotificationManager.IMPORTANCE_HIGH,
        )
        channel.setSound(sound, attributes)
        channel.enableVibration(true)
        manager.createNotificationChannel(channel)
    }

    /** Return the nearby access points the system currently knows about.
     * Android requires location/nearby-Wi-Fi permission for this operation;
     * the Dart side turns an empty result into a readable setup message.
     */
    private fun scanNetworks(result: MethodChannel.Result) {
        val manager = getSystemService(Context.WIFI_SERVICE) as WifiManager
        if (!manager.isWifiEnabled) {
            result.success(emptyList<Map<String, Any>>())
            return
        }
        // startScan is throttled by Android. The latest cached results are
        // still useful and avoid blocking the UI while the radio refreshes.
        runCatching { manager.startScan() }
        val seen = mutableSetOf<String>()
        val networks = manager.scanResults
            .asSequence()
            .filter { !it.SSID.isNullOrBlank() && !it.BSSID.isNullOrBlank() }
            .mapNotNull { item ->
                val key = "${item.SSID}\u0000${item.BSSID}"
                if (!seen.add(key)) return@mapNotNull null
                mapOf<String, Any>(
                    "ssid" to item.SSID,
                    "bssid" to item.BSSID.lowercase(),
                    "level" to item.level,
                )
            }
            .sortedByDescending { it["level"] as Int }
            .toList()
        result.success(networks)
    }

    private fun requestWifiAccess(result: MethodChannel.Result) {
        val permissions = mutableListOf(Manifest.permission.ACCESS_FINE_LOCATION)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.NEARBY_WIFI_DEVICES)
        }
        val missing = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isEmpty()) {
            result.success(true)
            return
        }
        pendingWifiPermissionResult = result
        requestPermissions(missing.toTypedArray(), wifiPermissionRequestCode)
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == wifiPermissionRequestCode) {
            val granted = grantResults.isNotEmpty() && grantResults.all {
                it == PackageManager.PERMISSION_GRANTED
            }
            pendingWifiPermissionResult?.success(granted)
            pendingWifiPermissionResult = null
        }
    }
}
