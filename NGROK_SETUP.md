# Google Photos with ngrok - Quick Setup Guide

## Why ngrok?

✅ **Easiest solution** - No DNS, no domain names needed  
✅ **Works immediately** - Get a public HTTPS URL in seconds  
✅ **Google accepts it** - Proper HTTPS domain that OAuth loves  
✅ **Free tier available** - No credit card required  

## Quick Setup (5 minutes)

### Step 1: Run the Setup Script

```bash
cd /home/rcook01/binghome
./setup_ngrok.sh
```

The script will:
1. Install ngrok automatically
2. Ask for your ngrok authtoken (see step 2)
3. Start the tunnel and give you a URL

### Step 2: Get ngrok Authtoken

While the script is waiting:

1. Go to: https://dashboard.ngrok.com/signup
2. Sign up for FREE (just email, no credit card)
3. Go to: https://dashboard.ngrok.com/get-started/your-authtoken
4. Copy your authtoken
5. Paste it into the terminal when asked

### Step 3: Get Your ngrok URL

Once ngrok starts, you'll see something like:
```
Forwarding  https://a1b2-123-456-789-012.ngrok-free.app -> http://localhost:5000
```

**Copy that HTTPS URL** (e.g., `https://a1b2-123-456-789-012.ngrok-free.app`)

### Step 4: Update Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Edit your OAuth Client ID
3. Under **Authorized redirect URIs**, add:
   ```
   https://YOUR-NGROK-URL.ngrok-free.app/api/google_photos/callback
   ```
   (Replace with your actual ngrok URL)
4. Click **Save**

### Step 5: Access BingHome via ngrok

1. Open your ngrok URL in browser: `https://YOUR-NGROK-URL.ngrok-free.app`
2. Click the ngrok warning page button (first time only)
3. Go to Settings and sign in to Google Photos
4. It will work! 🎉

## Important Notes

### Keep ngrok Running
- ngrok must stay running for the URL to work
- If you stop it, you'll get a new URL next time
- Run it in a separate terminal or use `screen` / `tmux`

### Free Tier Limitations
- URL changes each time you restart (unless you pay for static subdomain)
- 40 connections/minute limit
- One online ngrok process at a time

### Make ngrok Permanent (Optional)

Run ngrok in the background with systemd:

```bash
sudo tee /etc/systemd/system/ngrok.service > /dev/null << 'EOF'
[Unit]
Description=ngrok tunnel
After=network.target

[Service]
Type=simple
User=rcook01
ExecStart=/usr/local/bin/ngrok http 5000 --log=/var/log/ngrok.log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ngrok
sudo systemctl start ngrok

# View your URL
sleep 3
curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*' | grep https | cut -d'"' -f4
```

## Alternative: Static Subdomain (Paid)

If you want a permanent URL like `https://mybinghome.ngrok.app`:

1. Upgrade to ngrok paid plan (~$8/month)
2. Reserve a subdomain in the dashboard
3. Start with: `ngrok http 5000 --subdomain=mybinghome`
4. Your URL never changes!

## Troubleshooting

### "ERR_NGROK_108"
- Your authtoken is invalid
- Get a new one from: https://dashboard.ngrok.com/get-started/your-authtoken
- Run: `ngrok config add-authtoken YOUR_NEW_TOKEN`

### "tunnel not found"
- ngrok is not running
- Start it with: `./setup_ngrok.sh` or `ngrok http 5000`

### OAuth redirect mismatch
- Make sure the URL in Google Console matches your ngrok URL EXACTLY
- Include `/api/google_photos/callback` at the end
- Use HTTPS (not HTTP)

### ngrok URL changed
- This happens when you restart ngrok on free tier
- Update the redirect URI in Google Console with the new URL
- Or upgrade to get a static subdomain

## Best Approach

**For Testing**: Use ngrok free tier (URL changes each restart)  
**For Permanent Use**: Either:
- Option A: Pay $8/month for static ngrok subdomain ⭐ Recommended
- Option B: Use free DNS service (DuckDNS) + port forwarding
- Option C: Keep updating Google Console each time ngrok restarts (annoying)

---

Need help? The setup script makes it easy - just run `./setup_ngrok.sh`!
