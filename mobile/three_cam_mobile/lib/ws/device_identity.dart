import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

/// Device identity (network_architecture.md §Device Identity, protocol_specification.md
/// §Identity decision): the canonical `device_id` is a client-generated UUIDv4, created
/// once and persisted client-side - never derived from IP, never the native Android ID
/// (which doesn't exist on iOS and isn't what the new protocol keys sessions by).
class DeviceIdentity {
  static const _prefsKey = 'session_device_uuid';

  /// Returns the persisted UUID, generating and saving one on first call.
  static Future<String> getOrCreate() async {
    final prefs = await SharedPreferences.getInstance();
    final existing = prefs.getString(_prefsKey);
    if (existing != null && existing.isNotEmpty) {
      return existing;
    }
    final generated = const Uuid().v4();
    await prefs.setString(_prefsKey, generated);
    return generated;
  }
}
