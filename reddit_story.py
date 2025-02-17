import praw
import random
import re
import subprocess
import os
from gtts import gTTS
from mutagen.mp3 import MP3


reddit = praw.Reddit(
    client_id="wy9A8yMW-r0EAmmuPv4-vg",
    client_secret="nWr7v2LX3SZhHBdUnh8SKEMquch0cQ",
    user_agent="story_finder/1.0"
)

LOCAL_VIDEO_FILE = "iphone_gameplay.mp4"  



def cleanup_files(*files):
    """
    Remove the specified files if they exist.
    """
    for file_path in files:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Temporary file '{file_path}' removed.")
        else:
            print(f"File '{file_path}' not found or already removed.")

def fetch_short_story():
    """
    Fetch a random short story (400-600 words) from r/shortstories.
    Returns tuple (title, text) or None if no valid story found.
    """
    try:
        subreddit = reddit.subreddit("shortstories")
        posts = [post for post in subreddit.hot(limit=20) if post.selftext]

        # Filter for stories with 400-600 words
        stories = [(post.title, post.selftext)
                   for post in posts if 400 <= len(post.selftext.split()) <= 600]

        if stories:
            return random.choice(stories)
        else:
            return None
    except Exception as e:
        print(f"Error fetching story from Reddit: {e}")
        return None

def clean_filename(title):
    """
    Clean a title for use as a valid filename.
    """
    return re.sub(r'[\\/*?:"<>|]', "", title).replace(" ", "_")[:50]

def text_to_speech_gtts(text, filename):
    """
    Convert text to speech using gTTS and save as an MP3 file.
    """
    tts = gTTS(text=text, lang="en")
    tts.save(filename)
    print(f"Audio saved as {filename}")

def check_ffmpeg():
    """
    Ensure FFmpeg is installed before merging video/audio.
    """
    try:
        subprocess.run(["ffmpeg", "-version"],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("ERROR: FFmpeg is not installed or not on PATH.")
        exit(1)

def get_video_duration(video_file):
    """
    Use ffprobe to get video duration (in seconds).
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe error: {result.stderr}")
    return float(result.stdout.strip())

def get_audio_duration(audio_file):
    """
    Use mutagen to get MP3 file duration (in seconds).
    """
    audio = MP3(audio_file)
    return audio.info.length

def merge_subclip_ffmpeg(video_file, audio_file, start_time, duration, output_file):
    """
    Extract a subclip from 'video_file' starting at start_time for duration seconds,
    merge the audio_file track, and save as 'output_file'.
    """
    check_ffmpeg()
    cmd = [
        "ffmpeg",
        "-ss", str(start_time),      
        "-i", video_file,
        "-i", audio_file,
        "-t", str(duration),         
        "-c:v", "libx264",
        "-preset", "veryfast",       
        "-c:a", "aac",
        "-map", "0:v",
        "-map", "1:a",
        "-shortest",
        "-y",                        
        output_file
    ]
    subprocess.run(cmd, check=True)
    print(f"Final video saved as {output_file}")

# ---------------- Main Script Execution ----------------

def main():
    #  Fetch a random story
    story_data = fetch_short_story()
    if not story_data:
        print("No valid stories found (400-600 words). Exiting.")
        return

    title, story_text = story_data
    filename_base = clean_filename(title)
    audio_filename = f"{filename_base}.mp3"

    print(f"Fetched Story: {title}\n\n{story_text}")

    # Convert story to MP3
    text_to_speech_gtts(story_text, audio_filename)

    # Get durations
    if not os.path.exists(LOCAL_VIDEO_FILE):
        print(f"Local video file '{LOCAL_VIDEO_FILE}' does not exist.")
        cleanup_files(audio_filename)
        return

    video_duration = get_video_duration(LOCAL_VIDEO_FILE)
    narration_duration = get_audio_duration(audio_filename)

    if narration_duration >= video_duration:
        print("Narration is longer than the video; cannot subclip properly.")
        cleanup_files(audio_filename)
        return

    # Pick a random subclip start time
    start_time = random.uniform(0, video_duration - narration_duration)

    # Merge subclip with narration
    final_video_filename = filename_base + "_final.mp4"
    merge_subclip_ffmpeg(
        LOCAL_VIDEO_FILE, audio_filename,
        start_time, narration_duration,
        final_video_filename
    )

    cleanup_files(audio_filename)

    print("Done!")

if __name__ == "__main__":
    main()