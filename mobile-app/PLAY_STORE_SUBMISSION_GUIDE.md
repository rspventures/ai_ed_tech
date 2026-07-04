# Play Store Submission Guide — AI Tutor

## Before You Start (One-Time Setup)

### 1. Update Production API URL
Open `app.json` and replace the placeholder with your real backend URL:
```json
"extra": {
  "apiBaseUrl": "https://api.your-actual-domain.com/api/v1"
}
```

### 2. Create an Expo Account
```bash
# Install EAS CLI globally
npm install -g eas-cli

# Login (or create account at expo.dev)
eas login
```

### 3. Link Project to Expo
```bash
cd mobile-app
eas init
```
This generates a `projectId` — paste it into `app.json` under `extra.eas.projectId`.

---

## Building for Play Store

### Step 1 — Install dependencies
```bash
npm install
```

### Step 2 — Build the AAB (Android App Bundle)
```bash
eas build --platform android --profile production
```
- EAS handles keystore generation automatically on first build
- **Save the keystore** — you cannot update your app without it
- Build runs in the cloud, takes ~10-15 minutes
- Download the `.aab` file from the Expo dashboard when done

### Step 3 — (Optional) Test locally first
```bash
# Build a debug APK to test on a real device
eas build --platform android --profile preview
```

---

## Google Play Console Setup

### 1. Create Developer Account
- Go to [play.google.com/console](https://play.google.com/console)
- Pay the one-time $25 registration fee

### 2. Create New App
- Click **Create app**
- App name: `AI Tutor`
- Default language: `English`
- App type: `App`
- Free / Paid: choose accordingly

### 3. Required Store Listing Assets

| Asset | Size | Notes |
|---|---|---|
| App icon | 512 × 512 px PNG | No transparency, no rounded corners (Play adds them) |
| Feature graphic | 1024 × 500 px JPG/PNG | Shown at top of store listing |
| Screenshots (phone) | Min 2, max 8 | At least 1080 × 1920 px recommended |
| Short description | Max 80 chars | One-line pitch |
| Full description | Max 4000 chars | Describe all features |

### 4. Content Rating
- Complete the content rating questionnaire
- Expected rating: **Everyone** (educational app)

### 5. Privacy Policy (REQUIRED)
You must host a privacy policy before submitting. It must cover:
- What data you collect (email, name, learning progress)
- How it is stored and used
- How users can request deletion

Host it at a public URL (e.g., GitHub Pages, Notion, your website) and paste the URL in Play Console under **Store listing → Privacy policy**.

### 6. Data Safety Section
In Play Console → **Data safety**, declare:
- Email address collected (required for account)
- Name collected (required for account)
- App activity (learning progress) — stored, not shared with third parties
- No sensitive data (no location, no payment info, no health data)

---

## Uploading and Publishing

### Option A — Manual Upload
1. In Play Console, go to **Production → Releases → Create release**
2. Upload the `.aab` file downloaded from Expo
3. Add release notes (e.g., "Initial release")
4. Click **Review release** → **Start rollout**

### Option B — Automated via EAS Submit
```bash
# First, create a Google Play Service Account key:
# Play Console → Setup → API access → Create service account
# Download the JSON key and save as google-play-service-account.json in mobile-app/

eas submit --platform android --profile production
```

---

## Incrementing Versions for Updates

Every new Play Store upload requires a higher `versionCode`. Update `app.json`:
```json
"version": "1.0.1",         // User-visible version string
"android": {
  "versionCode": 2           // Must increase by at least 1 each release
}
```
Then rebuild: `eas build --platform android --profile production`

---

## Checklist Before Each Submission

- [ ] `apiBaseUrl` in `app.json` points to production server
- [ ] `android.versionCode` incremented from previous release
- [ ] `version` string updated
- [ ] App tested on a real Android device (not just emulator)
- [ ] Voice screen tested with real token (requires live backend)
- [ ] Privacy policy URL is live and accessible
- [ ] All screenshots taken from latest build
- [ ] No debug/test accounts hardcoded anywhere

---

## Track Strategy (Recommended Rollout)

1. **Internal testing** → share with your team (up to 100 testers)
2. **Closed testing (Alpha)** → small group of real users
3. **Open testing (Beta)** → broader audience
4. **Production** → full public release

Start at Internal, verify everything works, then promote through the tracks.
