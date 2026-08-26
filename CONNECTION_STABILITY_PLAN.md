# План: стабильная связь с телефонами при низком заряде

## Цель

Сделать так, чтобы связь с телефонами не обрывалась из-за Android battery saver / Doze / фоновых ограничений, пока оператор сам не остановит приложение или не отключит соединение.

Важно: Android не дает честной 100% гарантии "никогда" для обычного приложения, особенно если пользователь/система принудительно убивает процесс, телефон перегревается, отключается Wi-Fi или производитель агрессивно чистит фоновые процессы. Но можно сделать правильную архитектуру для максимально устойчивой связи:

- foreground service с постоянным уведомлением;
- partial wake lock для CPU;
- Wi-Fi lock для удержания Wi-Fi в активном режиме;
- запрос исключения из battery optimization;
- более надежный reconnect/heartbeat;
- корректная передача реального процента батареи в WS heartbeat.

## Что сейчас найдено

1. В Android-приложении есть только `FLAG_KEEP_SCREEN_ON`.
   - Файл: `mobile/three_cam_mobile/android/app/src/main/kotlin/com/example/three_cam_mobile/MainActivity.kt`
   - Это не дает телефону выключить экран, но не защищает CPU, Dart timers, WebSocket и Wi-Fi от энергосбережения.

2. В `AndroidManifest.xml` нет разрешений:
   - `WAKE_LOCK`
   - `FOREGROUND_SERVICE`
   - `FOREGROUND_SERVICE_CAMERA`
   - `FOREGROUND_SERVICE_MICROPHONE`
   - `FOREGROUND_SERVICE_CONNECTED_DEVICE`
   - `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`

3. WS heartbeat отправляется каждые 5 секунд.
   - Файл: `mobile/three_cam_mobile/lib/ws/ws_client.dart`
   - Сервер помечает телефон `SUSPECT` через 15 секунд без heartbeat и `OFFLINE` через 30 секунд.

4. В WS heartbeat сейчас отправляется `batteryPct: 0`, хотя Android-часть умеет читать реальный заряд.
   - Это не главная причина обрыва, но это ошибка мониторинга.

5. Reconnect уже есть, но он зависит от того, что Dart isolate продолжает работать. При low battery / Doze это может быть недостаточно.

## Предлагаемые изменения

### 1. Добавить Android foreground service

Создать нативный сервис `ConnectionKeepAliveService`.

Он будет запускаться, когда мобильное приложение готово к работе с камерой/сетью, и останавливаться только при закрытии приложения или явной команде.

Сервис должен:

- показывать постоянное уведомление `Three Cam active`;
- держать приложение в foreground process state;
- удерживать partial wake lock;
- удерживать Wi-Fi lock;
- не трогать бизнес-логику камеры напрямую.

Типы foreground service:

- `camera`, потому что приложение активно использует камеру;
- `microphone`, если включен звук;
- `connectedDevice` или `dataSync` для постоянной сетевой связи с PC.

Финальный набор типов нужно выбрать аккуратно под текущий target SDK и Android Manifest, чтобы не получить `SecurityException` на Android 14+.

и еще дополнително убрать функцию авто изменение яркости что бы яркость не ирграла при движении

### 2. Добавить нужные permissions в AndroidManifest

Добавить:

- `android.permission.WAKE_LOCK`
- `android.permission.FOREGROUND_SERVICE`
- `android.permission.FOREGROUND_SERVICE_CAMERA`
- `android.permission.FOREGROUND_SERVICE_MICROPHONE`
- `android.permission.FOREGROUND_SERVICE_CONNECTED_DEVICE`
- `android.permission.FOREGROUND_SERVICE_DATA_SYNC`, если выберем `dataSync`
- `android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`
- при необходимости `android.permission.POST_NOTIFICATIONS` для Android 13+

Также объявить сам service с `android:foregroundServiceType`.

### 3. Добавить MethodChannel-команды из Flutter

В `MainActivity.kt` добавить команды:

- `startKeepAliveService`
- `stopKeepAliveService`
- `isIgnoringBatteryOptimizations`
- `requestIgnoreBatteryOptimizations`

Flutter будет вызывать старт сервиса после boot приложения.

### 4. Запросить исключение из Battery Optimization

Добавить экранное/системное действие, которое открывает Android prompt/settings для исключения приложения из battery optimization.

Логика:

- проверить `PowerManager.isIgnoringBatteryOptimizations(packageName)`;
- если не исключено, дать пользователю системный запрос через `ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`;
- показывать в UI статус, включено исключение или нет.

Без подтверждения пользователя Android не разрешает приложению само выключить battery optimization.

### 5. Исправить WS heartbeat batteryPct

В `ws_client.dart` заменить `batteryPct: 0` на реальное значение из `deviceStatusProvider()`:

- читать `status['batteryPercent']`;
- аккуратно приводить к `double`;
- если значения нет, отправлять `0`.

Это позволит серверу и dashboard видеть реальную батарею через новый WS-путь.

### 6. Усилить reconnect

Проверить и при необходимости улучшить:

- очистку старого `_subscription` при обрыве;
- повторное подключение после `channel.ready` error;
- отправку heartbeat сразу после reconnect;
- логирование причин disconnect/reconnect в UI;
- защиту от нескольких параллельных reconnect timers.

Цель: если Wi-Fi коротко пропал, телефон автоматически возвращается без ручного вмешательства.

### 7. Не ломать legacy HTTP workflow

Существующие endpoints должны остаться рабочими:

- `/status`
- `/start`
- `/stop`
- `/videos`
- `/download`

Foreground service должен только держать процесс/сеть живыми, а не менять запись видео и dataset workflow.

### 8. Проверка после изменений

Проверить:

- `flutter analyze`
- `flutter test`
- сборку APK, если локальная среда позволит;
- существующие Python tests для server;
- ручной сценарий:
  - телефон ниже 20%;
  - телефон подключен к зарядке;
  - battery saver включен;
  - экран выключен/заблокирован;
  - запись идет;
  - dashboard продолжает видеть телефон connected.

## Что может потребовать ручного действия

На каждом телефоне, скорее всего, нужно будет один раз подтвердить:

- разрешение уведомлений на Android 13+;
- исключение Three Cam из battery optimization;
- возможно, OEM-настройки типа "Allow background activity", "No restrictions", "Auto launch".

Без этих ручных разрешений некоторые телефоны Xiaomi/Huawei/Oppo/Vivo/Samsung все равно могут убивать сетевую активность агрессивнее стандартного Android.

## Источники Android

- Wake locks: https://developer.android.com/develop/background-work/background-tasks/awake/wakelock
- Wake lock best practices: https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/best-practices
- Doze and App Standby: https://developer.android.com/training/monitoring-device-state/doze-standby
- Foreground service types: https://developer.android.com/develop/background-work/services/fgs/service-types
- Android 14 foreground service type requirements: https://developer.android.com/about/versions/14/changes/fgs-types-required

## После подтверждения

После твоего подтверждения я начну реализацию по этому плану:

1. внесу Android native service и permissions;
2. подключу MethodChannel из Flutter;
3. исправлю WS heartbeat battery percent;
4. улучшу reconnect там, где это нужно;
5. прогоню проверки и покажу результат.
