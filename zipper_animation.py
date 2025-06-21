import streamlit as st 
import streamlit.components.v1 as components

def show_zipper_animation():
    zipper_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Zipper Animation</title>
        <style>
            html, body {
                margin: 0;
                padding: 0;
                width: 100%;
                height: 100%;
                overflow: hidden;
                font-family: Arial, sans-serif;
            }
            
            #zipper-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                z-index: 9999;
                background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            }
            
            .side-panel {
                position: absolute;
                top: 0;
                width: 50%;
                height: 100vh;
                background: rgba(0, 0, 0, 0.7);
                color: white;
                padding: 20px;
                box-sizing: border-box;
                overflow-y: auto;
                transition: transform 0.3s ease;
            }
            
            .side-panel.left {
                left: 0;
                transform: translateX(-100%);
            }
            
            .side-panel.right {
                right: 0;
                transform: translateX(100%);
            }
            
            #zipper-container {
                position: fixed;
                top: 0;
                left: 50%;
                transform: translateX(-50%);
                width: 60px;
                height: 100vh;
                z-index: 10000;
                cursor: pointer;
            }
            
            #zipper-track {
                position: absolute;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(to right, #555, #333, #555);
                border-left: 2px solid #777;
                border-right: 2px solid #777;
            }
            
            #zipper-handle {
                position: absolute;
                left: 50%;
                transform: translateX(-50%);
                top: 20px;
                width: 40px;
                height: 80px;
                background: #888;
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0,0,0,0.5);
                transition: top 0.3s ease;
            }
        </style>
    </head>
    <body>
        <div id="zipper-overlay">
            <div class="side-panel left">
                <h2>APIHub Features</h2>
                <h3>API Documentation</h3>
                <p>Detailed documentation for all available endpoints with interactive examples.</p>
                <h3>Authentication</h3>
                <p>Secure API key management and OAuth integration.</p>
                <h3>Usage Analytics</h3>
                <p>Monitor your API usage and performance metrics in real-time.</p>
            </div>
            
            <div class="side-panel right">
                <h2>Quick Start</h2>
                <ol>
                    <li>Get API Key - Register to receive your unique API key</li>
                    <li>Explore Endpoints - Try our interactive API explorer</li>
                    <li>Integrate - Use our SDKs or make direct HTTP requests</li>
                </ol>
            </div>
            
            <div id="zipper-container">
                <div id="zipper-track"></div>
                <div id="zipper-handle"></div>
            </div>
        </div>
        
        <script>
            const zipperHandle = document.getElementById('zipper-handle');
            const zipperOverlay = document.getElementById('zipper-overlay');
            const leftPanel = document.querySelector('.side-panel.left');
            const rightPanel = document.querySelector('.side-panel.right');
            let isDragging = false;
            let startY = 0;
            let startTop = 0;
            
            zipperHandle.addEventListener('mousedown', startDrag);
            zipperHandle.addEventListener('touchstart', startDrag);
            
            function startDrag(e) {
                isDragging = true;
                startY = e.clientY || e.touches[0].clientY;
                startTop = parseInt(zipperHandle.style.top) || 20;
                document.addEventListener('mousemove', drag);
                document.addEventListener('mouseup', endDrag);
                document.addEventListener('touchmove', drag);
                document.addEventListener('touchend', endDrag);
                e.preventDefault();
            }
            
            function drag(e) {
                if (!isDragging) return;
                const y = e.clientY || e.touches[0].clientY;
                const deltaY = y - startY;
                let newTop = startTop + deltaY;
                
                newTop = Math.max(20, Math.min(newTop, window.innerHeight - 100));
                zipperHandle.style.top = newTop + 'px';
                
                const progress = (newTop - 20) / (window.innerHeight - 120);
                
                leftPanel.style.transform = `translateX(${-100 + progress * 100}%)`;
                rightPanel.style.transform = `translateX(${100 - progress * 100}%)`;
                
                zipperOverlay.style.opacity = 1 - (progress * 1.2);
            }
            
            function endDrag() {
                isDragging = false;
                document.removeEventListener('mousemove', drag);
                document.removeEventListener('mouseup', endDrag);
                document.removeEventListener('touchmove', drag);
                document.removeEventListener('touchend', endDrag);
                
                const currentTop = parseInt(zipperHandle.style.top) || 20;
                const openThreshold = window.innerHeight * 0.7;
                
                if (currentTop > openThreshold) {
                    zipperHandle.style.top = (window.innerHeight - 80) + 'px';
                    leftPanel.style.transform = 'translateX(0)';
                    rightPanel.style.transform = 'translateX(0)';
                    zipperOverlay.style.opacity = '0';
                    
                    setTimeout(() => {
                        window.parent.postMessage({
                            type: 'zipper_opened',
                            value: true
                        }, '*');
                    }, 500);
                } else {
                    zipperHandle.style.top = '20px';
                    leftPanel.style.transform = 'translateX(-100%)';
                    rightPanel.style.transform = 'translateX(100%)';
                    zipperOverlay.style.opacity = '1';
                }
            }
        </script>
    </body>
    </html>
    """
    
    components.html(zipper_html, height=800, scrolling=False)

def hide_zipper_animation():
    st.markdown("""
    <style>
        iframe {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)