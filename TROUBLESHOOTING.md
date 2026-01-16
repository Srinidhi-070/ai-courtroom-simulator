# 🔧 Troubleshooting Guide

## ⏱️ Timeout Error Fix

If you're getting **"Read timed out"** errors, follow these solutions:

### **Solution 1: Disable Ollama (Fastest Fix)**
1. Open `server.py`
2. Find line: `USE_OLLAMA = True`
3. Change to: `USE_OLLAMA = False`
4. Restart the server
5. App will use fast fallback responses instead

### **Solution 2: Install Ollama (For AI Responses)**
1. Download Ollama from: https://ollama.ai
2. Install and run Ollama
3. Open terminal/command prompt
4. Run: `ollama pull mistral`
5. Wait for download to complete
6. Restart the application

### **Solution 3: Increase Timeout**
1. Open `app.py`
2. Find: `timeout=30`
3. Change to: `timeout=60`
4. Save and restart

## 🚫 Common Errors

### **Backend Not Running**
- **Error**: "Cannot connect to backend"
- **Fix**: Run `START_HERE.bat` or `python server.py`

### **Port Already in Use**
- **Error**: "Address already in use"
- **Fix**: Close other instances or change port in code

### **Missing Modules**
- **Error**: "ModuleNotFoundError"
- **Fix**: Run `pip install -r requirements.txt`

## ✅ Quick Test

Run this to test if everything works:
```bash
# Test backend
curl http://127.0.0.1:8000/health

# Should return: {"status":"healthy",...}
```

## 💡 Performance Tips

1. **First response is slow** - Normal, AI loads model
2. **Subsequent responses faster** - Model stays in memory
3. **Fallback responses instant** - No AI needed
4. **Ollama optional** - App works without it

## 📞 Still Having Issues?

1. Check if both windows are running (Backend + Frontend)
2. Try restarting both servers
3. Check firewall settings
4. Disable antivirus temporarily
5. Use fallback mode (set `USE_OLLAMA = False`)
