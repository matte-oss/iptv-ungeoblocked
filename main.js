// Versione debug semplificata per Deno Deploy
const LIVE_STREAM = 'https://viamotionhsi.netplus.ch/live/eds/bbc3cbbc/browser-HLS8/bbc3cbbc.m3u8';
const FALLBACK_VIDEO = 'https://files.catbox.moe/hem4g0.mp4';

async function handler(request) {
  const url = new URL(request.url);
  
  console.log(`Request: ${request.method} ${url.pathname}`);
  
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
  
  if (request.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }
  
  // Determina modalità
  const now = new Date();
  const ukTime = new Date(now.toLocaleString("en-US", {timeZone: "Europe/London"}));
  const currentHour = ukTime.getHours();
  const modeOverride = url.searchParams.get('mode');
  
  let nightMode;
  if (modeOverride === 'night') {
    nightMode = true;
  } else if (modeOverride === 'day') {
    nightMode = false;
  } else {
    nightMode = currentHour >= 19 || currentHour < 7;
  }
  
  console.log(`UK Hour: ${currentHour}, Night Mode: ${nightMode}`);
  
  // Pagina principale con debug
  if (url.pathname === '/' || url.pathname === '') {
    const html = `<!DOCTYPE html>
<html>
<head>
    <title>CBBC Stream Debug</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@1.4.10/dist/hls.min.js"></script>
</head>
<body style="font-family: Arial, sans-serif; margin: 20px;">
    <h1>🎬 CBBC Stream - Debug Mode</h1>
    
    <div style="background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <h3>📊 Debug Info:</h3>
        <p><strong>🕐 Server UK Time:</strong> ${ukTime.toLocaleString()}</p>
        <p><strong>⏰ Current Hour:</strong> ${currentHour}</p>
        <p><strong>🌙 Night Mode:</strong> ${nightMode ? 'YES (19:00-07:00)' : 'NO (07:00-19:00)'}</p>
        <p><strong>🎯 Active Source:</strong> ${nightMode ? 'Fallback Video' : 'Live Stream'}</p>
        <p><strong>🔗 Stream URL:</strong> <code>${url.origin}/stream.m3u8</code></p>
    </div>
    
    <div style="margin: 20px 0;">
        <h3>🧪 Test Modes:</h3>
        <a href="/?mode=day" style="background: #4CAF50; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; margin-right: 10px;">☀️ Force Day Mode</a>
        <a href="/?mode=night" style="background: #2196F3; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px;">🌙 Force Night Mode</a>
    </div>
    
    <div style="margin: 20px 0;">
        <h3>📺 Video Player:</h3>
        <video id="video" controls width="640" height="360" style="border: 1px solid #ccc;"></video>
    </div>
    
    <div id="logs" style="background: #000; color: #0f0; padding: 10px; border-radius: 4px; font-family: monospace; height: 200px; overflow-y: scroll;">
        <div>🚀 Initializing player...</div>
    </div>
    
    <script>
        const video = document.getElementById('video');
        const logs = document.getElementById('logs');
        const streamUrl = '/stream.m3u8' + window.location.search;
        
        function addLog(message) {
            const div = document.createElement('div');
            div.textContent = new Date().toLocaleTimeString() + ' - ' + message;
            logs.appendChild(div);
            logs.scrollTop = logs.scrollHeight;
            console.log(message);
        }
        
        addLog('🔗 Stream URL: ' + streamUrl);
        
        // Test diretto del stream
        fetch(streamUrl)
            .then(response => {
                addLog('📡 Stream response status: ' + response.status);
                return response.text();
            })
            .then(content => {
                addLog('📄 Stream content preview: ' + content.substring(0, 100) + '...');
            })
            .catch(error => {
                addLog('❌ Stream fetch error: ' + error.message);
            });
        
        if (Hls.isSupported()) {
            addLog('✅ HLS.js is supported');
            
            const hls = new Hls({
                debug: true,
                enableWorker: false
            });
            
            hls.on(Hls.Events.MEDIA_ATTACHED, () => {
                addLog('📱 Media attached to HLS');
            });
            
            hls.on(Hls.Events.MANIFEST_PARSING, () => {
                addLog('📋 Parsing manifest...');
            });
            
            hls.on(Hls.Events.MANIFEST_PARSED, (event, data) => {
                addLog('✅ Manifest parsed successfully');
                addLog('📊 Levels found: ' + data.levels.length);
                video.play().catch(e => {
                    addLog('⚠️ Autoplay failed: ' + e.message);
                });
            });
            
            hls.on(Hls.Events.ERROR, (event, data) => {
                addLog('❌ HLS Error: ' + data.type + ' - ' + data.details);
                if (data.fatal) {
                    addLog('💀 Fatal error occurred');
                }
            });
            
            hls.loadSource(streamUrl);
            hls.attachMedia(video);
            
        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
            addLog('🍎 Using native HLS support (Safari)');
            video.src = streamUrl;
            video.addEventListener('canplay', () => {
                addLog('▶️ Video can play');
                video.play().catch(e => addLog('⚠️ Autoplay failed: ' + e.message));
            });
            video.addEventListener('error', (e) => {
                addLog('❌ Video error: ' + e.message);
            });
        } else {
            addLog('❌ HLS not supported in this browser');
        }
        
        // Info aggiuntive
        addLog('🌐 User Agent: ' + navigator.userAgent);
        addLog('📍 Current URL: ' + window.location.href);
    </script>
</body>
</html>`;
    
    return new Response(html, {
      headers: { ...corsHeaders, 'Content-Type': 'text/html; charset=utf-8' }
    });
  }
  
  // Stream endpoint
  if (url.pathname === '/stream.m3u8') {
    console.log(`Serving stream - Night mode: ${nightMode}`);
    
    if (nightMode) {
      // Playlist per video loop
      const playlist = `#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:3600
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:3600.0,
${FALLBACK_VIDEO}
#EXTINF:3600.0,
${FALLBACK_VIDEO}
#EXTINF:3600.0,
${FALLBACK_VIDEO}`;
      
      console.log('Returning night mode playlist');
      
      return new Response(playlist, {
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/vnd.apple.mpegurl',
          'Cache-Control': 'no-cache, no-store, must-revalidate'
        }
      });
    } else {
      // Proxy stream live
      try {
        console.log('Fetching live stream...');
        
        const response = await fetch(LIVE_STREAM, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
          }
        });
        
        console.log(`Live stream response: ${response.status}`);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const content = await response.text();
        console.log(`Live stream content length: ${content.length}`);
        
        return new Response(content, {
          headers: {
            ...corsHeaders,
            'Content-Type': 'application/vnd.apple.mpegurl',
            'Cache-Control': 'no-cache, no-store, must-revalidate'
          }
        });
      } catch (error) {
        console.error('Live stream error:', error);
        
        // Fallback al video
        const fallbackPlaylist = `#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:3600
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:3600.0,
${FALLBACK_VIDEO}
#EXT-X-ENDLIST`;
        
        return new Response(fallbackPlaylist, {
          headers: {
            ...corsHeaders,
            'Content-Type': 'application/vnd.apple.mpegurl'
          }
        });
      }
    }
  }
  
  return new Response('Not Found', { 
    status: 404, 
    headers: { ...corsHeaders, 'Content-Type': 'text/plain' }
  });
}

Deno.serve(handler);
