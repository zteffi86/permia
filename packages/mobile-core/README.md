# Permía Mobile Core (KMM)

Kotlin Multiplatform Mobile shared business logic for iOS and Android.

## What's Shared

- **Networking:** Ktor client with OpenAPI-aligned DTOs
- **Offline Queue:** SQLDelight-backed evidence queue (exactly-once semantics)
- **Cryptography:** SHA-256 hashing (MessageDigest on Android, CommonCrypto on iOS)
- **Models:** Evidence Record, Prompt, GPS, etc.
- **Retry Logic:** Exponential backoff for failed uploads

## What's Platform-Specific

- **UI:** Jetpack Compose (Android), SwiftUI (iOS)
- **Camera:** CameraX (Android), AVFoundation (iOS)
- **Push:** FCM (Android), APNs (iOS)

## Building

**Android:**
```bash
./gradlew :packages:mobile-core:assembleDebug
```

**iOS:**
```bash
./gradlew :packages:mobile-core:linkDebugFrameworkIosSimulatorArm64
```
