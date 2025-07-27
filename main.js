const LIVE_STREAM = 'https://viamotionhsi.netplus.ch/live/eds/bbc3cbbc/browser-HLS8/bbc3cbbc.m3u8';
const FALLBACK_VIDEO = 'https://files.catbox.moe/hem4g0.mp4';

function isNightTimeUK() {
  const now = new Date();
  const ukTime = new Date(now.toLocaleString("en-US", {timeZone: "Europe/London"}));
  const currentHour = ukTime.getHours();
  return currentHour >= 19 || currentHour < 7;
}

async function handler(request) {
  const url = new URL(request.url);
  
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
  
  if (request.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }
  
  const modeOverride = url.searchParams.get('mode');
  const nightMode = modeOverride === 'night' ? true : (modeOverride === 'day' ? false : isNightTimeUK());
  
  if (url.pathname === '/' || url.pathname === '') {
    const now = new Date();
    const ukTime = new Date(now.toLocaleString("en-US", {timeZone: "Europe/London"}));
    
    const html = `<!DOCTYPE html>
<html>
<head>
    <title>CBBC Stream</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest/dist/hls.min.js"></script>
</head>
<body style="font-family: Arial, sans-serif; margin: 40px;">
    <h1>🎬 CBBC Stream</h1>
    <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
        <p><strong>🕐 UK Time:</strong> ${ukTime.toLocaleString()}</p>
        <p><strong>📺 Mode:</strong> ${nightMode ? '🌙 Night (Video Loop)' : '☀️ Day (Live Stream)'}</p>
        <p><strong>🔗 Stream URL:</strong> <code>${url.origin}/stream.m3u8</code></p>
    </div>
    
    <video id="video" controls width="800" height="450" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"></video>
    
    <div style="margin-top: 20px;">
        <a href="/?mode=day" style="background: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-right: 10px;">☀️ Force Day</a>
        <a href="/?mode=night" style="background: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🌙 Force Night</a>
    </div>
    
    <script>
        const video = document.getElementById('video');
        const streamUrl = '/stream.m3u8' + window.location.search;
        
        console.log('Loading stream:', streamUrl);
        
        if (Hls.isSupported()) {
            const hls = new Hls({
                debug: false,
                enableWorker: false
            });
            
            hls.loadSource(streamUrl);
            hls.attachMedia(video);
            
            hls.on(Hls.Events.MANIFEST_PARSED, () => {
                console.log('✅ Stream loaded successfully');
                video.play().catch(e => {
                    console.log('Autoplay blocked, user interaction required');
                });
            });
            
            hls.on(Hls.Events.ERROR, (event, data) => {
                console.error('❌ HLS Error:', data);
                if (data.fatal) {
                    document.body.innerHTML += '<div style="color: red; margin-top: 20px;">❌ Stream error occurred. Try refreshing the page.</div>';
                }
            });
        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
            video.src = streamUrl;
            video.addEventListener('canplay', () => {
                video.play().catch(e => console.log('Autoplay blocked'));
            });
        } else {
            document.body.innerHTML += '<div style="color: red;">❌ Your browser does not support HLS streaming.</div>';
        }
    </script>
</body>
</html>`;
    
    return new Response(html, {
      headers: { ...corsHeaders, 'Content-Type': 'text/html' }
    });
  }
  
  if (url.pathname === '/stream.m3u8') {
    if (nightMode) {
      // Playlist per loop video notturno
      const playlist = `#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:3600
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:3600.0,
${FALLBACK_VIDEO}
#EXTINF:3600.0,
${FALLBACK_VIDEO}
#EXTINF:3600.0,
${FALLBACK_VIDEO}
#EXTINF:3600.0,
${FALLBACK_VIDEO}
#EXTINF:3600.0,
${FALLBACK_VIDEO}`;
      
      return new Response(playlist, {
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/vnd.apple.mpegurl',
          'Cache-Control': 'no-cache'
        }
      });
    } else {
      // Proxy stream live
      try {
        console.log('Fetching live stream...');
        const response = await fetch(LIVE_STREAM, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
          }
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        
        const content = await response.text();
        console.log('Live stream fetched successfully');
        
        return new Response(content, {
          headers: {
            ...corsHeaders,
            'Content-Type': 'application/vnd.apple.mpegurl',
            'Cache-Control': 'no-cache'
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
  
  return new Response('Not Found', { status: 404, headers: corsHeaders });
}

Deno.serve(handler);
