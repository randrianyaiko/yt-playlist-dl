import os
import re
import uuid
import tempfile
import zipfile
import streamlit as st
from yt_dlp import YoutubeDL

# Streamlit Page Setup
st.set_page_config(page_title="YouTube Playlist Downloader")
st.title("🎥 YouTube Playlist Downloader")

# Function to sanitize filenames
def sanitize(s: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", s)

# Main function to download and zip the playlist
def download_and_zip(playlist_url: str, status_callback=None, progress_callback=None) -> str:
    # Step 1: Extract playlist info
    with YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    playlist_title = sanitize(info.get('title', 'playlist'))

    # Step 2: Create a unique temp directory
    unique_id = str(uuid.uuid4())[:8]
    temp_dir = tempfile.mkdtemp(prefix=f"{playlist_title}_{unique_id}_")
    output_template = os.path.join(temp_dir, '%(playlist_index)03d - %(title)s.%(ext)s')

    skipped_videos = []
    total_videos = len(info.get('entries', []))
    progress = {'count': 0}

    # Hook for progress and status updates
    def hook(d):
        if d['status'] == 'downloading':
            if progress_callback and 'downloaded_bytes' in d and 'total_bytes' in d:
                total = d['total_bytes'] or d.get('total_bytes_estimate', 1)
                percent = d['downloaded_bytes'] / total
                progress_callback(percent)
        elif d['status'] == 'finished':
            progress['count'] += 1
            if status_callback:
                status_callback(f"✅ Downloaded {progress['count']} of {total_videos} videos...")
        elif d['status'] == 'error':
            skipped_videos.append(d.get('filename', 'Unknown video'))

    # Step 3: Configure yt-dlp options
    opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'ignoreerrors': True,
        'progress_hooks': [hook],
        'quiet': True,
        'noplaylist': False,
    }

    # Step 4: Download videos
    with YoutubeDL(opts) as ydl:
        ydl.download([playlist_url])

    # Step 5: Zip the downloaded files
    zip_filename = f"{unique_id}.zip"
    zip_path = os.path.join(temp_dir, zip_filename)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(temp_dir):
            for fname in files:
                full = os.path.join(root, fname)
                if full == zip_path:
                    continue  # avoid adding the zip itself
                rel = os.path.relpath(full, temp_dir)
                zf.write(full, rel)

    # Final warning if any videos were skipped
    if skipped_videos and status_callback:
        status_callback(f"⚠️ Skipped {len(skipped_videos)} video(s) due to copyright or download issues.")

    return zip_path

# === Streamlit UI ===
playlist_url = st.text_input("Enter YouTube Playlist URL")

if st.button("Download & Zip Playlist"):
    if not playlist_url:
        st.error("❌ Please enter a valid playlist URL.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_status(msg):
            status_text.text(msg)

        def update_progress(pct):
            progress_bar.progress(min(int(pct * 100), 100))

        with st.spinner("Downloading playlist..."):
            try:
                zip_file = download_and_zip(
                    playlist_url,
                    status_callback=update_status,
                    progress_callback=update_progress
                )
                st.success("✅ Download complete!")
                with open(zip_file, "rb") as f:
                    st.download_button(
                        label="📥 Download ZIP",
                        data=f,
                        file_name=os.path.basename(zip_file),
                        mime="application/zip"
                    )
            except Exception as e:
                st.error(f"❌ Error during download: {e}")
