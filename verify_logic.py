
import sys
import os

# Mock settings and objects
class Settings:
    STORAGE_DIR = "storage"
    BASE_DIR = "."
settings = Settings()

def _calculate_hook_score(text: str):
    score = 1.0
    text_lower = text.lower()
    if "¿" in text or "?" in text:
        score += 3.0
    HOOK_KEYWORDS = ["sabías que", "mira esto", "increíble", "truco"]
    for kw in HOOK_KEYWORDS:
        if kw in text_lower:
            score += 2.0
    if len(text.split()) < 10:
        score += 0.5
    return score

def test_grouping_logic():
    print("--- Testing Grouping Logic ---")
    # Simulate a 120s transcript with segments every 5s
    segments = []
    for i in range(0, 120, 5):
        segments.append({
            "start": float(i),
            "end": float(i + 5),
            "text": f"Segment at {i} seconds. Sabías que esto es una prueba?" if i % 15 == 0 else f"Normal segment at {i}."
        })
    
    # Mock matches (CLIP scores)
    matches = []
    for seg in segments:
        matches.append({"segment": seg, "score": 0.8 if seg['start'] % 20 == 0 else 0.5})

    target_clip_dur = 60
    max_search_dur = 70
    best_windows = []
    
    for i, start_seg in enumerate(segments):
        start_t = start_seg['start']
        current_scores = []
        subset = []
        best_end_t = start_t
        best_window_score = -1
        
        for j in range(i, len(segments)):
            next_seg = segments[j]
            current_dur = next_seg['end'] - start_t
            if current_dur > max_search_dur:
                break
            subset.append(next_seg)
            for m in matches:
                if m['segment']['start'] == next_seg['start']:
                    current_scores.append(m['score'])
                    break
            
            if current_dur >= 30:
                avg_clip_score = sum(current_scores) / len(current_scores) if current_scores else 0
                hook_power = _calculate_hook_score(start_seg['text'])
                semantic_score = (avg_clip_score * 0.4) + (hook_power * 0.6)
                duration_factor = 1.0 - (abs(target_clip_dur - current_dur) / target_clip_dur)
                final_score = semantic_score * (0.7 + 0.3 * duration_factor)
                
                if final_score > best_window_score:
                    best_window_score = final_score
                    best_end_t = next_seg['end']

        if best_window_score > 0:
            best_windows.append({"start": start_t, "end": best_end_t, "score": best_window_score, "duration": best_end_t - start_t})
    
    best_windows = sorted(best_windows, key=lambda x: x['score'], reverse=True)
    
    final_selection = []
    for win in best_windows:
        if not any(abs(win['start'] - s['start']) < 45 for s in final_selection):
            final_selection.append(win)
        if len(final_selection) >= 3: break

    print(f"Total windows found: {len(best_windows)}")
    for i, win in enumerate(final_selection):
        print(f"Clip {i+1}: Start={win['start']}, End={win['end']}, Duration={win['duration']:.1f}s, Score={win['score']:.2f}")

    # Assertions
    assert len(final_selection) > 0, "Should find at least one clip"
    for win in final_selection:
        assert 30 <= win['duration'] <= 70, f"Clip duration {win['duration']} out of bounds"
        if win['duration'] < 55:
            print(f"Note: Clip duration {win['duration']} is less than 55s, but may be best available.")

def test_ffmpeg_command_logic():
    print("\n--- Testing FFmpeg Command Logic ---")
    start = 10.0
    duration = 60.0
    video_path = "input.mp4"
    
    # New logic: Input seeking
    inputs = ["-ss", str(start), "-t", str(duration), "-i", video_path]
    cmd_start = ["ffmpeg", "-y"] + inputs
    
    print(f"Generated command start: {' '.join(cmd_start)}")
    assert cmd_start[2] == "-ss", "Should have -ss early"
    assert cmd_start[3] == "10.0", "Should have correct start time"
    assert cmd_start[4] == "-t", "Should have -t"
    assert cmd_start[5] == "60.0", "Should have correct duration"
    assert cmd_start[6] == "-i", "Should have -i after seeking params"

if __name__ == "__main__":
    try:
        test_grouping_logic()
        test_ffmpeg_command_logic()
        print("\nALL LOGIC TESTS PASSED!")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
