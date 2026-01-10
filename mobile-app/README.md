# AI Tutor Mobile App

This is a **React Native (Expo)** project for the AI Tutor Platform.

## Prerequisites
1.  **Node.js**: You MUST install Node.js (LTS version) from [nodejs.org](https://nodejs.org/).
2.  **Android Emulator**: You need Android Studio installed and an emulator running (or a physical device).

## Setup Instructions
Since this project was generated manually, you need to install dependencies first.

1.  Open this folder in a terminal:
    ```bash
    cd mobile-app
    ```

2.  Install dependencies:
    ```bash
    npm install
    ```
    *Note: This will install Expo, React Native, and all libraries defined in `package.json`.*

3.  Start the Development Server:
    ```bash
    npm run android
    ```
    *This command (alias for `expo start --android`) will launch the app on your running emulator.*

## Project Structure
- `App.js`: Main entry point with Navigation logic.
- `src/api/client.ts`: Axios client configured for Android Emulator (`10.0.2.2`).
- `src/context/AuthContext.tsx`: Authentication state management.
- `src/screens/`: UI Screens (`LoginScreen`, `DashboardScreen`).
- `src/services/`: API service functions.
