# server/upload

UploadService: resumable/chunked HTTP video transfer from CameraNodes, independent of
the WebSocket control connection (which stays open for the next command while a phone
is still uploading footage from the previous one).

Supports checksum verification, progress reporting, parallel upload, automatic retry.
Retry/backoff numbers in `docs/failure_recovery.md`.
