# Анализ recording logs: 2026-08-24 - 2026-09-24

Сегодняшний лог `recording_log_20260925.ndjson` не анализировался.

## Короткий вывод

- Прочитано файлов: 22 из диапазона; JSON-строк: 193 971; ошибок парсинга: 0.
- Успешных сессий: 16 558 из 16 707 (99.11%). Проблемных сессий: 149.
- Сохранено видеофайлов: 49 978. Суммарные видео-часы по всем камерам: 94:02:47. Реальное съемочное время по сессиям: 31:31:17.
- Из видео-часов примерно 31:16:18 оценено по `START` -> `STOP`, потому что старые `STOP_SAVE` не всегда содержат `duration_ms`; остальные длительности взяты напрямую из логов.
- Объем сохраненных видео по логам: 328.74 GB.
- START_FAILED: 176; EMERGENCY_STOP: 46.
- Не все идеально: главные проблемы связаны с недоступностью телефонов/таймаутами статуса. Сохранение успешных сессий в основном штатное: почти всегда 3 файла на сессию.

## Какие дни есть и каких нет

Файлы найдены: 2026-08-24, 2026-08-25, 2026-08-26, 2026-08-27, 2026-08-28, 2026-09-02, 2026-09-03, 2026-09-04, 2026-09-05, 2026-09-07, 2026-09-09, 2026-09-10, 2026-09-11, 2026-09-15, 2026-09-16, 2026-09-17, 2026-09-18, 2026-09-19, 2026-09-21, 2026-09-22, 2026-09-23, 2026-09-24.

Нет файлов за даты: 2026-08-29, 2026-08-30, 2026-08-31, 2026-09-01, 2026-09-06, 2026-09-08, 2026-09-12, 2026-09-13, 2026-09-14, 2026-09-20.

## Итого по дням

| Дата | Время в логе | Сессии | OK | Проблемные | START_FAILED | EMERGENCY_STOP | Видеофайлы | Видео-часы | Съемочное время | Объем |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-24 | 13:39:57-18:42:43 | 1344 | 1339 | 5 | 25 | 0 | 4019 | 7:12:43 | 2:24:15 | 25.34 GB |
| 2026-08-25 | 13:24:06-18:15:34 | 1275 | 1275 | 0 | 9 | 0 | 3825 | 6:30:47 | 2:10:16 | 22.54 GB |
| 2026-08-26 | 13:32:35-19:00:09 | 1605 | 1587 | 18 | 9 | 15 | 4805 | 7:30:07 | 2:30:19 | 26.06 GB |
| 2026-08-27 | 10:23:22-17:38:59 | 1513 | 1467 | 46 | 25 | 29 | 4488 | 7:15:17 | 2:25:06 | 25.54 GB |
| 2026-08-28 | 09:18:08-09:42:50 | 160 | 157 | 3 | 2 | 2 | 477 | 0:43:01 | 0:14:20 | 2.54 GB |
| 2026-09-02 | 12:26:37-12:26:37 | 0 | 0 | 0 | 1 | 0 | 0 | 0:00:00 | 0:00:00 | 0.00 GB |
| 2026-09-03 | 14:21:44-15:30:17 | 12 | 12 | 0 | 4 | 0 | 36 | 0:03:49 | 0:01:16 | 0.04 GB |
| 2026-09-04 | 09:50:44-16:27:58 | 333 | 321 | 12 | 16 | 0 | 965 | 1:38:27 | 0:32:56 | 5.78 GB |
| 2026-09-05 | 15:23:24-15:44:54 | 56 | 56 | 0 | 2 | 0 | 168 | 0:22:07 | 0:07:22 | 1.31 GB |
| 2026-09-07 | 11:33:57-11:33:57 | 0 | 0 | 0 | 1 | 0 | 0 | 0:00:00 | 0:00:00 | 0.00 GB |
| 2026-09-09 | 02:37:33-13:35:01 | 432 | 430 | 2 | 9 | 0 | 1296 | 2:15:29 | 0:45:25 | 7.61 GB |
| 2026-09-10 | 10:44:31-16:19:52 | 613 | 610 | 3 | 5 | 0 | 1839 | 3:29:15 | 1:10:09 | 12.32 GB |
| 2026-09-11 | 13:40:56-13:56:24 | 98 | 96 | 2 | 1 | 0 | 291 | 0:30:18 | 0:10:10 | 1.78 GB |
| 2026-09-15 | 15:37:24-18:32:16 | 716 | 711 | 5 | 25 | 0 | 2148 | 3:59:44 | 1:20:36 | 14.04 GB |
| 2026-09-16 | 11:41:03-15:53:46 | 941 | 932 | 9 | 4 | 0 | 2810 | 5:04:46 | 1:42:30 | 17.38 GB |
| 2026-09-17 | 09:39:28-17:00:06 | 1334 | 1329 | 5 | 5 | 0 | 4002 | 8:13:06 | 2:45:39 | 29.16 GB |
| 2026-09-18 | 10:18:08-17:16:34 | 1062 | 1059 | 3 | 3 | 0 | 3183 | 6:42:19 | 2:15:02 | 23.78 GB |
| 2026-09-19 | 09:50:24-15:11:44 | 955 | 948 | 7 | 10 | 0 | 2862 | 6:40:21 | 2:14:26 | 23.60 GB |
| 2026-09-21 | 10:57:06-16:07:34 | 1029 | 1021 | 8 | 5 | 0 | 3084 | 6:13:23 | 2:05:33 | 21.66 GB |
| 2026-09-22 | 09:57:30-17:26:18 | 816 | 810 | 6 | 2 | 0 | 2448 | 4:55:27 | 1:39:25 | 17.26 GB |
| 2026-09-23 | 11:14:32-16:33:35 | 860 | 855 | 5 | 2 | 0 | 2579 | 4:59:31 | 1:40:42 | 17.00 GB |
| 2026-09-24 | 11:26:26-18:01:43 | 1553 | 1543 | 10 | 11 | 0 | 4653 | 9:42:51 | 3:15:47 | 34.00 GB |

