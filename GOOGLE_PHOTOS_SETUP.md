# Google Photos Integration Setup Guide

This guide will help you set up Google Photos integration with BingHome to display a rotating slideshow of your photos on the home screen.

## Prerequisites

- Active Google account with photos in Google Photos
- Access to Google Cloud Console
- BingHome running on your Raspberry Pi

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Name it "BingHome" or similar
4. Click **Create**

## Step 2: Enable Google Photos Library API

1. In the Cloud Console, go to **APIs & Services** → **Library**
2. Search for "Photos Library API"
3. Click on it and press **Enable**

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** user type
3. Click **Create**
4. Fill in the required information:
   - App name: `BingHome`
   - User support email: Your email
   - Developer contact: Your email
5. Click **Save and Continue**
6. On "Scopes" page, click **Add or Remove Scopes**
7. Search for "photoslibrary" and select:
   - `.../auth/photoslibrary.readonly` (View your Google Photos library)
8. Click **Update** → **Save and Continue**
9. Add your email as a test user
10. Click **Save and Continue** → **Back to Dashboard**

## Step 4: Create OAuth Credentials

### ⚠️ Important: Google requires a domain name (not an IP address)

Choose ONE of these options:

**Option A: Use ngrok (⭐ EASIEST - Recommended)**
```
https://YOUR-NGROK-URL.ngrok-free.app/api/google_photos/callback
```
- ✅ Works immediately - no DNS setup needed
- ✅ Proper HTTPS that Google loves
- ✅ Free tier available
- 📖 **See [NGROK_SETUP.md](NGROK_SETUP.md) for step-by-step guide**
- 🚀 **Run: `./setup_ngrok.sh` to get started**

**Option B: Use .local hostname (Works on local network only)**
```
http://bing.local:5000/api/google_photos/callback
```
- May not work on all devices/networks
- No HTTPS (less secure)

**Option C: Use localhost (Only if accessing from the Pi itself)**
```
http://localhost:5000/api/google_photos/callback
```

**Option D: Set up a custom domain (Most permanent)**
- Register a domain (e.g., myhome.duckdns.org) using a free DNS service
- Point it to your Pi's IP address
- Use: `http://myhome.duckdns.org:5000/api/google_photos/callback`

### Now create the credentials:

1. Go to **APIs & Services** → **Credentials**
2. Click **+ Create Credentials** → **OAuth client ID**
3. Select **Web application**
4. Name it "BingHome Client"
5. Under **Authorized redirect URIs**, click **+ Add URI** and enter your chosen URL from above
6. Click **Create**
7. **Important**: Copy the **Client ID** and **Client Secret** that appear

## Step 5: Configure BingHome

1. SSH into your Raspberry Pi or open terminal

2. **Check your hostname** (important for .local option):
   ```bash
   hostname
   ```
   This will show your Pi's hostname (default is usually `raspberrypi`)

3. Edit the `.env` file:
   ```bash
   cd /home/rcook01/binghome
   nano .env
   ```

4. Add your Google credentials:
   ```bash
   GOOGLE_CLIENT_ID=your_client_id_here
   GOOGLE_CLIENT_SECRET=your_client_secret_here
   ```

5. Save the file (Ctrl+X, then Y, then Enter)

6. Restart BingHome:
   ```bash
   sudo systemctl restart binghome
   ```

## Step 6: Connect Google Photos in BingHome

1. Open BingHome in your browser using the SAME URL format you used in Google Console:
   - If you used `.local`: `http://raspberrypi.local:5000` (or your hostname)
   - If you used `localhost`: `http://localhost:5000`
   - If you used a domain: `http://yourdomain.com:5000`
   
   ⚠️ **Important**: The URL must match what you configured in Google Cloud Console!

2. Click the **Settings** icon (⚙️) in the top right
3. Scroll to the **📸 Google Photos Integration** section
4. Click **Sign in to Google Photos**
5. A popup window will open with Google's authorization screen
6. Sign in with your Google account
7. Click **Allow** to grant BingHome access to your photos
8. The popup will close automatically when complete

## Step 7: Select Album for Slideshow

1. Once connected, the settings page will show "✅ Connected"
2. A dropdown menu will appear with all your albums
3. Select the album you want to display on the home screen
4. Set the **Slideshow Interval** (seconds between photos) - default is 10 seconds
5. Click **Save Settings** at the bottom

## Step 8: Enjoy Your Photos!

1. Return to the home screen (using your configured URL)
2. The Google Photos widget (top-left) will now display rotating photos from your selected album
3. Photos will fade in and out automatically
4. Click on the photo widget to open Google Photos in a new window

## Troubleshooting

### "Invalid Redirect" error from Google
- Google doesn't allow IP addresses (like `192.168.1.100`) in redirect URIs
- You must use a hostname:
  - `.local` hostname: `http://raspberrypi.local:5000/api/google_photos/callback`
  - Domain name: `http://yourdomain.com:5000/api/google_photos/callback`
  - Localhost (only for local access): `http://localhost:5000/api/google_photos/callback`
- Make sure the redirect URI in Google Console matches EXACTLY
- Access BingHome using the same URL format (hostname, not IP)

### Can't access via .local hostname
- Check your hostname: `hostname`
- Try from different devices - some networks block mDNS
- Windows users may need to install Bonjour Print Services
- Alternative: Set up a free domain at duckdns.org

### "Not connected" status
- Make sure you've set up the OAuth credentials correctly
- Check that `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are in your `.env` file
- Restart the BingHome service: `sudo systemctl restart binghome`
- Verify you're accessing BingHome with the correct URL (not IP address)

### "No albums found"
- Make sure you've created at least one album in Google Photos
- Try clicking the **Refresh Albums** button
- Check that the Photos Library API is enabled in Google Cloud Console

### Authorization popup doesn't open
- Check your browser's popup blocker settings
- Try using a different browser
- Make sure the redirect URI in Google Cloud Console matches exactly

### Photos not displaying
- Verify an album is selected in settings
- Check that the album has photos (not videos)
- Look for errors in the system logs: `sudo journalctl -u binghome -f`

### Token expired errors
- Sign out and sign back in through the settings page
- This will refresh your access token

## Managing Your Albums

You can change which album is displayed at any time:
1. Go to **Settings** → **Google Photos Integration**
2. Select a different album from the dropdown
3. Click **Save Settings**
4. The slideshow will automatically update with photos from the new album

## Disconnecting Google Photos

To remove Google Photos access:
1. Go to **Settings** → **Google Photos Integration**
2. Click **Disconnect**
3. Confirm the action
4. Your photos will no longer be displayed, and BingHome will show the default icon

## Privacy & Security

- BingHome only requests **read-only** access to your photos
- Access tokens are stored locally on your Raspberry Pi in `settings.json`
- No photos are uploaded or stored by BingHome
- You can revoke access at any time via [Google Account Settings](https://myaccount.google.com/permissions)

## Need Help?

If you encounter issues:
1. Check the logs: `sudo journalctl -u binghome -n 100`
2. Verify your credentials in `.env`
3. Ensure your Pi has internet connectivity
4. Open an issue on GitHub: https://github.com/oodog/binghome/issues

---

Enjoy your personal photo slideshow on BingHome! 📸
