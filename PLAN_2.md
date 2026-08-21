Изучи проект полностью и найди причину бага с ориентацией камеры при начале записи.

## Описание проблемы

Сейчас камера работает неправильно именно при нажатии **START REC / REC**.

Поведение:

1. Я открываю экран камеры.
2. До начала записи камера отображается **абсолютно нормально**.
3. Превью имеет правильную ориентацию.
4. Нажимаю **START REC / REC**.
5. В момент начала записи изображение камеры внезапно **поворачивается примерно на 90 градусов**.
6. То, что до записи было горизонтально относительно сцены, после начала записи становится вертикальным.
7. Когда запись останавливается и видео сохраняется, превью снова возвращается в нормальное положение.

То есть проблема возникает **ТОЛЬКО во время активной записи**.

Это хорошо видно на видео:

* `Ready` → камера нормальная.
* `Recording` → камера повернулась на 90°.
* `Saved / после STOP` → камера снова нормальная.

## Очень важно

Не нужно просто визуально повернуть весь экран или поставить случайный `Transform.rotate`.

Нужно найти **реальную причину**, почему START REC меняет ориентацию камеры.

До начала записи ориентация уже правильная, поэтому используй состояние камеры **до REC как эталон**.

После нажатия REC камера должна выглядеть **точно так же**, как за секунду до нажатия REC.

START REC должен только:

* начать запись видео;
* изменить статус `Ready` → `Recording`;
* сохранить файл в нужную папку;
* при необходимости показать STOP.

Он **НЕ должен менять**:

* rotation preview;
* aspect ratio;
* ориентацию камеры;
* размер/положение preview;
* sensor orientation;
* display rotation;
* front/back camera transform;
* масштаб камеры.

## Что необходимо проверить в коде

Найди весь код, который выполняется при:

* `START REC`
* `startRecording`
* `startVideoRecording`
* `VideoCapture`
* `MediaRecorder`
* CameraX
* Camera2
* Flutter camera plugin, если используется
* пересоздании Camera Controller
* bind/unbind камеры

Особенно проверь использование:

* `targetRotation`
* `setTargetRotation`
* `rotation`
* `deviceOrientation`
* `lockedCaptureOrientation`
* `lockCaptureOrientation`
* `sensorOrientation`
* `orientationHint`
* `setOrientationHint`
* `Surface.ROTATION_0`
* `Surface.ROTATION_90`
* `Surface.ROTATION_180`
* `Surface.ROTATION_270`
* `Transform.rotate`
* `RotatedBox`
* `Matrix`
* `TextureView`
* `PreviewView`
* `AspectRatio`
* `VideoCapture`
* `Recorder`
* `QualitySelector`

Проверь, не происходит ли при START REC что-то вроде:

```text
camera stop
→ camera reinitialize
→ VideoCapture initialize
→ новая rotation
→ preview получает другую orientation
```

или:

```text
Preview использует одну targetRotation,
а VideoCapture при REC использует другую targetRotation.
```

Это очень вероятный источник проблемы.

## Проверь также настройки Vertical / Horizontal

В Settings есть выбор ориентации:

* `Vertical`
* `Horizontal`

Не ломай эту систему.

Нужно четко разделить:

**ориентацию записываемого файла**

и

**ориентацию live preview камеры**.

Выбранный режим записи не должен неожиданно физически вращать preview после нажатия REC.

Если пользователь выбрал `Vertical`, это не значит, что при START REC существующее нормальное изображение надо повернуть на 90°.

Если необходимо установить metadata/rotation для сохраненного видео — делай это на уровне VideoCapture/MediaRecorder/output orientation, а не поворотом live preview.

## Правильное ожидаемое поведение

Например:

```text
Открыл камеру
↓
Preview NORMAL
↓
нажал START REC
↓
Preview NORMAL
↓
Recording...
↓
Preview NORMAL
↓
нажал STOP REC
↓
Saved
↓
Preview NORMAL
```

То есть визуально ориентация камеры должна оставаться неизменной весь цикл.

## Обязательно проверь

Если при START REC создается новый VideoCapture или Camera Controller, он должен получать ту же rotation, что Preview.

Например концептуально:

```text
previewRotation = currentDisplayRotation

Preview.targetRotation = previewRotation
VideoCapture.targetRotation = previewRotation
```

а не:

```text
Preview = ROTATION_0

START REC →

VideoCapture = ROTATION_90
Preview = ROTATION_90
```

Также не хардкодь `90°`, `270°` и т. д. без учета:

* ориентации сенсора камеры;
* текущей ориентации устройства;
* front/back camera;
* режима Vertical/Horizontal.

## Что нужно сделать

1. Сначала найди точное место в коде, из-за которого при START REC происходит поворот.

2. Объясни конкретно:

   * какой файл;
   * какой класс;
   * какая функция;
   * какая строка/логика вызывает изменение ориентации.

3. Исправь архитектурно, а не костылем.

4. Не меняй нормальную ориентацию Preview до записи.

5. Сделай так, чтобы начало/остановка записи вообще не влияли на rotation live preview.

6. Убедись, что сохраненное видео также имеет правильную ориентацию.

7. Проверь оба режима:

   * Vertical;
   * Horizontal.

8. Проверь полный сценарий:

```text
OPEN CAMERA
→ START REC
→ RECORD
→ STOP REC
→ SAVE
→ NEXT RECORD
```

Ориентация не должна прыгать ни на одном этапе.

## Важное ограничение

НЕ надо переписывать весь camera module без необходимости.

НЕ ломай существующие:

* START REC;
* STOP REC;
* сохранение видео;
* FPS;
* resolution;
* zoom;
* autofocus;
* auto brightness;
* reticle;
* работу нескольких устройств;
* названия камер;
* структуру папок.

Исправь именно проблему rotation/orientation.

## Главное правило

**Картинка непосредственно ДО нажатия START REC и картинка непосредственно ПОСЛЕ нажатия START REC должны иметь совершенно одинаковую ориентацию.**

Единственное визуальное изменение после START REC должно быть состояние `Recording`, а НЕ поворот камеры.

Сначала проведи анализ существующего кода и найди root cause, затем внеси исправление и покажи мне, какие файлы и какой код были изменены.
