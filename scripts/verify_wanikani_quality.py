import json
import os
import glob

def verify_quality():
    files = sorted(glob.glob('resources/data/level_*.json'))
    report = []
    
    total_subjects = 0
    missing_meanings = 0
    missing_readings = 0
    missing_audio = 0
    missing_sentences = 0
    missing_images = 0 # Specifically for radicals with no characters
    
    for file_path in files:
        with open(file_path, 'r') as f:
            level_data = json.load(f)
            level = level_data['level']
            subjects = level_data['data']
            
            for s in subjects:
                total_subjects += 1
                obj_type = s['object']
                data = s['data']
                
                # Check meanings
                if not data.get('meanings'):
                    missing_meanings += 1
                
                # Check readings (Kanji and Vocab only)
                if obj_type in ['kanji', 'vocabulary', 'kana_vocabulary']:
                    if obj_type == 'kana_vocabulary':
                        # Kana vocab might not have "readings" array but the text itself is the reading
                        pass
                    elif not data.get('readings'):
                        missing_readings += 1
                
                # Check sentences (Vocab only)
                if obj_type == 'vocabulary':
                    if not data.get('context_sentences'):
                        missing_sentences += 1
                    
                    # Check audio
                    if not data.get('pronunciation_audios'):
                        missing_audio += 1
                
                # Check images for radicals
                if obj_type == 'radical':
                    if not data.get('characters') and not data.get('character_images'):
                        missing_images += 1

    summary = {
        "total_subjects": total_subjects,
        "missing_meanings": missing_meanings,
        "missing_readings": missing_readings,
        "missing_sentences": missing_sentences,
        "missing_audio": missing_audio,
        "missing_images": missing_images
    }
    
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    verify_quality()
