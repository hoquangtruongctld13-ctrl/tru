import os
import shutil
from tts_helper import TextToSpeechHelper
from split_text import split_text
from tts import create_tts
from natsort import natsorted
import concurrent.futures
import time
import sys

def print_progress_bar(iteration, total, decimals=1, length=50, fill='█'):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r|{bar}| {percent}% Complete', end='\r')
    if iteration == total:
        print()

def write_error_log(temp_folder, error_info, txt_file):
    """Write error to file-specific error_log.txt immediately."""
    error_log_file = os.path.join(temp_folder, "error_log.txt")
    with open(error_log_file, 'a', encoding='utf-8') as log_file:
        log_file.write(f"File: {txt_file}\n")
        log_file.write(f"Segment: {error_info['segment_id']}\n")
        log_file.write(f"Text not converted to MP3: {error_info['text']}\n")
        log_file.write("-" * 50 + "\n")

def retry_failed_segments(temp_folder, voice_id, txt_file):
    """Retry failed segments listed in error_log.txt using up to 5 threads."""
    error_log_file = os.path.join(temp_folder, "error_log.txt")
    if not os.path.exists(error_log_file):
        print(f"No error_log.txt found in {temp_folder}, skipping retry")
        return []

    print(f"Found error_log.txt in {temp_folder}, reading failed segments...")
    failed_segments = []
    try:
        with open(error_log_file, 'r', encoding='utf-8') as log_file:
            lines = log_file.readlines()
            i = 0
            while i < len(lines):
                if lines[i].startswith("Segment:"):
                    segment_id = lines[i].split("Segment: ")[1].strip()
                    text_line = lines[i + 1].split("Text not converted to MP3: ")[1].strip()
                    failed_segments.append((segment_id, text_line))
                    i += 4  # Skip to next error block
                else:
                    i += 1
    except Exception as e:
        print(f"Failed to read error_log.txt in {temp_folder}: {str(e)}")
        return []

    if not failed_segments:
        print(f"No failed segments found in error_log.txt for {txt_file}")
        return []

    num_threads = min(5, len(failed_segments))
    print(f"Retrying {len(failed_segments)} failed segments for {txt_file} with {num_threads} threads...")

    new_errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {
            executor.submit(create_tts, text, voice_id, segment_id, temp_folder): (segment_id, text)
            for segment_id, text in failed_segments
        }
        for future in concurrent.futures.as_completed(futures):
            segment_id, text = futures[future]
            try:
                success, error_info = future.result()
                if not success:
                    print(f"Retry failed for segment {segment_id}: {error_info.get('error', 'Unknown error')}")
                    new_errors.append(error_info)
                    write_error_log(temp_folder, error_info, txt_file)
                else:
                    print(f"Retry succeeded for segment {segment_id}")
                    with open(error_log_file, 'r', encoding='utf-8') as log_file:
                        lines = log_file.readlines()
                    with open(error_log_file, 'w', encoding='utf-8') as log_file:
                        i = 0
                        while i < len(lines):
                            if lines[i].startswith(f"Segment: {segment_id}\n"):
                                i += 4
                            else:
                                log_file.write(lines[i])
                                i += 1
            except Exception as e:
                print(f"Exception during retry for segment {segment_id}: {str(e)}")
                error_info = {"segment_id": segment_id, "text": text, "error": str(e)}
                new_errors.append(error_info)
                write_error_log(temp_folder, error_info, txt_file)

    return new_errors

