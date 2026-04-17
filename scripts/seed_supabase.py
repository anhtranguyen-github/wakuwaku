import json
import os
import glob
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

def seed_data():
    # Database connection parameters from environment
    dbname = os.getenv('POSTGRES_DB', 'postgres')
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    host = os.getenv('POSTGRES_HOST', 'db')
    port = os.getenv('POSTGRES_PORT', '5432')

    print(f"Connecting to database {dbname} on {host}:{port}...")
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        cur = conn.cursor()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return

    # 1. Create System User if not exists
    system_user_id = '00000000-0000-0000-0000-000000000000'
    cur.execute("""
        INSERT INTO users (id, username, email, level)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, (system_user_id, 'system', 'system@hanachan.local', 60))
    
    # 2. Clear existing subjects if requested (optional, we use ON CONFLICT)
    # cur.execute("DELETE FROM subjects WHERE user_id = %s", (system_user_id,))

    # 3. Process level files
    files = sorted(glob.glob('resources/data/level_*.json'))
    
    total_inserted = 0
    for file_path in files:
        print(f"Processing {file_path}...")
        with open(file_path, 'r') as f:
            level_data = json.load(f)
            subjects = level_data['data']
            
            batch = []
            for s in subjects:
                d = s['data']
                
                # Map fields
                subject_id = s['id']
                obj_type = s['object']
                slug = d.get('slug', '')
                level = d.get('level', 0)
                meaning_mnemonic = d.get('meaning_mnemonic', '')
                reading_mnemonic = d.get('reading_mnemonic', '')
                meaning_hint = d.get('meaning_hint', '')
                reading_hint = d.get('reading_hint', '')
                characters = d.get('characters', '')
                meanings = json.dumps(d.get('meanings', []))
                readings = json.dumps(d.get('readings', []))
                auxiliary_meanings = json.dumps(d.get('auxiliary_meanings', []))
                component_subject_ids = d.get('component_subject_ids', [])
                amalgamation_subject_ids = d.get('amalgamation_subject_ids', [])
                visually_similar_subject_ids = d.get('visually_similar_subject_ids', [])
                context_sentences = json.dumps(d.get('context_sentences', []))
                pronunciation_audios = json.dumps(d.get('pronunciation_audios', []))
                character_images = json.dumps(d.get('character_images', []))
                parts_of_speech = d.get('parts_of_speech', [])
                document_url = d.get('document_url', '')
                srs_id = d.get('spaced_repetition_system_id', 1)
                lesson_position = d.get('lesson_position', 0)
                hidden_at = d.get('hidden_at')

                batch.append((
                    subject_id, system_user_id, obj_type, slug, level,
                    meaning_mnemonic, reading_mnemonic, meaning_hint, reading_hint,
                    characters, meanings, readings, auxiliary_meanings,
                    component_subject_ids, amalgamation_subject_ids, visually_similar_subject_ids,
                    context_sentences, pronunciation_audios, character_images,
                    parts_of_speech, document_url, srs_id, lesson_position,
                    hidden_at
                ))
            
            if batch:
                insert_query = """
                INSERT INTO subjects (
                    id, user_id, type, slug, level,
                    meaning_mnemonic, reading_mnemonic, meaning_hint, reading_hint,
                    characters, meanings, readings, auxiliary_meanings,
                    component_subject_ids, amalgamation_subject_ids, visually_similar_subject_ids,
                    context_sentences, pronunciation_audios, character_images,
                    parts_of_speech, document_url, spaced_repetition_system_id, lesson_position,
                    hidden_at
                ) VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    type = EXCLUDED.type,
                    slug = EXCLUDED.slug,
                    level = EXCLUDED.level,
                    meaning_mnemonic = EXCLUDED.meaning_mnemonic,
                    reading_mnemonic = EXCLUDED.reading_mnemonic,
                    meaning_hint = EXCLUDED.meaning_hint,
                    reading_hint = EXCLUDED.reading_hint,
                    characters = EXCLUDED.characters,
                    meanings = EXCLUDED.meanings,
                    readings = EXCLUDED.readings,
                    auxiliary_meanings = EXCLUDED.auxiliary_meanings,
                    component_subject_ids = EXCLUDED.component_subject_ids,
                    amalgamation_subject_ids = EXCLUDED.amalgamation_subject_ids,
                    visually_similar_subject_ids = EXCLUDED.visually_similar_subject_ids,
                    context_sentences = EXCLUDED.context_sentences,
                    pronunciation_audios = EXCLUDED.pronunciation_audios,
                    character_images = EXCLUDED.character_images,
                    parts_of_speech = EXCLUDED.parts_of_speech,
                    document_url = EXCLUDED.document_url,
                    spaced_repetition_system_id = EXCLUDED.spaced_repetition_system_id,
                    lesson_position = EXCLUDED.lesson_position,
                    hidden_at = EXCLUDED.hidden_at,
                    updated_at = NOW()
                """
                execute_values(cur, insert_query, batch)
                total_inserted += len(batch)
                conn.commit()

    print(f"Successfully seeded {total_inserted} subjects!")
    cur.close()
    conn.close()

if __name__ == "__main__":
    seed_data()
