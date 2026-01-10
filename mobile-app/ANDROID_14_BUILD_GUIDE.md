# Building for Android 14+ (API 34+)

When using **Expo Go** on Android 14+, you may encounter this error:
```
Permission Denial: registerScreenCaptureObserver requires android.permission.DETECT_SCREEN_CAPTURE
```

This happens because Expo Go doesn't have this new Android 14 permission. Here's how to fix it:

---

## Quick Fix: Use Android 13 Emulator

For development, use an Android 13 (API 33) emulator. See `ANDROID_SETUP.md` for instructions.

---

## Production Fix: Build Your Own App

### Option 1: Development Client (For Development)

Build a custom Expo app with the correct permissions:

```bash
# Install EAS CLI (one-time)
npm install -g eas-cli

# Login to Expo
eas login

# Configure your project
eas build:configure

# Build a development client for Android
eas build --profile development --platform android
```

This creates a custom `.apk` that includes all permissions from your `app.json`.

**After the build:**
1. Download the APK from the Expo dashboard
2. Install it on your emulator: `adb install your-app.apk`
3. Run `npx expo start --dev-client` instead of `npx expo start`

### Option 2: Production Build (For Release)

```bash
# Build a production APK (local testing)
eas build --platform android --profile preview

# Build for Play Store (AAB format)
eas build --platform android --profile production
```

---

## EAS Configuration

Add this to your `eas.json` (created by `eas build:configure`):

```json
{
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal",
      "android": {
        "buildType": "apk"
      }
    },
    "preview": {
      "android": {
        "buildType": "apk"
      }
    },
    "production": {}
  }
}
```

---

## Why This Works

| Approach | Permissions | Best For |
|----------|-------------|----------|
| Expo Go | Fixed, limited | Quick prototyping on Android 13 |
| Development Client | Custom from app.json | Development on any Android |
| Production Build | Full control | Release to users |

When you build your own app, the permissions in `app.json` are included in the Android Manifest, giving your app access to all required APIs.

---

## Current Status

This project is configured to request `DETECT_SCREEN_CAPTURE` in `app.json`:
```json
"android": {
  "permissions": [
    "android.permission.DETECT_SCREEN_CAPTURE"
  ]
}
```

This will work automatically once you build your own APK.
