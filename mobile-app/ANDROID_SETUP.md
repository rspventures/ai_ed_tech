# Android Studio & Emulator Setup Guide

To run the mobile app, you need an **Android Emulator**. The best way to get this is by installing **Android Studio**.

## 1. Download Android Studio
1.  Go to the official website: [developer.android.com/studio](https://developer.android.com/studio)
2.  Click **Download Android Studio**.
3.  Accept the terms and download the installer (`.exe` for Windows).

## 2. Install
1.  Run the downloaded installer.
2.  **Important**: Ensure **"Android Virtual Device"** is checked during installation.
3.  Click Next > Next > Install > Finish.

## 3. First Run Wizard
1.  Open Android Studio.
2.  Select "Do not import settings" (if prompted).
3.  Follow the wizard.
4.  **License Agreement**: You MUST accept the licenses for all components (click on each item in the left list and select "Accept").
5.  Let it download the SDK components (this may take a while).

## 4. Create an Emulator
1.  On the Welcome Screen, click **More Actions** (three dots) > **Virtual Device Manager**.
    *   *If you are already inside a project, go to Tools > Device Manager.*
2.  Click **Create Device** (or the Plus icon).
3.  **Select Hardware**: Choose "Pixel 7" (or any Pixel device with the Play Store icon). Click Next.
4.  **System Image**:
    *   Click the **Download** icon next to the latest recommended release (e.g., "UpsideDownCake" or "Tiramisu").
    *   Wait for the download to finish.
    *   Select it and click Next.
5.  Click **Finish**.

## 5. Run the Emulator
1.  In the Device Manager, click the **Play Button (▶)** next to your new device.
2.  Wait for the phone to boot up on your screen.
3.  **Done!** You can now run the `start_android.cmd` script in the `mobile-app` folder.

---

## ⚠️ Troubleshooting: Android 14+ Permission Error

If you see this error:
```
Permission Denial: registerScreenCaptureObserver requires android.permission.DETECT_SCREEN_CAPTURE
```

**This is an Android 14+ restriction.** The Expo Go app doesn't have this permission.

### Fix: Create an Android 13 (API 33) Emulator

1.  Open **Android Studio** > **Device Manager**
2.  Click **Create Device**
3.  Select **Pixel 6** > Click Next
4.  **System Image**: Click the **x86 Images** tab
5.  Find **Tiramisu (API 33)** - Download it if needed
6.  Select it and click **Next** > **Finish**
7.  **Start this new emulator** instead of the Android 14/15 one

Then run `start_android.cmd` again. The app should work!