## Кто сколько снимал

`Съемочное время` - длительность сессий для человека. `Видео-часы` - сумма длительностей всех сохраненных камер.

| Исполнитель | Дней | Сессии | OK | Проблемные | START_FAILED | EMERGENCY_STOP | Видеофайлы | Видео-часы | Съемочное время | Режимы |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Муслима (signer_8) | 9 | 1822 | 1812 | 10 | 27 | 3 | 5462 | 10:39:55 | 3:34:28 | phrase:1402, word:410, background:10 |
| Лазокат (signer_10) | 7 | 1691 | 1680 | 11 | 7 | 5 | 5073 | 10:06:28 | 3:23:11 | phrase:1036, word:643, background:12 |
| Фазилят (signer_3) | 9 | 1669 | 1654 | 15 | 8 | 8 | 5006 | 9:43:08 | 3:15:22 | phrase:978, word:680, background:11 |
| Азиза (signer_15) | 9 | 1628 | 1624 | 4 | 34 | 0 | 4884 | 9:14:21 | 3:05:33 | phrase:996, word:618, background:14 |
| Шоира (signer_1) | 11 | 1690 | 1672 | 18 | 24 | 11 | 5070 | 9:11:05 | 3:04:42 | phrase:1047, word:625, background:18 |
| Дилназ (signer_4) | 10 | 1553 | 1543 | 10 | 28 | 3 | 4655 | 8:04:05 | 2:42:30 | phrase:911, word:632, background:10 |
| Адолат (signer_2) | 11 | 1571 | 1564 | 7 | 9 | 3 | 4713 | 8:03:08 | 2:41:54 | phrase:935, word:622, background:14 |
| Нафиса (signer_9) | 11 | 1420 | 1410 | 10 | 9 | 3 | 4256 | 7:48:23 | 2:37:17 | phrase:773, word:627, background:20 |
| Намуна (signer_7) | 10 | 1211 | 1202 | 9 | 14 | 7 | 3633 | 7:21:39 | 2:27:56 | phrase:765, word:430, background:16 |
| Парогат (signer_6) | 7 | 1216 | 1209 | 7 | 10 | 2 | 3648 | 7:20:12 | 2:27:31 | word:626, phrase:582, background:8 |
| Шахзода_1 (signer_5) | 8 | 1193 | 1188 | 5 | 6 | 1 | 3578 | 6:30:25 | 2:10:53 | phrase:785, word:401, background:7 |
| unknown (unknown) | 11 | 43 | 0 | 43 | 0 | 0 | 0 | 0:00:00 | 0:00:00 |  |

## Камеры / телефоны

| Устройство | START_ACK ok | Видеофайлы | Видео-часы | Объем | Средний FPS | Средняя длительность файла |
|---|---:|---:|---:|---:|---:|---:|
| device_1 | 16664 | 16661 | 31:20:51 | 110.36 GB | 29.906 | 0:00:07 |
| device_2 | 16664 | 16661 | 31:21:03 | 110.14 GB | 29.899 | 0:00:07 |
| device_3 | 16664 | 16656 | 31:20:54 | 108.24 GB | 29.897 | 0:00:07 |

## Качество синхронизации и FPS