if __name__ == "__main__":
    try:
        folder_name = input("Enter the folder name containing text files: ")
        if not os.path.exists(folder_name):
            print(f"Error: Folder {folder_name} does not exist")
            input("Nhấn Enter để thoát...")
            sys.exit(1)

        voice_id = "BV074_streaming"
        num_workers = 150

        temp_root = 'temp'
        os.makedirs(temp_root, exist_ok=True)

        txt_files = natsorted([f for f in os.listdir(folder_name) if f.endswith('.txt')])
        if not txt_files:
            print(f"Error: No .txt files found in {folder_name}")
            input("Nhấn Enter để thoát...")
            sys.exit(1)

        global_error_log = "global_error_log.txt"
        incomplete_files = []

        for txt_file in txt_files:
            mp3_output = os.path.join(folder_name, os.path.splitext(txt_file)[0] + '.mp3')
            if os.path.exists(mp3_output):
                print(f"Skipping {txt_file}: MP3 already exists at {mp3_output}")
                continue

            print(f"Processing file: {txt_file}")
            with open(os.path.join(folder_name, txt_file), 'r', encoding='utf-8') as file:
                input_string = file.read().strip()
            
            max_length = 190
            mode = TextToSpeechHelper.BreakMode.Sentence
            clean_lines = [line.strip() for line in input_string.split('\n') if line.strip()]
            
            chunk_size = 2
            all_sentences = []
            
            for i in range(0, len(clean_lines), chunk_size):
                chunk = clean_lines[i:i+chunk_size]
                chunk_text = '\n'.join(chunk)
                try:
                    chunk_sentences = TextToSpeechHelper.break_sentence(chunk_text, max_length, mode)
                    all_sentences.extend(chunk_sentences)
                    print(f"Processed chunk {i//chunk_size + 1} of {(len(clean_lines)-1)//chunk_size + 1}")
                except Exception as e:
                    print(f"Error processing chunk {i//chunk_size + 1}: {str(e)}, skipping...")
                    continue
            
            sentences = all_sentences
            texts = [sentence.text.strip() for sentence in sentences]
            arr = split_text(texts, max_length)
            total_segments = len(arr)
            print(f"Total segments for {txt_file}: {total_segments}")

            temp_folder = os.path.join(temp_root, os.path.splitext(txt_file)[0])
            os.makedirs(temp_folder, exist_ok=True)

            existing_errors = retry_failed_segments(temp_folder, voice_id, txt_file)
            if not existing_errors:
                mp3_files = natsorted([f for f in os.listdir(temp_folder) if f.endswith('.mp3')])
                if mp3_files and len(mp3_files) >= total_segments:
                    print(f"All segments for {txt_file} processed, merging...")
                    with open(mp3_output, 'wb') as outfile:
                        for mp3_file in mp3_files:
                            file_path = os.path.join(temp_folder, mp3_file)
                            with open(file_path, 'rb') as infile:
                                outfile.write(infile.read())
                    print(f"Done! Combined MP3 saved as {mp3_output} with {len(mp3_files)}/{total_segments} segments")
                    shutil.rmtree(temp_folder)
                    continue
                else:
                    print(f"Not enough MP3 files ({len(mp3_files)}/{total_segments}) for {txt_file}, proceeding to process segments")

            file_start_time = time.time()
            error_logs = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = {}
                for i, segment in enumerate(arr):
                    segment_id = f"{os.path.splitext(txt_file)[0]}_segment_{i}"
                    futures[executor.submit(create_tts, segment, voice_id, segment_id, temp_folder)] = (i, segment)
                
                completed = 0
                for future in concurrent.futures.as_completed(futures):
                    index, segment_text = futures[future]
                    try:
                        success, error_info = future.result(timeout=20)
                        if not success:
                            print(f"Segment {index} failed: {error_info.get('error', 'Unknown error')}")
                            error_logs.append(error_info)
                            write_error_log(temp_folder, error_info, txt_file)
                        else:
                            print(f"Segment {index} processed successfully")
                    except concurrent.futures.TimeoutError:
                        print(f"Segment_{index} timed out after 20 seconds")
                        error_logs.append({
                            "segment_id": index,
                            "text": segment_text,
                            "error": "Timeout after 20 seconds"
                        })
                        write_error_log(temp_folder, {
                            "segment_id": index,
                            "text": segment_text,
                            "error": "Timeout after 20 seconds"
                        }, txt_file)
                    except Exception as e:
                        print(f"Segment_{index} raised exception: {e}")
                        error_logs.append({
                            "segment_id": index,
                            "text": segment_text,
                            "error": str(e)
                        })
                        write_error_log(temp_folder, {
                            "segment_id": index,
                            "text": segment_text,
                            "error": str(e)
                        }, txt_file)
                    completed += 1
                    print_progress_bar(completed, total_segments)

            file_duration = time.time() - file_start_time
            if not error_logs:
                mp3_files = natsorted([f for f in os.listdir(temp_folder) if f.endswith('.mp3')])
                if mp3_files and len(mp3_files) >= total_segments:
                    print(f"Finished processing segments, starting to merge files...")
                    with open(mp3_output, 'wb') as outfile:
                        for mp3_file in mp3_files:
                            file_path = os.path.join(temp_folder, mp3_file)
                            with open(file_path, 'rb') as infile:
                                outfile.write(infile.read())
                    print(f"Done! Combined MP3 saved as {mp3_output} with {len(mp3_files)}/{total_segments} segments in {file_duration:.2f}s")
                    shutil.rmtree(temp_folder)
                else:
                    print(f"Not enough MP3 files generated ({len(mp3_files)}/{total_segments}) for {txt_file} in {file_duration:.2f}s")
                    incomplete_files.append(txt_file)
            else:
                print(f"Errors occurred for {txt_file}, skipping merge and keeping temp folder {temp_folder}")
                incomplete_files.append(txt_file)

        if incomplete_files:
            with open(global_error_log, 'a', encoding='utf-8') as log_file:
                log_file.write(f"Processing completed at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                log_file.write("Files not fully processed (missing MP3 or errors):\n")
                for file in incomplete_files:
                    log_file.write(f"- {file}\n")
                log_file.write("-" * 50 + "\n")
            print(f"Incomplete files logged to {global_error_log}")

        print("All files processed!")
        input("Nhấn Enter để thoát...")

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        input("Nhấn Enter để thoát...")
        sys.exit(1)