- Проверок длительности: 10400. Средний разброс между камерами: 110 ms; медиана: 71 ms; максимум: 10231 ms.
- FPS по проверкам: средний 29.898; минимум 0.177; максимум 29.948.
- Средняя длительность сессии: 0:00:07; медиана: 0:00:06; максимум: 0:00:55.

## Проблемы

### START_FAILED

| Причина | Количество |
|---|---:|
| connected 0/3 phones / recording blocked | 26 |
| status timed out | 23 |
| ERROR: РќРµР»СЊР·СЏ РЅР°С‡Р°С‚СЊ Р·Р°РїРёСЃСЊ:; device_3: РЅРёР·РєРёР№ Р·Р°СЂСЏРґ Р±Р°С‚Р°СЂРµРё 14% (РЅСѓР¶РЅРѕ РјРёРЅРё | 13 |
| ERROR: WARNING: configured 2/3 phones. Recording blocked. | 12 |
| ERROR: Нельзя начать запись:; device_2: низкий заряд батареи 14% (нужно минимум 15%, не на зарядке) | 10 |
| ERROR: РќРµР»СЊР·СЏ РЅР°С‡Р°С‚СЊ Р·Р°РїРёСЃСЊ:; device_3: РЅРёР·РєРёР№ Р·Р°СЂСЏРґ Р±Р°С‚Р°СЂРµРё 12% (РЅСѓР¶РЅРѕ РјРёРЅРё | 10 |
| ERROR: START blocked: device_2: ERROR: HTTP Error 500: Internal Server Error; device_1: ERROR: HTTP Error 500: Internal  | 9 |
| ERROR: START blocked: device_1: ERROR: HTTP Error 500: Internal Server Error; device_2: ERROR: HTTP Error 500: Internal  | 8 |
| ERROR: Нельзя начать запись:; device_2: низкий заряд батареи 13% (нужно минимум 15%, не на зарядке) | 7 |
| ERROR: START blocked: device_2: ERROR: HTTP Error 500: Internal Server Error; device_3: ERROR: HTTP Error 500: Internal  | 5 |
| ERROR: START blocked: device_3: ERROR: HTTP Error 500: Internal Server Error; device_1: ERROR: HTTP Error 500: Internal  | 5 |
| ERROR: РќРµР»СЊР·СЏ РЅР°С‡Р°С‚СЊ Р·Р°РїРёСЃСЊ:; device_3: РЅРёР·РєРёР№ Р·Р°СЂСЏРґ Р±Р°С‚Р°СЂРµРё 13% (РЅСѓР¶РЅРѕ РјРёРЅРё | 5 |
| ERROR: WARNING: connected 2/3 phones. Recording blocked.; Missing: device_2 http://192.168.0.102:8088 | 4 |
| ERROR: START blocked: device_1: ERROR: HTTP Error 500: Internal Server Error; device_3: ERROR: HTTP Error 500: Internal  | 4 |
| ERROR: РќРµР»СЊР·СЏ РЅР°С‡Р°С‚СЊ Р·Р°РїРёСЃСЊ:; device_1: РЅРёР·РєРёР№ Р·Р°СЂСЏРґ Р±Р°С‚Р°СЂРµРё 14% (РЅСѓР¶РЅРѕ РјРёРЅРё | 4 |
| ERROR: РќРµР»СЊР·СЏ РЅР°С‡Р°С‚СЊ Р·Р°РїРёСЃСЊ:; device_2: РЅРёР·РєРёР№ Р·Р°СЂСЏРґ Р±Р°С‚Р°СЂРµРё 14% (РЅСѓР¶РЅРѕ РјРёРЅРё | 4 |
| ERROR: WARNING: connected 2/3 phones. Recording blocked.; Missing: device_2 http://192.168.0.100:8088 | 2 |
| ERROR: WARNING: connected 2/3 phones. Recording blocked.; Missing: device_1 http://192.168.0.101:8088 | 2 |
| ERROR: START blocked: device_3: ERROR: HTTP Error 500: Internal Server Error; device_2: ERROR: HTTP Error 500: Internal  | 2 |
| ERROR: WARNING: connected 2/3 phones. Recording blocked.; Missing: device_3 http://192.168.0.101:8088 | 2 |
| ERROR: START blocked: device_3: ERROR: HTTP Error 500: Internal Server Error; connected started 2/3 | 2 |
| ERROR: START blocked: device_2: ERROR: timeout; device_1: ERROR: timeout; device_3: ERROR: timeout; connected started 0/ | 2 |
| ERROR: Нельзя начать запись:; device_1: низкий заряд батареи 14% (нужно минимум 15%, не на зарядке) | 2 |
| ERROR: START blocked: device_1: ERROR: timeout; device_2: ERROR: timeout; device_3: ERROR: timeout; connected started 0/ | 2 |
| ERROR: START blocked: device_1: ERROR: HTTP Error 500: Internal Server Error; connected started 2/3 | 1 |
| ERROR: WARNING: connected 2/3 phones. Recording blocked.; Missing: device_3 http://not connected:8088 | 1 |
| ERROR: WARNING: connected 2/3 phones. Recording blocked.; Missing: device_3 http://192.168.0.100:8088 | 1 |
| ERROR: WARNING: connected 2/3 phones. Recording blocked.; Missing: device_1 http://192.168.0.104:8088 | 1 |
| ERROR: WARNING: connected 1/3 phones. Recording blocked.; Missing: device_3 http://192.168.0.101:8088, device_1 http://19 | 1 |
| ERROR: WARNING: connected 1/3 phones. Recording blocked.; Missing: device_3 http://192.168.0.102:8088, device_2 http://19 | 1 |
| ERROR: START blocked: device_2: ERROR: HTTP Error 500: Internal Server Error; connected started 2/3 | 1 |
| ERROR: WARNING: connected 2/3 phones. Recording blocked.; Missing: device_2 http://not connected:8088 | 1 |
| ERROR: WARNING: connected 2/3 phones. Recording blocked.; Missing: device_2 http://192.168.0.105:8088 | 1 |
| ERROR: START blocked: device_3: ERROR: timeout; device_1: ERROR: timeout; device_2: ERROR: timeout; connected started 0/ | 1 |
| ERROR: START blocked: device_3: ERROR: timeout; device_2: ERROR: timeout; device_1: ERROR: timeout; connected started 0/ | 1 |

Устройства, упомянутые в ошибках START_FAILED: device_3: 112, device_2: 103, device_1: 84.

### EMERGENCY_STOP

Всего: 46. Это аварийные остановки уже начатых сессий, в основном из-за `no status` / `timed out`.
Устройства, упомянутые в EMERGENCY_STOP: device_3: 27, device_2: 25, device_1: 23.

| Дата | Сессия | Исполнитель | Слово/фраза | Причина |
|---|---|---|---|---|
| 2026-08-26 | 20260826_133911_32 | Фазилят | Sabotli (qattiq turmoq, sabot, ma-tonat) | device_2: no status (<urlopen error timed out>); device_3: no status (<urlopen error timed out>) |
| 2026-08-26 | 20260826_135602_140 | Фазилят | Shvetsiya | device_2: no status (<urlopen error timed out>); device_1: no status (<urlopen error timed out>) |
| 2026-08-26 | 20260826_141030_227 | Шоира | Bilmaslik (xabardor bo'lmaslik) | device_2: no status (<urlopen error timed out>); device_1: no status (<urlopen error timed out>) |
| 2026-08-26 | 20260826_142136_313 | Шоира | Hollandiya | device_1: no status (<urlopen error timed out>) |
| 2026-08-26 | 20260826_142555_332 | Шоира | Latviya | device_1: no status (<urlopen error timed out>); device_3: no status (<urlopen error timed out>) |
| 2026-08-26 | 20260826_142959_366 | Шоира | Qozon | device_2: no status (<urlopen error timed out>) |
| 2026-08-26 | 20260826_153027_806 | Адолат | Milliy | device_2: no status (<urlopen error timed out>) |
| 2026-08-26 | 20260826_165539_879 | Лазокат | Karam | device_2: no status (<urlopen error timed out>); device_3: no status (<urlopen error timed out>) |
| 2026-08-26 | 20260826_170952_990 | Лазокат | Mo'ylov | device_3: no status (<urlopen error timed out>); device_1: no status (<urlopen error timed out>) |
| 2026-08-26 | 20260826_172124_1069 | Лазокат | G'oya | device_3: no status (<urlopen error timed out>) |
| 2026-08-26 | 20260826_172533_1102 | Лазокат | O'g'ri (o'g'irlamoq, o'g'irlash,o'g'rilik) | device_3: no status (<urlopen error timed out>) |
| 2026-08-26 | 20260826_172649_1111 | Лазокат | Yoqalashish | device_1: no status (<urlopen error timed out>) |
| 2026-08-26 | 20260826_175354_1285 | Нафиса | Parad | device_3: no status (<urlopen error timed out>) |
| 2026-08-26 | 20260826_180452_1340 | Нафиса | Don (urug') | device_3: no status (<urlopen error timed out>); device_1: no status (<urlopen error timed out>); device_2: no status (<urlopen error timed out>) |
| 2026-08-26 | 20260826_180627_1349 | Нафиса | Xo’roz | device_1: no status (<urlopen error timed out>); device_3: no status (<urlopen error timed out>); device_2: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_103405_1652 | Парогат | Tanlov | device_1: no status (<urlopen error timed out>); device_3: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_105646_1706 | Парогат | Pharﬁ | device_2: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_134634_1777 | Шоира | Parad | device_3: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_140025_1839 | Шоира | Suv quymoq, sug'orish | device_1: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_140802_1868 | Шоира | Qharﬁ | device_1: no status (<urlopen error timed out>); device_3: no status (<urlopen error timed out>); device_2: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_140818_1870 | Шоира | Sharﬁ | device_3: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_141331_1905 | Шоира | 17 | device_1: no status (<urlopen error timed out>); device_2: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_141736_1928 | Шоира | 1000000000 | device_1: no status (<urlopen error timed out>); device_2: no status (<urlopen error timed out>); device_3: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_141757_1929 | Шоира | background | device_3: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_142559_1976 | Дилназ | So'roq (tergovchi) | device_2: no status (<urlopen error timed out>); device_1: no status (<urlopen error timed out>); device_3: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_142950_2007 | Дилназ | Yurist, huquqshunos | device_1: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_144852_2143 | Фазилят | Medal | device_3: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_145713_2202 | Фазилят | Don (urug') | device_2: no status (<urlopen error timed out>); device_1: no status (<urlopen error timed out>); device_3: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_150122_2228 | Фазилят | Eharﬁ | device_2: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_150451_2253 | Фазилят | Ch harﬁ | device_2: no status (<urlopen error timed out>); device_3: no status (<urlopen error timed out>); device_1: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_150538_2258 | Фазилят | Tomchi | device_3: no status (<urlopen error timed out>); device_2: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_150813_2275 | Фазилят | 14 | device_1: no status (<urlopen error timed out>); device_2: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_152212_2367 | Дилназ | Tovuq | device_2: no status (<urlopen error timed out>); device_1: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_162601_2641 | Шахзода_1 | Jarohat (yaralanish) | device_3: no status (<urlopen error timed out>); device_2: no status (<urlopen error timed out>); device_1: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_165145_2801 | Намуна | Tank | device_3: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_165829_2848 | Намуна | Dehqon | device_2: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_165851_2851 | Намуна | Cho'pon | device_2: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_165907_2853 | Намуна | Dala | device_3: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_165952_2855 | Намуна | Suv quymoq, sug'orish | device_3: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_170041_2859 | Намуна | Urug' qadamoq, sepmoq | device_2: no status (<urlopen error timed out>); device_3: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_170154_2864 | Намуна | Xo'jalik (ferma) | device_3: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_171954_2976 | Муслима | Muallif | device_2: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_172245_2994 | Муслима | Ashula aytmoq | device_1: no status (<urlopen error timed out>) |
| 2026-08-27 | 20260827_173602_3094 | Муслима | 17 | device_1: no status (<urlopen error timed out>) |
| 2026-08-28 | 20260828_093442_3212 | Адолат | Lharﬁ | device_3: no status (timed out) |
| 2026-08-28 | 20260828_093542_3220 | Адолат | Tharﬁ | device_1: no status (<urlopen error timed out>); device_2: no status (<urlopen error timed out>) |

### Проблемные сессии

| Дата | Сессия | Исполнитель | Слово/фраза | Причины | STOP_SAVE ok | Длительность | Разброс |
|---|---|---|---|---|---:|---:|---:|
| 2026-08-24 | 20260824_171059_987 | Муслима | Albaniya | STOP_SAVE ok 2/3; SESSION_CHECK failed=1 | 2/3 | 0:00:03 |  |
| 2026-08-24 | 20260824_171111_988 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-24 | 20260824_171120_989 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-24 | 20260824_171208_990 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-24 | 20260824_171224_991 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-26 | 20260826_133911_32 | Фазилят | Sabotli (qattiq turmoq, sabot, ma-tonat) | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-26 | 20260826_135602_140 | Фазилят | Shvetsiya | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-26 | 20260826_141030_227 | Шоира | Bilmaslik (xabardor bo'lmaslik) | EMERGENCY_STOP | 3/3 | 0:00:06 |  |
| 2026-08-26 | 20260826_142136_313 | Шоира | Hollandiya | EMERGENCY_STOP | 3/3 | 0:00:04 |  |
| 2026-08-26 | 20260826_142555_332 | Шоира | Latviya | EMERGENCY_STOP | 3/3 | 0:00:06 |  |
| 2026-08-26 | 20260826_142959_366 | Шоира | Qozon | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-26 | 20260826_153027_806 | Адолат | Milliy | EMERGENCY_STOP | 3/3 | 0:00:04 |  |
| 2026-08-26 | 20260826_164657_849 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-26 | 20260826_164721_850 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-26 | 20260826_164730_851 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-26 | 20260826_165539_879 | Лазокат | Karam | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-26 | 20260826_170952_990 | Лазокат | Mo'ylov | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-26 | 20260826_172124_1069 | Лазокат | G'oya | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-26 | 20260826_172533_1102 | Лазокат | O'g'ri (o'g'irlamoq, o'g'irlash,o'g'rilik) | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-26 | 20260826_172649_1111 | Лазокат | Yoqalashish | EMERGENCY_STOP | 3/3 | 0:00:04 |  |
| 2026-08-26 | 20260826_175354_1285 | Нафиса | Parad | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-26 | 20260826_180452_1340 | Нафиса | Don (urug') | EMERGENCY_STOP | 3/3 | 0:00:08 |  |
| 2026-08-26 | 20260826_180627_1349 | Нафиса | Xo’roz | STOP_SAVE ok 2/3; SESSION_CHECK failed=1; EMERGENCY_STOP | 2/3 | 0:00:51 |  |
| 2026-08-27 | 20260827_103405_1652 | Парогат | Tanlov | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-27 | 20260827_105646_1706 | Парогат | Pharﬁ | EMERGENCY_STOP | 3/3 | 0:00:05 |  |
| 2026-08-27 | 20260827_134634_1777 | Шоира | Parad | EMERGENCY_STOP | 3/3 | 0:00:05 |  |
| 2026-08-27 | 20260827_140025_1839 | Шоира | Suv quymoq, sug'orish | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-27 | 20260827_140802_1868 | Шоира | Qharﬁ | EMERGENCY_STOP | 3/3 | 0:00:04 |  |
| 2026-08-27 | 20260827_140818_1870 | Шоира | Sharﬁ | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-27 | 20260827_141331_1905 | Шоира | 17 | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-27 | 20260827_141736_1928 | Шоира | 1000000000 | EMERGENCY_STOP | 3/3 | 0:00:07 |  |
| 2026-08-27 | 20260827_141757_1929 | Шоира | background | EMERGENCY_STOP | 3/3 | 0:00:13 |  |
| 2026-08-27 | 20260827_142559_1976 | Дилназ | So'roq (tergovchi) | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-27 | 20260827_142950_2007 | Дилназ | Yurist, huquqshunos | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-27 | 20260827_144852_2143 | Фазилят | Medal | EMERGENCY_STOP | 3/3 | 0:00:05 |  |
| 2026-08-27 | 20260827_145713_2202 | Фазилят | Don (urug') | EMERGENCY_STOP | 3/3 | 0:00:05 |  |
| 2026-08-27 | 20260827_150122_2228 | Фазилят | Eharﬁ | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-27 | 20260827_150451_2253 | Фазилят | Ch harﬁ | EMERGENCY_STOP | 3/3 | 0:00:05 |  |
| 2026-08-27 | 20260827_150538_2258 | Фазилят | Tomchi | EMERGENCY_STOP | 3/3 | 0:00:04 |  |
| 2026-08-27 | 20260827_150813_2275 | Фазилят | 14 | EMERGENCY_STOP | 3/3 | 0:00:06 |  |
| 2026-08-27 | 20260827_152212_2367 | Дилназ | Tovuq | EMERGENCY_STOP | 3/3 | 0:00:04 |  |
| 2026-08-27 | 20260827_154318_2468 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_154329_2469 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_154338_2470 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_154346_2471 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_162601_2641 | Шахзода_1 | Jarohat (yaralanish) | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-27 | 20260827_165145_2801 | Намуна | Tank | EMERGENCY_STOP | 3/3 | 0:00:05 |  |
| 2026-08-27 | 20260827_165829_2848 | Намуна | Dehqon | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-27 | 20260827_165851_2851 | Намуна | Cho'pon | EMERGENCY_STOP | 3/3 | 0:00:04 |  |
| 2026-08-27 | 20260827_165907_2853 | Намуна | Dala | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-27 | 20260827_165952_2855 | Намуна | Suv quymoq, sug'orish | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-27 | 20260827_170041_2859 | Намуна | Urug' qadamoq, sepmoq | EMERGENCY_STOP | 3/3 | 0:00:04 |  |
| 2026-08-27 | 20260827_170154_2864 | Намуна | Xo'jalik (ferma) | EMERGENCY_STOP | 3/3 | 0:00:04 |  |
| 2026-08-27 | 20260827_171954_2976 | Муслима | Muallif | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-27 | 20260827_172245_2994 | Муслима | Ashula aytmoq | EMERGENCY_STOP | 3/3 | 0:00:05 |  |
| 2026-08-27 | 20260827_172513_3011 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_172523_3012 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_172525_3013 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_172526_3014 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_172538_3015 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_172540_3016 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_172542_3017 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_172543_3018 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_172544_3019 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_172546_3020 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_172547_3021 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_172556_3022 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_172558_3023 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-08-27 | 20260827_173602_3094 | Муслима | 17 | EMERGENCY_STOP | 3/3 | 0:00:04 |  |
| 2026-08-28 | 20260828_093442_3212 | Адолат | Lharﬁ | EMERGENCY_STOP | 3/3 | 0:00:04 |  |
| 2026-08-28 | 20260828_093542_3220 | Адолат | Tharﬁ | EMERGENCY_STOP | 3/3 | 0:00:03 |  |
| 2026-08-28 | 20260828_093731_3236 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-04 | 20260904_162204_310 | Дилназ | Maktab | STOP_SAVE ok 2/3 | 2/3 | 0:00:22 |  |
| 2026-09-04 | 20260904_162253_311 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-04 | 20260904_162257_312 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-04 | 20260904_162307_313 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-04 | 20260904_162309_314 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-04 | 20260904_162310_315 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-04 | 20260904_162325_316 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-04 | 20260904_162403_317 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-04 | 20260904_162409_318 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-04 | 20260904_162424_319 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-04 | 20260904_162427_320 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-04 | 20260904_162444_321 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-09 | 20260909_114443_24 | Муслима | Haykal (monument) | duration_check=false | 3/3 | 0:00:12 | 3052 ms |
| 2026-09-09 | 20260909_120157_68 | Фазилят | Yarim | duration_check=false | 3/3 | 0:00:10 | 3020 ms |
| 2026-09-10 | 20260910_114527_175 | Нафиса | Navbatim qachon keladi? | duration_check=false | 3/3 | 0:00:08 | 2162 ms |
| 2026-09-10 | 20260910_133339_413 | Муслима | Men ta'til olmoqchiman. | duration_check=false | 3/3 | 0:00:11 | 3169 ms |
| 2026-09-10 | 20260910_135944_500 | Азиза | Manzilim shu yerda. | duration_check=false | 3/3 | 0:00:10 | 2081 ms |
| 2026-09-11 | 20260911_134622_34 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-11 | 20260911_135348_83 | Нафиса | Rasm yuboring. | duration_check=false | 3/3 | 0:00:12 | 4908 ms |
| 2026-09-15 | 20260915_153858_1 | Намуна | Qosh бровь | duration_check=false | 3/3 | 0:00:09 | 2299 ms |
| 2026-09-15 | 20260915_161854_226 | Шоира | Peshona лоб | duration_check=false | 3/3 | 0:00:09 | 3029 ms |
| 2026-09-15 | 20260915_162938_290 | Шоира | Ko'rmoq видеть | duration_check=false | 3/3 | 0:00:07 | 2152 ms |
| 2026-09-15 | 20260915_170650_401 | Шоира | Pulimni o'g'irlashdi. Уменя украли деньги. | duration_check=false | 3/3 | 0:00:10 | 2090 ms |
| 2026-09-15 | 20260915_172552_434 | Намуна | Men hayajondaman. Яволнуюсь. | duration_check=false | 3/3 | 0:00:11 | 3154 ms |
| 2026-09-16 | 20260916_114248_2 | Шоира | Retseptim yo'q. Уменя нет рецепта. | duration_check=false | 3/3 | 0:00:09 | 1875 ms |
| 2026-09-16 | 20260916_125057_176 | Муслима | Ish suhbati собеседование | duration_check=false | 3/3 | 0:00:10 | 1750 ms |
| 2026-09-16 | 20260916_133818_375 | Муслима | Ko'rmoq видеть | STOP_SAVE ok 0/3; SESSION_CHECK failed=3 | 0/3 | 0:00:04 |  |
| 2026-09-16 | 20260916_133818_376 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-16 | 20260916_135418_464 | Азиза | Baland высокий | duration_check=false | 3/3 | 0:00:13 | 3850 ms |
| 2026-09-16 | 20260916_142214_572 | Нафиса | Toq нечётный | duration_check=false | 3/3 | 0:00:09 | 3046 ms |
| 2026-09-16 | 20260916_145336_654 | Дилназ | Bo'yin шея | нет STOP; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-16 | 20260916_145435_655 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-16 | 20260916_153613_844 | Фазилят | Qattiq твёрдый / жёсткий | STOP_SAVE ok 2/3; SESSION_CHECK failed=1 | 2/3 | 0:00:03 | 149 ms |
| 2026-09-17 | 20260917_100827_102 | Шоира | Birga boramizmi? Пойдём вместе? | duration_check=false | 3/3 | 0:00:23 | 10231 ms |
| 2026-09-17 | 20260917_101233_109 | Азиза | Manzil адрес | duration_check=false | 3/3 | 0:00:09 | 2599 ms |
| 2026-09-17 | 20260917_131521_646 | Лазокат | Menga tegmang, og‘riyapti. | duration_check=false | 3/3 | 0:00:10 | 1638 ms |
| 2026-09-17 | 20260917_134724_751 | Лазокат | Pasportim shu yerda. | duration_check=false | 3/3 | 0:00:11 | 2242 ms |
| 2026-09-17 | 20260917_140232_814 | Лазокат | Tutun bor. Есть дым. | duration_check=false | 3/3 | 0:00:14 | 3870 ms |
| 2026-09-18 | 20260918_114658_198 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-18 | 20260918_155544_745 | Адолат | Kutib turing. Подождите. | duration_check=false | 3/3 | 0:00:08 | 2917 ms |
| 2026-09-18 | 20260918_161242_809 | Фазилят | Qayerga imzo qo'yaman? Где мне подписать? | duration_check=false | 3/3 | 0:00:11 | 4056 ms |
| 2026-09-19 | 20260919_100951_77 | unknown |  | нет START; нет STOP; START_ACK 0/3; STOP_SAVE ok 0/3 | 0/3 | 0:00:00 |  |
| 2026-09-19 | 20260919_105708_201 | Лазокат | Kartangizni bering. Дайте вашу карту. | duration_check=false | 3/3 | 0:00:13 | 3882 ms |
| 2026-09-19 | 20260919_110150_211 | Лазокат | Qancha to'lov to'layman? Сколько мне заплатить? | duration_check=false | 3/3 | 0:00:13 | 3039 ms |
| 2026-09-19 | 20260919_123609_525 | Шахзода_1 | Avtobus kechikdi. Автобус опоздал. | duration_check=false | 3/3 | 0:00:11 | 1829 ms |
| 2026-09-19 | 20260919_124407_559 | Шахзода_1 | Yana biror narsa kerakmi? Ещё что-нибудь нужно? | duration_check=false | 3/3 | 0:00:11 | 3222 ms |
| 2026-09-19 | 20260919_130217_635 | Азиза | Jizzax Джизак | duration_check=false | 3/3 | 0:00:11 | 1916 ms |
| 2026-09-19 | 20260919_142139_851 | Парогат | Bu avtobus qayerga boradi? Куда идёт этот автобус? | duration_check=false | 3/3 | 0:00:05 | 3107 ms |
| ... | ... | ... | ... | еще 29 строк | ... | ... | ... |

## События по типам

| Event | Количество |
|---|---:|
| START_ACK | 49 992 |
| STOP_SAVE | 49 988 |
| START_PENDING | 16 707 |
| START | 16 664 |
| STOP | 16 663 |
| SESSION_CHECK | 16 663 |
| LOG_SAVED | 16 663 |
| CAMERA_LAYOUT | 10 409 |
| START_FAILED | 176 |
| EMERGENCY_STOP | 46 |

## Наблюдения по работе системы

- Нормальный цикл успешной записи выглядит так: `START_PENDING` -> `CAMERA_LAYOUT` (в новых логах) -> `START` -> 3 x `START_ACK` -> `STOP` -> 3 x `STOP_SAVE` -> `SESSION_CHECK` -> `LOG_SAVED`.
- В успешных сессиях система ожидает 3 телефона и обычно получает 3 сохраненных файла.
- Основная неисправность: телефоны периодически не отвечают на статус-запросы (`timed out`). При `connected 0/3 phones` запись блокируется до старта; при `EMERGENCY_STOP` сессия уже была начата и остановлена аварийно.
- Дни 2026-09-02 и 2026-09-07 содержат только по одному `START_FAILED`, без успешной съемки. Дни 2026-09-03, 2026-09-05 и 2026-09-11 короткие по объему относительно остальных.
- С 2026-09-09 в логах появился `CAMERA_LAYOUT`, а с 2026-09-15 в `STOP_SAVE` появился `actual_fps`; это похоже на расширение логирования без смены `app_version` (`1.1.0`).

## Рекомендации

1. Перед началом съемочного дня проверять, что все 3 телефона отвечают по своим URL и находятся в одной сети.
2. Отдельно посмотреть стабильность `device_1`, `device_2`, `device_3`: все три встречаются в таймаутах, но частота разная указана в разделе проблем.
3. Для аварийных остановок 2026-08-26 - 2026-08-28 стоит проверить, были ли пересняты соответствующие слова; в отчете перечислены первые проблемные сессии.
4. Если нужен стопроцентный контроль датасета, следующим шагом лучше сверить эти логи с фактическим наличием `.mp4` файлов на диске.
